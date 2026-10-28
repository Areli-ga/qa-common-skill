#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate qa-testcase-design delivery files before handing them to the user.

规则来源:references/authoring-core.md §C「机器校验硬规则」。改规则时两边同步。

用法:
    python3 validate_output.py --dir <交付目录>            # 推荐:自动发现并校验整个交付目录
    python3 validate_output.py testcases.md [--history H] [--mindmap M] [--tables T]
                               [--images-notes N --content C]
FAIL(退出码 1)阻断交付/发布;WARN 不阻断,但每条都要处理。
"""

import argparse
import json
import re
import sys
from pathlib import Path


BUSINESS_SECTION = "用例设计（按端 / 页面 / 功能组织）"
REQUIRED_SECTIONS = [
    "需求理解",
    "风险判断",
    BUSINESS_SECTION,
    "APP 常驻维度补充",
    "风险与待确认",
    "覆盖自检表",
]
CASE_SECTIONS = [
    BUSINESS_SECTION,
    "APP 常驻维度补充",
]
LEGACY_SECTIONS = ["P0 主流程", "P1 重要场景", "P2 边界/兼容"]
REMOVED_SHOWCASE_SECTION = "showcase（提测准入）"
CASE_RE = re.compile(r"^\[(P[0-2]-\d{2,3})\]\s*(.+)$")
CASE_ID_RE = re.compile(r"\bP[0-2]-\d{2,3}\b")
Q_ID_RE = re.compile(r"\bQ\d+\b")
RULE_ID_RE = re.compile(r"^R\d{2,3}$")
RULE_TRACE_HEADING_RE = re.compile(r"^###\s+业务规则追溯\s*$", re.M)
# 期望里把多个结果串起来的连接:「；」或「，且/，并且/，而且/，同时/，并」
CLAUSE_SPLIT_RE = re.compile(r"[；;]|[，,]\s*(?:并且|而且|同时|且|并)")
BANNED_VAGUE = ["验证功能正常", "功能正常", "检查页面无问题", "正常显示", "按预期展示"]
ALLOWED_COVERAGE_STATUS = {"已覆盖", "N/A", "待确认"}
RISK_LEVELS = ("阻断", "已确认", "记录")
APP_PERMANENT_DIMENSIONS = ["边界/兼容", "跨端联动", "后端/配置", "AB", "埋点", "多语言兼容"]
# 常驻维度允许的少量同义写法(去空白后比较);其余名字一律视为业务维度,避免「提醒配置」被误算成「后端/配置」
PERMANENT_ALIASES = {
    "边界兼容": "边界/兼容", "边界与兼容": "边界/兼容",
    "后端配置": "后端/配置", "后端/接口/配置": "后端/配置", "后端/接口": "后端/配置",
    "AB/灰度": "AB", "AB实验": "AB", "灰度/AB": "AB",
    "埋点/上报": "埋点", "多语言": "多语言兼容",
}
HISTORY_QUERY_GROUPS = {
    "模块词": ("模块词",),
    "功能词": ("功能词",),
    "埋点或字段词": ("埋点或字段词", "埋点词", "字段词", "配置词", "埋点/字段词"),
    "相邻入口词": ("相邻入口词", "入口词"),
}
# 按端分组闸:端范围同时含 Admin 和 App 时,第 3 块 ### 必须以这些端名开头
ADMIN_SCOPE_RE = re.compile(r"admin|后台", re.I)
APP_SCOPE_RE = re.compile(r"(?<![a-z])app(?![a-z])|android|ios|unity|客户端", re.I)
END_GROUP_PREFIXES = ("Admin", "App", "服务端", "H5", "Web")
# 命名闸:分组标题禁用 PRD 表号/图号/规则编号/示例
BAD_GROUP_NAME_RE = re.compile(r"表\s*\d|图\s*\d|(?<![A-Za-z])R\d{2,3}(?!\d)|示例")
EXPECT_FAIL_LEN = 80
EXPECT_WARN_LEN = 50
ACTION_WARN_LEN = 40
P0_RATIO_WARN = 0.5


# ---------------------------------------------------------------- helpers

def split_sections(text):
    sections = {}
    for chunk in re.split(r"\n##\s+", "\n" + text):
        if not chunk.strip():
            continue
        lines = chunk.splitlines()
        name = re.sub(r"^\d+\.\s*", "", lines[0].strip())
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
    dim = re.sub(r"[（(][^）)]*[）)]$", "", dim)  # 去掉结尾括注,如「AB（灰度）」
    for name in APP_PERMANENT_DIMENSIONS:
        if dim == name.replace(" ", ""):
            return name
    return PERMANENT_ALIASES.get(dim, value.strip())


def expectation_of(line):
    m = re.search(r"｜期望：(.*)$", line)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------- testcases.md

def extract_cases(sections, errors, warnings):
    cases, section_cases, duplicates = {}, {name: [] for name in CASE_SECTIONS}, set()
    for section_name in CASE_SECTIONS:
        section = sections.get(section_name, "")
        for block in re.finditer(r"```(?:text)?\n(.*?)```", section, re.S):
            for raw_line in block.group(1).splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                match = CASE_RE.match(line)
                if not match:
                    errors.append(f"{section_name}: invalid case line: {line[:80]}")
                    continue
                case_id = match.group(1)
                if case_id in cases:
                    duplicates.add(case_id)
                cases[case_id] = line
                section_cases[section_name].append(case_id)
                if "｜期望：" not in line:
                    errors.append(f"{case_id}: missing ｜期望：")
                if "｜前置：" in line or "｜步骤：" in line:
                    errors.append(f"{case_id}: 叶子不再写前置/步骤——共用前置写成上一层树标题,步骤压成一句操作,只留「操作｜期望：结果」")
                action = match.group(2).split("｜", 1)[0].strip()
                if len(action) > ACTION_WARN_LEN:
                    warnings.append(f"{case_id}: 操作 {len(action)} 字 > {ACTION_WARN_LEN},压成短句")
                for phrase in BANNED_VAGUE:
                    if phrase in line:
                        errors.append(f"{case_id}: vague phrase {phrase!r}")
                        break
                check_atomic(case_id, expectation_of(line), errors, warnings)
    for case_id in sorted(duplicates):
        errors.append(f"duplicate case id: {case_id}")
    return cases, section_cases


def check_atomic(case_id, expectation, errors, warnings):
    """原子闸:一例一断言。长度与「；」串联是打包多断言的两个机器可见信号。"""
    if expectation is None:
        return
    n = len(expectation)
    if n > EXPECT_FAIL_LEN:
        errors.append(f"{case_id}: 期望 {n} 字 > {EXPECT_FAIL_LEN}——疑似打包多个断言,拆成原子用例")
    elif n > EXPECT_WARN_LEN:
        warnings.append(f"{case_id}: 期望 {n} 字 > {EXPECT_WARN_LEN},检查是否可拆原子用例")
    clauses = len([c for c in CLAUSE_SPLIT_RE.split(expectation) if c.strip()])
    if clauses >= 3:
        errors.append(f"{case_id}: 期望用「；/，且/，同时」等串联 {clauses} 个结果——一例一断言,拆成 {clauses} 条")
    elif clauses == 2:
        warnings.append(f"{case_id}: 期望用「；/，且/，同时」等串联 2 个结果,检查是否应拆成 2 条")


def validate_business_tree(sections, errors):
    """分解树粒度闸:第 4 块单个 ### 组下用例 >4 条却无 #### 细分 → FAIL。"""
    body = sections.get(BUSINESS_SECTION, "")
    group, has_sub, count, in_block = None, False, 0, False

    def flush():
        if group and count > 4 and not has_sub:
            errors.append(f"用例设计: 「{group}」组下 {count} 条用例但无 #### 细分——"
                          f"按分解树拆(数值逐项/分支逐行/结局逐个成节点)")

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


