#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_to_mindmap.py — 把 testcases.md 确定性转成飞书画板 PlantUML 思维导图(.puml)。

为什么用脚本:确定性转换、不靠 AI 手抄,根治"转写出错/节点重复/长行断行"那类坑。
默认输出完整评审图:业务/覆盖维度 → 子模块 → 用例 → 前置/操作步骤/预期结果。
风险与待确认、需求理解、P0/P1/P2 优先级属性不进入思维导图。

用法:
    python3 scripts/md_to_mindmap.py <testcases.md> [输出.puml] [--compact]

约定:testcases.md 的用例行格式为
    [P0-01] 用例标题｜前置：...｜步骤：...｜期望：...
新结构优先读取 `用例设计（按业务功能 / 需求类目组织）` 内的 `###/####/...` 标题层级；用例放在 ```text``` 围栏里。
如果 testcases.md 已包含 ```plantuml 的 @startmindmap 块,脚本会原样提取该块。
"""
import re
import sys

BUSINESS_CASE_SECTION = "用例设计（按业务功能 / 需求类目组织）"
APP_CASE_SECTION = "APP 常驻维度补充"
CASE_SECTIONS = [
    "showcase（提测准入）",
    BUSINESS_CASE_SECTION,
    APP_CASE_SECTION,
    "P0 主流程",
    "P1 重要场景",
    "P2 边界/兼容",
    "跨端联动",
    "后端 / 配置 / AB / 埋点",
]
PERMANENT_CATEGORIES = ["边界/兼容", "跨端联动", "后端/配置", "AB", "埋点", "多语言兼容"]
EXCLUDED_DIMENSIONS = {"需求理解", "风险判断", "风险与待确认", "覆盖自检表", "历史回归"}
CASE_ID_RE = re.compile(r"\b(?:P[0-2]|S)-\d{2}\b")
CASE_LINE_RE = re.compile(r"^\[((?:P[0-2]|S)-\d{2})\]\s*(.+)$")
CASE_ID_PREFIX_RE = re.compile(r"^\[(?:P[0-2]|S)-\d{2}\]\s*")

PERMANENT_KEYWORDS = {
    "边界/兼容": ["边界", "兼容", "低端", "弱网", "设备", "性能", "前后台", "降级", "超长", "异常", "图片/表格保真", "Android", "iOS"],
    "跨端联动": ["跨端", "联动", "Unity", "原生", "端内", "端间"],
    "后端/配置": ["后端", "接口", "配置", "Admin", "payload", "字段", "权限", "热更"],
    "AB": ["AB", "灰度", "实验", "开关"],
    "埋点": ["埋点", "神策", "事件", "上报", "tracking"],
    "多语言兼容": ["多语言", "本地化", "语言", "翻译", "文案", "词形", "发音"],
}

# 2026-07-08 清空:此前按关键词推断中间层的规则表,一半是「跟读组件改版」需求的领域词
# (战斗数值/反馈分支/结算),对其他需求是跨需求污染;且推断层"命中才有、不命中直挂"导致
# 树深忽深忽浅。先树后例契约生效后,结构一律来自 testcases.md 的 ###/####/##### 分解树,
# 不再由脚本编造中间层。保留空表与 infer_submodule 兜底逻辑,便于以后按需回加通用规则。
SUBMODULE_RULES = {}


def clean(s):
    """单行化:换行/制表 → 空格,合并连续空格,首尾去白。防止节点被折成多行。"""
    value = str(s).replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    value = value.replace("@startmindmap", "startmindmap").replace("@endmindmap", "endmindmap")
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()


def mindmap_case_title(value):
    """思维导图隐藏内部用例 ID,ID 只留在 testcases/自检表/history 中追踪。"""
    return CASE_ID_PREFIX_RE.sub("", clean(value)).strip()


def extract_existing_mindmap(text):
    block = re.search(r"```(?:plantuml|puml)\s*\n(@startmindmap\b.*?@endmindmap)\s*```", text, re.S | re.I)
    if block:
        return block.group(1).strip()
    standalone = re.search(r"(^@startmindmap\b.*?^@endmindmap\s*$)", text, re.S | re.M)
    return standalone.group(1).strip() if standalone else None


def split_sections(text):
    sections = {}
    for chunk in re.split(r"\n##\s+", "\n" + text):
        if not chunk.strip():
            continue
        head = chunk.splitlines()[0].strip()
        name = re.sub(r"^\d+(?:-\d+)?\.\s*", "", head)
        sections[name] = "\n".join(chunk.splitlines()[1:])
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


def parse_case_line(line, section_name, path=None):
    fields = [f.strip() for f in line.split("｜") if f.strip()]
    if not fields:
        return None
    match = CASE_LINE_RE.match(fields[0])
    if not match:
        return None
    case_id, raw_title = match.groups()
    detail = {}
    for field in fields[1:]:
        if field.startswith("前置："):
            detail["前置"] = field.removeprefix("前置：")
        elif field.startswith("步骤："):
            detail["操作步骤"] = field.removeprefix("步骤：")
        elif field.startswith("操作步骤："):
            detail["操作步骤"] = field.removeprefix("操作步骤：")
        elif field.startswith("期望："):
            detail["预期结果"] = field.removeprefix("期望：")
        elif field.startswith("预期结果："):
            detail["预期结果"] = field.removeprefix("预期结果：")
    return {
        "id": case_id,
        "title": mindmap_case_title(raw_title),
        "section": section_name,
        "path": path or [],
        "detail": detail,
    }


def extract_section_cases(section, section_name):
    case_ids = []
    parsed = []
    heading_path = []
    in_block = False
    for raw_line in section.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^(#{3,9})\s+(.+?)\s*$", line)
        if heading and not in_block:
            depth = len(heading.group(1)) - 2
            # 只剥「1. 」「2.3 」这类编号前缀(数字后必须跟 . 、或空格);
            # 不能用 ^\d+ 裸剥——会把「3★ 大获全胜」吃成「★ 大获全胜」(2026-07-08 实测踩坑)
            title = clean(re.sub(r"^\d+(?:\.\d+)*[.、]\s*", "", heading.group(2)))
            heading_path = heading_path[: depth - 1] + [title]
            continue
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        case = parse_case_line(line.strip(), section_name, heading_path[:])
        if not case:
            continue
        parsed.append(case)
        case_ids.append(case["id"])
    return parsed, case_ids


def extract_cases(sections):
    cases = {}
    section_cases = {name: [] for name in CASE_SECTIONS}
    for section_name in CASE_SECTIONS:
        section = sections.get(section_name, "")
        parsed, case_ids = extract_section_cases(section, section_name)
        for case in parsed:
            cases[case["id"]] = case
        section_cases.setdefault(section_name, []).extend(case_ids)
    return cases, section_cases


def category_for_dimension(dimension):
    dim = clean(dimension)
    if dim in EXCLUDED_DIMENSIONS:
        return None
    if dim == "showcase（提测准入）":
        return dim
    # 先做全量精确匹配,再做关键词扫描——否则「多语言兼容」会被排在前面的
    # 「边界/兼容」的关键词"兼容"劫持,导致多语言分类被清空(2026-07-08 实测踩坑)
    if dim in PERMANENT_KEYWORDS:
        return dim
    for category, keywords in PERMANENT_KEYWORDS.items():
        if any(keyword in dim for keyword in keywords):
            return category
    return dim


def infer_submodule(category, dimension, case):
    """无 #### 子级时推断中间层;推断不出返回 None,用例直挂分类节点。
    (2026-07-08 修复:此前兜底返回「功能点」占位层——纯排版噪声,每个单层分组都多长一层
    无信息节点。结构应来自 testcases.md 的 ###/#### 分解树,不靠这里编造。)"""
    if category == "showcase（提测准入）":
        return None
    title = case["title"]
    for submodule, keywords in SUBMODULE_RULES.get(category, []):
        if any(keyword in title for keyword in keywords):
            return submodule
    if dimension and dimension != category and dimension not in EXCLUDED_DIMENSIONS:
        return clean(dimension)
    return None


def fallback_category_for_case(case, section_name):
    title = clean(case["title"])
    inferred = category_for_dimension(title)
    if inferred in PERMANENT_CATEGORIES:
        return inferred, inferred

    # 兜底只用通用类目;需求专属分组交给「覆盖自检表」的维度(每需求不同),
    # 避免把 A 需求的领域词(如"回顾"→结算)误套到 B 需求上造成跨需求污染。
    business_rules = [
        ("数据一致性", ["一致", "重复", "同步", "状态恢复"]),
        ("主流程", ["主流程", "进入", "完成主"]),
    ]
    for category, keywords in business_rules:
        if any(keyword in title for keyword in keywords):
            return category, category

    if section_name == "P2 边界/兼容":
        return "边界/兼容", "边界/兼容"
    if section_name == "跨端联动":
        return "跨端联动", "跨端联动"
    if section_name == "后端 / 配置 / AB / 埋点":
        return "后端/配置", "后端/配置"
    return "其他业务场景", "其他业务场景"


def append_unique(mapping, category, dimension, case_ids, path=None):
    if not category or not case_ids:
        return
    bucket = mapping.setdefault(category, [])
    for item in bucket:
        if item["dimension"] == dimension and item.get("path", []) == (path or []):
            target = item
            break
    else:
        target = {"dimension": dimension, "path": path or [], "case_ids": []}
        bucket.append(target)
    for case_id in case_ids:
        if case_id not in target["case_ids"]:
            target["case_ids"].append(case_id)


def build_category_mapping(sections, cases, section_cases):
    mapping = {}
    assigned = set()
    coverage = sections.get("覆盖自检表", "")
    for cells in markdown_rows(coverage):
        if len(cells) < 3 or cells[0] == "维度":
            continue
        dimension = clean(cells[0])
        category = category_for_dimension(dimension)
        if not category:
            continue
        for case_id in CASE_ID_RE.findall(cells[2]):
            if case_id not in cases or case_id in assigned:
                continue
            case = cases[case_id]
            if case.get("path") and case["section"] == BUSINESS_CASE_SECTION:
                append_unique(mapping, case["path"][0], case["path"][0], [case_id], case["path"][1:])
            elif case.get("path") and case["section"] == APP_CASE_SECTION:
                category_from_path = category_for_dimension(case["path"][0]) or case["path"][0]
                append_unique(mapping, category_from_path, category_from_path, [case_id], case["path"][1:])
            else:
                append_unique(mapping, category, dimension, [case_id])
            assigned.add(case_id)

    for case_id in section_cases.get("showcase（提测准入）", []):
        append_unique(mapping, "showcase（提测准入）", "showcase（提测准入）", [case_id])

    assigned = {case_id for groups in mapping.values() for item in groups for case_id in item["case_ids"]}
    for section_name, case_ids in section_cases.items():
        for case_id in case_ids:
            if case_id in assigned:
                continue
            if section_name == "showcase（提测准入）":
                category, dimension = "showcase（提测准入）", "showcase（提测准入）"
                append_unique(mapping, category, dimension, [case_id])
                continue
            if cases[case_id].get("path") and section_name == BUSINESS_CASE_SECTION:
                path = cases[case_id]["path"]
                append_unique(mapping, path[0], path[0], [case_id], path[1:])
                continue
            if cases[case_id].get("path") and section_name == APP_CASE_SECTION:
                path = cases[case_id]["path"]
                category = category_for_dimension(path[0]) or path[0]
                append_unique(mapping, category, category, [case_id], path[1:])
                continue
            else:
                category, dimension = fallback_category_for_case(cases[case_id], section_name)
            append_unique(mapping, category, dimension, [case_id])
    return mapping


def ordered_categories(mapping):
    order = []
    if "showcase（提测准入）" in mapping:
        order.append("showcase（提测准入）")
    for category in mapping:
        if category not in order and category not in PERMANENT_CATEGORIES:
            order.append(category)
    for category in PERMANENT_CATEGORIES:
        if category not in order:
            order.append(category)
    return order


def emit_case(out, level, case, compact):
    stars = "*" * level
    out.append(f"{stars} {clean(case['title'])}")
    if compact:
        return
    detail_stars = "*" * (level + 1)
    for key in ["前置", "操作步骤", "预期结果"]:
        value = clean(case["detail"].get(key, ""))
        if value:
            out.append(f"{detail_stars} {key}：{value}")


def add_to_tree(tree, path, case):
    if not path:
        tree.setdefault("__cases__", []).append(case)
        return
    head, *tail = path
    children = tree.setdefault("__children__", {})
    node = children.setdefault(head, {})
    add_to_tree(node, tail, case)


def emit_tree(out, level, tree, compact):
    for case in tree.get("__cases__", []):
        emit_case(out, level, case, compact)
    for name, child in tree.get("__children__", {}).items():
        out.append(f"{'*' * level} {clean(name)}")
        emit_tree(out, level + 1, child, compact)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    compact = "--compact" in sys.argv[1:]
    if not args:
        print("用法: python3 md_to_mindmap.py <testcases.md> [输出.puml] [--compact]")
        sys.exit(1)
    src = args[0]
    out_path = args[1] if len(args) > 1 else src.rsplit(".", 1)[0].replace("testcases", "mindmap") + ".puml"

    text = open(src, encoding="utf-8").read()
    existing = extract_existing_mindmap(text)
    if existing:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(existing + "\n")
        nodes = len([l for l in existing.splitlines() if l.startswith("*")])
        depth = max((len(l) - len(l.lstrip("*")) for l in existing.splitlines() if l.startswith("*")), default=0)
        print(f"[md_to_mindmap] 提取已有 PlantUML {out_path}({nodes} 节点, 最深 {depth} 层)")
        print("[md_to_mindmap] 交付提示:清空飞书画板编辑框 → 从【已发布飞书文档的思维导图代码块】或本地 .puml 全选复制 → 只粘一次(勿从对话复制,长行会折断)")
        return

    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "测试用例")
    sec = split_sections(text)
    cases, section_cases = extract_cases(sec)
    mapping = build_category_mapping(sec, cases, section_cases)

    out = ["@startmindmap", f"* {clean(title)}"]

    for category in ordered_categories(mapping):
        out.append(f"** {clean(category)}")
        groups = mapping.get(category, [])
        if not groups:
            out.append("*** 无")
            continue
        if category == "showcase（提测准入）":
            for group in groups:
                for case_id in group["case_ids"]:
                    emit_case(out, 3, cases[case_id], compact)
            continue
        tree = {}
        for group in groups:
            dimension = group["dimension"]
            for case_id in group["case_ids"]:
                case = cases[case_id]
                path = group.get("path") or []
                if not path:
                    submodule = infer_submodule(category, dimension, case)
                    path = [submodule] if submodule else []
                add_to_tree(tree, path, case)
        emit_tree(out, 3, tree, compact)

    out.append("@endmindmap")

    # 自检:层级不跳变、无空节点
    prev = 0
    for i, l in enumerate(out):
        if l.startswith("*"):
            lv = len(l) - len(l.lstrip("*"))
            if prev and lv > prev + 1:
                print(f"⚠️ 层级跳变(第{i+1}行 {prev}→{lv}),请检查 testcases.md 结构")
            prev = lv
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    nodes = len([l for l in out if l.startswith("*")])
    depth = max((len(l) - len(l.lstrip("*")) for l in out if l.startswith("*")), default=0)
    mode = "compact" if compact else "full"
    print(f"[md_to_mindmap] 写出 {out_path}({mode}, {nodes} 节点, 最深 {depth} 层)")
    print("[md_to_mindmap] 交付提示:清空飞书画板编辑框 → 从【已发布飞书文档的思维导图代码块】或本地 .puml 全选复制 → 只粘一次(勿从对话复制,长行会折断)")


if __name__ == "__main__":
    main()
