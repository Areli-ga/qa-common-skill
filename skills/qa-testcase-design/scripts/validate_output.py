#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate qa-testcase-design delivery files before handing them to the user."""

import argparse
import re
import sys
from pathlib import Path


NEW_REQUIRED_SECTIONS = [
    "需求理解",
    "风险判断",
    "showcase（提测准入）",
    "用例设计（按业务功能 / 需求类目组织）",
    "APP 常驻维度补充",
    "风险与待确认",
    "覆盖自检表",
]
OLD_REQUIRED_SECTIONS = [
    "需求理解",
    "风险判断",
    "showcase（提测准入）",
    "P0 主流程",
    "P1 重要场景",
    "P2 边界/兼容",
    "跨端联动",
    "后端 / 配置 / AB / 埋点",
    "风险与待确认",
    "覆盖自检表",
]
NEW_CASE_SECTIONS = {
    "showcase（提测准入）",
    "用例设计（按业务功能 / 需求类目组织）",
    "APP 常驻维度补充",
}
OLD_CASE_SECTIONS = {
    "showcase（提测准入）",
    "P0 主流程",
    "P1 重要场景",
    "P2 边界/兼容",
    "跨端联动",
    "后端 / 配置 / AB / 埋点",
}
CASE_RE = re.compile(r"^\[(P[0-2]-\d{2})\]\s*(.+)$")
CASE_ID_RE = re.compile(r"\bP[0-2]-\d{2}\b")
Q_ID_RE = re.compile(r"\bQ\d+\b")
BANNED_VAGUE = ["验证功能正常", "检查页面无问题", "正常显示", "按预期展示"]
ALLOWED_COVERAGE_STATUS = {"已覆盖", "N/A", "待确认"}
APP_PERMANENT_DIMENSIONS = ["边界/兼容", "跨端联动", "后端/配置", "AB", "埋点", "多语言兼容"]


def split_sections(text):
    sections = {}
    for chunk in re.split(r"\n##\s+", "\n" + text):
        if not chunk.strip():
            continue
        lines = chunk.splitlines()
        head = lines[0].strip()
        name = re.sub(r"^\d+\.\s*", "", head)
        sections[name] = "\n".join(lines[1:])
    return sections