def validate_end_split(sections, errors):
    """按端分组闸:端范围同时含 Admin 和 App 时,第 3 块每个 ### 都必须以端名开头。"""
    scope = next((line for line in sections.get("需求理解", "").splitlines() if "端范围" in line), "")
    if not (ADMIN_SCOPE_RE.search(scope) and APP_SCOPE_RE.search(scope)):
        return
    body = sections.get(BUSINESS_SECTION, "")
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    groups = re.findall(r"^###\s+(.+?)\s*$", body, re.M)
    bad = [g for g in groups if not g.startswith(END_GROUP_PREFIXES)]
    if bad or len(groups) < 2:
        errors.append(f"用例设计: 端范围同时有 Admin 和 App,第一层 ### 须按端分(Admin / App / 服务端 / H5 / Web),"
                      f"再往下按页面/模块细化;不合规的分组: {'、'.join(bad) or '只有 1 个端分组'}")


def validate_group_names(sections, errors):
    """命名闸:分组标题禁用 PRD 表号/图号/规则编号/「示例」,测试者看不懂。"""
    for name in CASE_SECTIONS:
        body = re.sub(r"```.*?```", "", sections.get(name, ""), flags=re.S)
        for title in re.findall(r"^#{3,}\s+(.+?)\s*$", body, re.M):
            if BAD_GROUP_NAME_RE.search(title):
                errors.append(f"{name}: 分组「{title}」用了 PRD 表号/图号/规则编号/示例——"
                              f"改用页面、控件、数据或状态命名,让人照着就能找到地方")


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
    trace = RULE_TRACE_HEADING_RE.search(section)
    if trace:  # 业务规则追溯表由 validate_rule_trace 检查,这里只看前面的列表
        section = section[:trace.start()]
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith("- ")]
    non_bullets = [line for line in lines if not line.startswith("- ")]
    if len(bullet_lines) < 3:
        errors.append(f"需求理解 should use '- ' bullet list with at least 3 items, found {len(bullet_lines)}")
    if non_bullets:
        errors.append(f"需求理解 should not use paragraph text; use '- ' bullet lines instead: {non_bullets[0][:80]}")
    for keyword in ["目标", "入口", "端范围"]:
        if not any(keyword in line for line in bullet_lines):
            errors.append(f"需求理解 bullet list missing {keyword}")


def defined_q_ids(risk_text):
    return {row[0] for row in markdown_rows(risk_text) if row and re.fullmatch(r"Q\d+", row[0])}


def validate_rule_trace(section, cases, risk_text, errors):
    """追溯闸:需求理解末尾「业务规则追溯」表,每条 PRD 规则必须落到用例或已定义的 Q 项。"""
    trace = RULE_TRACE_HEADING_RE.search(section)
    if not trace:
        errors.append("需求理解 missing `### 业务规则追溯` 表:PRD 规则逐条编号并写落点(authoring-core §C)")
        return
    q_ids = defined_q_ids(risk_text)
    rows = [row for row in markdown_rows(section[trace.end():]) if row and row[0] != "编号"]
    if not rows:
        errors.append("业务规则追溯 表没有数据行")
        return
    seen = set()
    for row in rows:
        if len(row) != 4:
            errors.append(f"业务规则追溯 行应为 4 列(编号|规则|来源|落点),实际 {len(row)} 列: {' | '.join(row)[:80]}")
            continue
        rule_id, rule, source, landing = row
        if not RULE_ID_RE.match(rule_id):
            errors.append(f"业务规则追溯 编号格式应为 R01: {rule_id}")
        elif rule_id in seen:
            errors.append(f"业务规则追溯 编号重复: {rule_id}")
        seen.add(rule_id)
        if not rule or rule == "-":
            errors.append(f"业务规则追溯 {rule_id}: 规则为空")
        if not source or source == "-":
            errors.append(f"业务规则追溯 {rule_id}: 来源为空(写正文段落 / 表N / 图NN)")
        landing_cases = CASE_ID_RE.findall(landing)
        landing_qs = Q_ID_RE.findall(landing)
        for case_id in landing_cases:
            if case_id not in cases:
                errors.append(f"业务规则追溯 {rule_id}: 落点引用不存在的用例 {case_id}")
        for q_id in landing_qs:
            if q_id not in q_ids:
                errors.append(f"业务规则追溯 {rule_id}: 落点引用的 {q_id} 未在风险与待确认表中定义")
        if not landing_cases and not landing_qs:
            errors.append(f"业务规则追溯 {rule_id}: 落点为空——这条规则漏测,补用例或在风险与待确认加 Q 项")