def markdown_rows(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def normalize_dimension(value):
    dim = re.sub(r"\s+", "", value)
    upper = dim.upper()
    if "边界" in dim and "兼容" in dim:
        return "边界/兼容"
    if "跨端" in dim or "联动" in dim:
        return "跨端联动"
    if "AB" in upper or "灰度" in dim or "实验" in dim:
        return "AB"
    if "埋点" in dim or "神策" in dim or "上报" in dim:
        return "埋点"
    if "多语言" in dim or "本地化" in dim:
        return "多语言兼容"
    if "后端" in dim or "配置" in dim or "接口" in dim:
        return "后端/配置"
    return value.strip()


def detect_schema(sections, allow_old_schema=False):
    has_new = all(name in sections for name in NEW_REQUIRED_SECTIONS)
    has_old = all(name in sections for name in OLD_REQUIRED_SECTIONS)
    if has_new:
        return "new", NEW_REQUIRED_SECTIONS, NEW_CASE_SECTIONS
    if has_old:
        if allow_old_schema:
            return "old", OLD_REQUIRED_SECTIONS, OLD_CASE_SECTIONS
        return "old_disallowed", OLD_REQUIRED_SECTIONS, OLD_CASE_SECTIONS
    return "new", NEW_REQUIRED_SECTIONS, NEW_CASE_SECTIONS


EXPECT_FAIL_LEN = 140
EXPECT_WARN_LEN = 90


def extract_cases(sections, errors, case_sections, warnings=None):
    warnings = warnings if warnings is not None else []
    cases = {}
    section_cases = {section_name: [] for section_name in case_sections}
    duplicates = set()
    for section_name in case_sections:
        section = sections.get(section_name, "")
        for block in re.finditer(r"```(?:text)?\n(.*?)```", section, re.S):
            for raw_line in block.group(1).splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                match = CASE_RE.match(line)
                if not match:
                    errors.append(f"{section_name}: invalid case line: {line}")
                    continue
                case_id = match.group(1)
                if case_id in cases:
                    duplicates.add(case_id)
                cases[case_id] = line
                section_cases.setdefault(section_name, []).append(case_id)
                for token in ["｜前置：", "｜步骤：", "｜期望："]:
                    if token not in line:
                        errors.append(f"{case_id}: missing {token}")
                for phrase in BANNED_VAGUE:
                    if phrase in line:
                        errors.append(f"{case_id}: vague phrase {phrase!r}")
                # 原子用例闸(2026-07-08):期望过长≈打包多断言,结构在这一刻丢失、导图无法还原
                exp_match = re.search(r"｜期望：(.*)$", line)
                if exp_match:
                    exp_len = len(exp_match.group(1).strip())
                    if exp_len > EXPECT_FAIL_LEN:
                        errors.append(f"{case_id}: 期望 {exp_len} 字 > {EXPECT_FAIL_LEN}——疑似打包多个断言,按「一例一断言」拆成原子用例")
                    elif exp_len > EXPECT_WARN_LEN:
                        warnings.append(f"{case_id}: 期望 {exp_len} 字 > {EXPECT_WARN_LEN},检查是否可拆原子用例")
    for case_id in sorted(duplicates):
        errors.append(f"duplicate case id: {case_id}")
    return cases, section_cases


def validate_business_tree(sections, errors):
    """分解树粒度闸(2026-07-08):第 4 块单个 ### 组下用例 >4 条却无 #### 细分 → FAIL。
    结构必须在出例时以多级标题形态存在,导图由树长出;塞在一行期望里的结构无法恢复。"""
    body = sections.get("用例设计（按业务功能 / 需求类目组织）", "")
    group, has_sub, count, in_block = None, False, 0, False

    def flush():
        if group and count > 4 and not has_sub:
            errors.append(
                f"用例设计: 「{group}」组下 {count} 条用例但无 #### 细分——"
                f"按分解树拆(数值逐项/分支逐行/结局逐个成节点)"
            )

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            m3 = re.match(r"^###\s+(.+)$", line)
            if m3:
                flush()
                group, has_sub, count = m3.group(1).strip(), False, 0
                continue
            if re.match(r"^#{4,}\s+", line) and group:
                has_sub = True
        elif CASE_RE.match(line.strip()):
            count += 1
    flush()


def normalize_for_match(s):
    s = re.sub(r"\s+", "", s)
    return (s.replace("−", "-").replace("＝", "=").replace("×", "x")
             .replace("X", "x").replace("★", "星"))


_VALUE_PHRASE = re.compile(
    r"(?:HP|血量|伤害)\s*[=＝][^,，。;；|<]{1,14}"
    r"|(?<![\d\w])[−\-]\s*\d+(?:\.\d+)?"
    r"|[×xX]\s*\d+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?\s*(?:★|星|次|词|张|层|连|档|血|伤害|秒|分钟|ms|%)"
)


def collect_value_phrases(tables_text):
    """从 tables.md 表格行抽数值短语(带单位/符号上下文;过滤 4 位以上纯数字如年份/token)。
    供数值对账:PRD 表格里的每个数值要么落进用例,要么在风险与待确认说明。"""
    phrases = set()
    for line in tables_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        for m in _VALUE_PHRASE.finditer(line):
            tok = re.sub(r"\s+", "", m.group(0)).rstrip("，。;；,")
            if re.fullmatch(r"[−\-]?\d{4,}(?:\.\d+)?", tok):
                continue
            phrases.add(tok)
    return phrases


def audit_table_values(tables_text, testcases_text, warnings):
    tc_norm = normalize_for_match(testcases_text)
    for phrase in sorted(collect_value_phrases(tables_text)):
        if normalize_for_match(phrase) not in tc_norm:
            warnings.append(f"数值对账: 表格数值「{phrase}」未出现在任何用例——补用例或在「风险与待确认」说明")


def validate_risk_judgment(section, errors):
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith("- ")]
    statement_lines = [line for line in lines if not line.startswith("- ") and not line.startswith("|")]

    if not statement_lines:
        errors.append("风险判断 must start with one judgment sentence before bullet reasons")
    elif statement_lines[0].startswith(("目标", "需求", "本次需求")):
        errors.append("风险判断 should be a risk judgment, not neutral requirement restatement")

    if not (3 <= len(bullet_lines) <= 5):
        errors.append(f"风险判断 should contain 3-5 bullet reasons, found {len(bullet_lines)}")


def validate_requirement_understanding(section, errors):
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith("- ")]
    non_bullets = [line for line in lines if not line.startswith("- ")]

    if len(bullet_lines) < 3:
        errors.append(f"需求理解 should use '- ' bullet list with at least 3 items, found {len(bullet_lines)}")
    if non_bullets:
        sample = non_bullets[0][:80]
        errors.append(f"需求理解 should not use paragraph text; use '- ' bullet lines instead: {sample}")

    required_keywords = ["目标", "入口", "端范围"]
    for keyword in required_keywords:
        if not any(keyword in line for line in bullet_lines):
            errors.append(f"需求理解 bullet list missing {keyword}")