def validate_coverage(coverage, cases, errors):
    rows = [cells[:4] for cells in markdown_rows(coverage) if len(cells) >= 4 and cells[0] != "维度"]
    if not rows:
        errors.append("coverage table has no data rows")
        return
    referenced, dimensions, has_history = set(), set(), False
    for dimension, status, case_cell, note in rows:
        dimensions.add(normalize_dimension(dimension))
        has_history |= re.sub(r"\s+", "", dimension) == "历史回归"
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
    if not has_history:
        errors.append("coverage table missing 历史回归 dimension")
    for name in APP_PERMANENT_DIMENSIONS:
        if name not in dimensions:
            errors.append(f"coverage table missing APP permanent dimension: {name}(维度名需逐字一致)")
    for case_id in sorted(set(cases) - referenced):
        errors.append(f"case id missing from coverage table: {case_id}")


def validate_risk_table(sections, cases, errors):
    risk_text = sections.get("风险与待确认", "")
    pending = [cid for cid, line in cases.items() if "（待确认）" in line or "(待确认)" in line]
    if pending and not Q_ID_RE.search(risk_text):
        errors.append("pending cases exist but 风险与待确认 has no Q id")
    for case_id in pending:
        if not re.search(rf"\b{re.escape(case_id)}\b", risk_text):
            errors.append(f"pending case {case_id} must be referenced in 风险与待确认")
    for case_id in sorted(set(CASE_ID_RE.findall(risk_text)) - set(cases)):
        errors.append(f"风险与待确认 references unknown case id: {case_id}")


def validate_risk_levels(risk_text, errors):
    """阻断闸:待确认按影响分级。阻断 = 必须先停下问用户,存在即 FAIL;已确认须留下用户答复。"""
    rows = markdown_rows(risk_text)
    if not rows:
        return
    header = [re.sub(r"\s+", "", c) for c in rows[0]]
    if "级别" not in header:
        errors.append("风险与待确认 缺「级别」列:表头改为 `编号 | 级别 | 问题 | 影响`,级别填 阻断 / 已确认 / 记录")
        return
    level_col = header.index("级别")
    problem_col = header.index("问题") if "问题" in header else None
    blocked = []
    for row in rows[1:]:
        qid = row[0] if row else ""
        level = row[level_col].strip() if level_col < len(row) else ""
        if level not in RISK_LEVELS:
            errors.append(f"风险与待确认 {qid}: 级别 {level!r} 无效,只能是 阻断 / 已确认 / 记录")
        elif level == "阻断":
            blocked.append(qid)
        elif level == "已确认":
            problem = row[problem_col] if problem_col is not None and problem_col < len(row) else ""
            if not re.search(r"用户确认[：:]", problem):
                errors.append(f"风险与待确认 {qid}: 已确认 行的问题列须写「用户确认：<答复>」")
    if blocked:
        errors.append(f"风险与待确认 {'、'.join(blocked)} 为阻断级:先停下问用户;"
                      f"答复后改为 已确认 并在问题列写「用户确认：…」,不得自行改级别")


def validate_priority_mix(cases, warnings):
    total = len(cases)
    p0 = sum(1 for cid in cases if cid.startswith("P0-"))
    if total >= 6 and p0 / total > P0_RATIO_WARN:
        warnings.append(f"P0 占比 {p0}/{total} > {int(P0_RATIO_WARN * 100)}%——全是 P0 等于没有排序,复核风险判断")


def validate_testcases(path, warnings=None):
    """返回 (text, sections, cases, errors);warnings 追加到传入列表。"""
    errors, warnings = [], warnings if warnings is not None else []
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)

    if not re.match(r"\s*#\s+\S", text):
        warnings.append("testcases.md 首行应为 `# <需求名>`(导图根节点与飞书标题兜底)")
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            errors.append(f"missing section: {name}")
    for legacy in LEGACY_SECTIONS:
        if legacy in sections:
            errors.append(f"旧版 P0/P1/P2 一级目录骨架已不支持: {legacy}——改用 6 块骨架(authoring-core §C)")
    if REMOVED_SHOWCASE_SECTION in sections:
        errors.append("showcase 块已取消:删掉「showcase（提测准入）」块,其中用例移入用例设计对应分组,覆盖表删除 showcase 行")

    validate_requirement_understanding(sections.get("需求理解", ""), errors)
    validate_risk_judgment(sections.get("风险判断", ""), errors)
    cases, _ = extract_cases(sections, errors, warnings)
    if not cases:
        errors.append("no executable case lines found(用例行需放在 ```text 块内,行首直接 [P0-01])")
    validate_business_tree(sections, errors)
    validate_end_split(sections, errors)
    validate_group_names(sections, errors)
    validate_risk_table(sections, cases, errors)
    validate_risk_levels(sections.get("风险与待确认", ""), errors)
    validate_coverage(sections.get("覆盖自检表", ""), cases, errors)
    validate_rule_trace(sections.get("需求理解", ""), cases, sections.get("风险与待确认", ""), errors)
    validate_priority_mix(cases, warnings)
    return text, sections, cases, errors


# ---------------------------------------------------------------- history-hits.md

def kb_locatable():
    try:
        import kb  # 同目录 scripts/kb.py
        return kb.locate() is not None
    except Exception:
        return False


def validate_history(path, known_cases, warnings=None):
    errors = []
    warnings = warnings if warnings is not None else []
    text = path.read_text(encoding="utf-8")
    for header in ["检索词组", "命中笔记", "判定", "理由", "编入位置"]:
        if header not in text:
            errors.append(f"history missing column: {header}")
    data_rows = [row for row in markdown_rows(text) if row and row[0] != "检索词组"]
    if not data_rows:
        errors.append("history has no data rows")

    # 未读只认表格数据行的判定列;表外备注不算。读到过命中(保留/待确认/丢弃)就不可能是未读。
    verdicts = [row[2].strip() for row in data_rows if len(row) >= 3]
    kb_unread = (any(v.startswith("未读") for v in verdicts)
                 and not any(v.startswith(("保留", "待确认", "丢弃")) for v in verdicts))
    if kb_unread and kb_locatable():
        warnings.append("history 声明未读 qa-knowledge-base,但本机能定位到知识库——确认是否真的无法检索")
    if not kb_unread:
        queries = [re.sub(r"\s+", "", row[0]) for row in data_rows if row]
        for group, prefixes in HISTORY_QUERY_GROUPS.items():
            if not any(q.startswith(prefixes) for q in queries):
                errors.append(f"history missing query group: {group}(检索词组列以「{group}：」开头;PRD 无对应信息也写一行,判定=未命中并说明)")

    for row in data_rows:
        if len(row) != 5:
            errors.append(f"history row has {len(row)} columns, expected 5(空值写 -): {' | '.join(row)[:100]}")
            continue
        query, note, verdict, reason, landing = row[:5]
        if not query or not verdict or not reason:
            errors.append(f"history row incomplete: {' | '.join(row)[:100]}")
        verdict_norm = verdict.strip()
        # 前缀匹配:实际写法常带说明后缀,如「保留(Top1 高风险)」
        if verdict_norm.startswith(("保留", "待确认")):
            if not note or note == "-":
                errors.append(f"history {verdict} row missing note: {query}")
            if not landing or landing == "-":
                errors.append(f"history {verdict} row missing 编入位置: {query}")
                continue
            for case_id in CASE_ID_RE.findall(landing):
                if case_id not in known_cases:
                    errors.append(f"history references unknown case id: {case_id}")
            if not (CASE_ID_RE.search(landing) or Q_ID_RE.search(landing)
                    or "风险判断" in landing or "覆盖自检表" in landing):
                errors.append(f"history {verdict} landing must be case id, Q id, 风险判断, or 覆盖自检表: {landing}")
    return errors


# ---------------------------------------------------------------- mindmap.puml

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
    for placeholder in ["功能点", "其他业务场景"]:
        if re.search(rf"^\*+\s+{re.escape(placeholder)}\s*$", text, re.M):
            errors.append(f"mindmap contains placeholder node: {placeholder}——结构应来自 testcases.md 分解树/覆盖自检表")
    if re.search(r"\[(?:P[0-2]|S)-\d{2,3}\]", text):
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