def coverage_data_rows(coverage):
    data_rows = []
    for cells in markdown_rows(coverage):
        if len(cells) < 4 or cells[0] == "维度":
            continue
        data_rows.append(cells[:4])
    return data_rows


def validate_coverage(coverage, cases, errors):
    rows = coverage_data_rows(coverage)
    if not rows:
        errors.append("coverage table has no data rows")
        return

    referenced = set()
    dimensions = set()
    has_showcase_dimension = False
    for dimension, status, case_cell, note in rows:
        normalized = normalize_dimension(dimension)
        dimensions.add(normalized)
        if dimension == "showcase（提测准入）":
            has_showcase_dimension = True

        if status not in ALLOWED_COVERAGE_STATUS:
            errors.append(f"coverage dimension {dimension}: invalid status {status!r}")
        if status == "已覆盖" and not CASE_ID_RE.search(case_cell):
            errors.append(f"coverage dimension {dimension}: 已覆盖 must reference at least one case id")
        if status == "N/A" and CASE_ID_RE.search(case_cell):
            errors.append(f"coverage dimension {dimension}: N/A should not reference case ids")
        if status == "待确认" and not (CASE_ID_RE.search(case_cell) or Q_ID_RE.search(note) or "待确认" in note):
            errors.append(f"coverage dimension {dimension}: 待确认 must reference affected case id or Q id")

        for case_id in CASE_ID_RE.findall(case_cell):
            if case_id not in cases:
                errors.append(f"coverage references unknown case id: {case_id}")
            referenced.add(case_id)

    if not has_showcase_dimension:
        errors.append("coverage table missing showcase（提测准入） dimension")

    missing_dimensions = [name for name in APP_PERMANENT_DIMENSIONS if name not in dimensions]
    for name in missing_dimensions:
        errors.append(f"coverage table missing APP permanent dimension: {name}")

    missing_cases = sorted(set(cases) - referenced)
    for case_id in missing_cases:
        errors.append(f"case id missing from coverage table: {case_id}")


def validate_showcase(section_cases, errors):
    count = len(section_cases.get("showcase（提测准入）", []))
    if not (1 <= count <= 5):
        errors.append(f"showcase（提测准入） should contain 1-5 cases, found {count}")


def validate_pending_cases(sections, cases, errors):
    risk_text = sections.get("风险与待确认", "")
    pending_ids = [
        case_id
        for case_id, line in cases.items()
        if "（待确认）" in line or "(待确认)" in line
    ]
    if pending_ids and not Q_ID_RE.search(risk_text):
        errors.append("pending cases exist but 风险与待确认 has no Q id")
    for case_id in pending_ids:
        if case_id not in risk_text:
            errors.append(f"pending case {case_id} must be referenced in 风险与待确认")


def validate_testcases(path, allow_old_schema=False, warnings=None):
    errors = []
    warnings = warnings if warnings is not None else []
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    schema_name, required_sections, case_sections = detect_schema(sections, allow_old_schema)

    for name in required_sections:
        if name not in sections:
            errors.append(f"missing section: {name}")

    if schema_name == "old_disallowed":
        errors.append(
            "old schema is no longer accepted by default; use the new 7-section schema "
            "or pass --allow-old-schema only for legacy audits"
        )

    if schema_name == "new":
        for old_top_level in ["P0 主流程", "P1 重要场景", "P2 边界/兼容"]:
            if old_top_level in sections:
                errors.append(f"new schema should not use old priority section: {old_top_level}")

    validate_requirement_understanding(sections.get("需求理解", ""), errors)
    validate_risk_judgment(sections.get("风险判断", ""), errors)

    cases, section_cases = extract_cases(sections, errors, case_sections, warnings)
    if not cases:
        errors.append("no executable case lines found")
    if schema_name == "new":
        validate_business_tree(sections, errors)
    validate_showcase(section_cases, errors)
    validate_pending_cases(sections, cases, errors)

    coverage = sections.get("覆盖自检表", "")
    if "历史回归" not in coverage:
        errors.append("coverage table missing 历史回归 dimension")
    validate_coverage(coverage, cases, errors)

    return text, sections, cases, errors