# ---------------------------------------------------------------- 数值对账(WARN)

def normalize_for_match(s):
    s = re.sub(r"\s+", "", s)
    return (s.replace("−", "-").replace("＝", "=").replace("×", "x").replace("X", "x")
             .replace("★", "星").replace("％", "%"))


# 通用数值短语(不含任何需求领域词):键=数字、±数字、×倍数、数字+通用单位
_VALUE_PHRASE = re.compile(
    r"[A-Za-z_一-龥]{1,8}\s*[=＝]\s*[−\-]?\d+(?:\.\d+)?"
    r"|(?<![\d\w])[+＋−\-]\s*\d+(?:\.\d+)?"
    r"|[×xX]\s*\d+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?\s*(?:★|星|次|个|条|词|张|档|级|关|课|秒|分钟|小时|天|ms|%|％)"
)


# 飞书 PRD 模板的文档信息行(背景/目标/修订等):叙述性文字,不是可测规格,不对账
_META_ROW_LABELS = {"产品文档", "产品Owner", "需求背景", "产品目标", "主要特性", "修订记录"}
_URL_RE = re.compile(r"https?://\S+")
# 「1 + 1」这类加法拆分:两侧都是数字的「+」不是增量,只去掉加号,避免拆出「+1」误报
_SUM_PLUS_RE = re.compile(r"(?<=\d)\s*[+＋]\s*(?=\d)")


def collect_value_phrases(tables_text):
    phrases = set()
    for line in tables_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] in _META_ROW_LABELS:
            continue
        line = _SUM_PLUS_RE.sub(" ", _URL_RE.sub(" ", line))
        for m in _VALUE_PHRASE.finditer(line):
            tok = re.sub(r"\s+", "", m.group(0)).rstrip("，。;；,")
            if re.fullmatch(r"[+＋−\-]?\d{4,}(?:\.\d+)?", tok):  # 年份/token 类长数字
                continue
            phrases.add(tok)
    return phrases


def audit_table_values(tables_text, testcases_text, warnings):
    """PRD 表格数值要么落进用例,要么在「风险与待确认」说明;只对账这两处,不算需求理解里的复述。"""
    sections = split_sections(testcases_text)
    scope = "\n".join(sections.get(name, "") for name in CASE_SECTIONS + ["风险与待确认"])
    scope_norm = normalize_for_match(scope)
    for phrase in sorted(collect_value_phrases(tables_text)):
        if normalize_for_match(phrase) not in scope_norm:
            warnings.append(f"数值对账: 表格数值「{phrase}」未出现在用例或风险与待确认——补用例或说明")


# ---------------------------------------------------------------- images-notes.md

def expected_image_ids(content_path, meta_path=None):
    ids = []
    if content_path and content_path.exists():
        ids = sorted({int(n) for n in re.findall(r"【图(\d{2,3})｜", content_path.read_text(encoding="utf-8"))})
    if not ids and meta_path and meta_path.exists():
        try:
            n = int(json.loads(meta_path.read_text(encoding="utf-8")).get("images_expected") or 0)
        except (json.JSONDecodeError, ValueError, OSError):
            n = 0
        ids = list(range(1, n + 1))
    return ids


def validate_images_notes(notes_paths, image_ids):
    """读图覆盖闸:content.txt 每个【图NN】都要在 images-notes 里有一节(含略读登记)。"""
    errors = []
    if not image_ids:
        return errors
    existing = [p for p in notes_paths if p.exists()]
    if not existing:
        return [f"images-notes.md 缺失:PRD 有 {len(image_ids)} 张图,有图就必产逐图转录"]
    notes = "\n".join(p.read_text(encoding="utf-8") for p in existing)
    # 只认行首节标题【图NN,正文里顺带提到的图号不算覆盖
    covered = {int(n) for n in re.findall(r"^\s*(?:#+\s*)?【图\s*(\d{1,3})", notes, re.M)}
    missing = [i for i in image_ids if i not in covered]
    if missing:
        errors.append("images-notes 未覆盖图片: " + "、".join(f"图{i:02d}" for i in missing)
                      + "——每张图单独一节、行首写【图NN｜文件名】;略读也要一节写原因")
    return errors


# ---------------------------------------------------------------- 交付目录

def validate_delivery(delivery_dir, require_mindmap=True, require_history=True):
    """校验整个交付目录;publish_to_lark_doc.py 复用本函数。返回 (errors, warnings)。"""
    d = Path(delivery_dir)
    errors, warnings = [], []
    testcases = d / "testcases.md"
    cases = {}
    text = ""
    if not testcases.exists():
        errors.append(f"missing testcases file: {testcases}")
    else:
        text, _, cases, case_errors = validate_testcases(testcases, warnings)
        errors.extend(case_errors)

    history = d / "history-hits.md"
    if history.exists():
        errors.extend(validate_history(history, cases, warnings))
    elif require_history:
        errors.append("missing history-hits.md:每次必产;qa-knowledge-base 不可达也要写明「未读 qa-knowledge-base」及原因")

    mindmap = d / "mindmap.puml"
    if mindmap.exists():
        errors.extend(validate_mindmap(mindmap))
    elif require_mindmap:
        errors.append("missing mindmap.puml:飞书发布由导图承载用例;先运行 scripts/md_to_mindmap.py")

    source = d / "source"
    tables = source / "tables.md"
    if tables.exists() and text:
        audit_table_values(tables.read_text(encoding="utf-8"), text, warnings)

    image_ids = expected_image_ids(source / "content.txt", source / "meta.json")
    notes_paths = [d / "images-notes.md"] + sorted(d.glob("images-notes-*.md"))
    errors.extend(validate_images_notes(notes_paths, image_ids))
    return errors, warnings


def report(errors, warnings, checked):
    for warning in warnings:
        print(f"[validate_output] WARN - {warning}")
    if errors:
        print(f"[validate_output] FAIL ({len(errors)} 项)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[validate_output] PASS " + " ".join(checked))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate qa-testcase-design output files.")
    parser.add_argument("testcases", type=Path, nargs="?")
    parser.add_argument("--dir", type=Path, help="交付目录:自动校验 testcases/history-hits/mindmap/tables 对账/images-notes 覆盖")
    parser.add_argument("--history", type=Path)
    parser.add_argument("--mindmap", type=Path)
    parser.add_argument("--tables", type=Path, action="append", help="source/tables.md(可多次):数值对账,遗漏输出 WARN")
    parser.add_argument("--images-notes", type=Path, action="append", help="images-notes*.md(可多次),需配合 --content")
    parser.add_argument("--content", type=Path, help="source/content.txt:提取【图NN】占位做读图覆盖检查")
    args = parser.parse_args()

    if args.dir:
        errors, warnings = validate_delivery(args.dir)
        return report(errors, warnings, [str(args.dir)])
    if not args.testcases:
        parser.error("需要 testcases.md 路径或 --dir <交付目录>")

    errors, warnings = [], []
    if not args.testcases.exists():
        errors.append(f"missing testcases file: {args.testcases}")
        return report(errors, warnings, [])
    text, _, cases, case_errors = validate_testcases(args.testcases, warnings)
    errors.extend(case_errors)
    checked = [str(args.testcases)]
    if args.history:
        if args.history.exists():
            errors.extend(validate_history(args.history, cases, warnings))
            checked.append(str(args.history))
        else:
            errors.append(f"missing history file: {args.history}")
    if args.mindmap:
        if args.mindmap.exists():
            errors.extend(validate_mindmap(args.mindmap))
            checked.append(str(args.mindmap))
        else:
            errors.append(f"missing mindmap file: {args.mindmap}")
    for tables_path in args.tables or []:
        if tables_path.exists():
            audit_table_values(tables_path.read_text(encoding="utf-8"), text, warnings)
        else:
            warnings.append(f"数值对账: tables 文件不存在 {tables_path}")
    if args.images_notes or args.content:
        errors.extend(validate_images_notes(args.images_notes or [], expected_image_ids(args.content)))
    return report(errors, warnings, checked)


if __name__ == "__main__":
    sys.exit(main())