def validate_history(path, known_cases):
    errors = []
    text = path.read_text(encoding="utf-8")
    required_headers = ["检索词组", "命中笔记", "判定", "理由", "编入位置"]
    for header in required_headers:
        if header not in text:
            errors.append(f"history missing column: {header}")

    rows = markdown_rows(text)
    data_rows = [row for row in rows if row and row[0] != "检索词组"]
    if not data_rows:
        errors.append("history has no data rows")

    for row in data_rows:
        if len(row) < 5:
            continue
        query, note, verdict, reason, landing = row[:5]
        if not query or not verdict or not reason:
            errors.append(f"history row incomplete: {' | '.join(row)}")
        # 前缀匹配(2026-07-08 修复):实际写法常带说明后缀,如「保留(Top1 高风险)」「待确认(弱)」,
        # 此前用集合精确匹配会让这类行整体跳过落点强校验,漏检"保留却没编入位置"。
        verdict_norm = verdict.strip()
        if verdict_norm.startswith("保留") or verdict_norm.startswith("待确认"):
            if not note or note == "-":
                errors.append(f"history {verdict} row missing note: {query}")
            if not landing or landing == "-":
                errors.append(f"history {verdict} row missing 编入位置: {query}")
            for case_id in CASE_ID_RE.findall(landing):
                if case_id not in known_cases:
                    errors.append(f"history references unknown case id: {case_id}")
            if not CASE_ID_RE.search(landing) and not Q_ID_RE.search(landing) and landing not in {"风险判断", "覆盖自检表"}:
                errors.append(f"history {verdict} landing must be case id, Q id, 风险判断, or 覆盖自检表: {landing}")
    return errors


def validate_mindmap(path):
    errors = []
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped.startswith("@startmindmap"):
        errors.append("mindmap missing @startmindmap")
    if not stripped.endswith("@endmindmap"):
        errors.append("mindmap missing @endmindmap")
    for forbidden in ["风险与待确认", "history-hits", "历史回归", "覆盖自检", "检索词组", "qa-knowledge-base"]:
        if forbidden in text:
            errors.append(f"mindmap should not contain appendix text: {forbidden}")
    for old_node in ["需求理解", "P0 主流程", "P1 重要场景", "P2 边界/兼容"]:
        if re.search(rf"^\*+\s+{re.escape(old_node)}\s*$", text, re.M):
            errors.append(f"mindmap should not contain old top-level node: {old_node}")
    # 占位节点闸(2026-07-08):「功能点」=转换器编造的废层;「其他业务场景」=用例没进覆盖自检表的信号
    for placeholder in ["功能点", "其他业务场景"]:
        if re.search(rf"^\*+\s+{re.escape(placeholder)}\s*$", text, re.M):
            errors.append(f"mindmap contains placeholder node: {placeholder}——结构应来自 testcases.md 分解树/覆盖自检表")
    if re.search(r"\[(?:P[0-2]|S)-\d{2}\]", text):
        errors.append("mindmap should hide internal case IDs")

    prev = 0
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("*"):
            continue
        level = len(line) - len(line.lstrip("*"))
        if prev and level > prev + 1:
            errors.append(f"mindmap level jump at line {index}: {prev}->{level}")
        prev = level
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate qa-testcase-design output files.")
    parser.add_argument("testcases", type=Path)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--mindmap", type=Path)
    parser.add_argument(
        "--allow-old-schema",
        action="store_true",
        help="Allow the legacy P0/P1/P2 section schema for old archived outputs only.",
    )
    parser.add_argument(
        "--tables",
        type=Path,
        action="append",
        help="source/tables.md 路径(可多次):做 PRD 数值对账,表格数值未落入用例则输出 WARN。",
    )
    args = parser.parse_args()

    errors = []
    warnings = []
    if not args.testcases.exists():
        errors.append(f"missing testcases file: {args.testcases}")
    else:
        text, _, cases, case_errors = validate_testcases(
            args.testcases, allow_old_schema=args.allow_old_schema, warnings=warnings)
        errors.extend(case_errors)

        if args.history:
            if not args.history.exists():
                errors.append(f"missing history file: {args.history}")
            else:
                errors.extend(validate_history(args.history, cases))

        if args.mindmap:
            if not args.mindmap.exists():
                errors.append(f"missing mindmap file: {args.mindmap}")
            else:
                errors.extend(validate_mindmap(args.mindmap))

        for tables_path in args.tables or []:
            if not tables_path.exists():
                warnings.append(f"数值对账: tables 文件不存在 {tables_path}")
            else:
                audit_table_values(tables_path.read_text(encoding="utf-8"), text, warnings)

    for warning in warnings:
        print(f"[validate_output] WARN - {warning}")
    if errors:
        print("[validate_output] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    checked = [str(args.testcases)]
    if args.history:
        checked.append(str(args.history))
    if args.mindmap:
        checked.append(str(args.mindmap))
    print("[validate_output] PASS " + " ".join(checked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
