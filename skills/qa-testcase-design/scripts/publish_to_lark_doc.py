#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish qa-testcase-design delivery files into a new Lark/Feishu docx."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lark_common  # 凭证/HTTP 内核,与 read_doc.py 共用(同目录)
import validate_output


# 飞书凭证与 read_doc.py 同源(见 lark_common):环境变量优先,否则拉 config 服务(需 VPN)。
# 不依赖 giggle-common gateway(CF Access),读写统一一套 tenant_access_token。
MAX_BLOCK_CHARS = 1800


class PublishTarget(NamedTuple):
    kind: str
    token: str
    source: str
    host: str


class PublishError(RuntimeError):
    """发布链路分段错误:带 stage 与已建文档信息,供 main 输出友好 JSON 而非裸 traceback。
    document_id 非空 = 飞书已建出半成品文档(建档成功但后续步骤失败),需提示用户可手动删除。"""

    def __init__(self, stage: str, message: str, document_id: str | None = None, document_url: str = ""):
        super().__init__(message)
        self.stage = stage
        self.document_id = document_id
        self.document_url = document_url


def parse_publish_target(value: str) -> PublishTarget:
    source = value.strip()
    wiki = re.search(r"https?://([^/]+)/wiki/([\w-]+)", source)
    if wiki:
        return PublishTarget("wiki_parent", wiki.group(2), source, wiki.group(1))

    drive = re.search(r"https?://([^/]+)/drive/folder/([\w-]+)", source)
    if drive:
        return PublishTarget("drive_folder", drive.group(2), source, drive.group(1))

    folder = re.search(r"https?://([^/]+)/folder/([\w-]+)", source)
    if folder:
        return PublishTarget("drive_folder", folder.group(2), source, folder.group(1))

    if re.fullmatch(r"fld[\w-]+", source):
        return PublishTarget("drive_folder", source, source, "")

    raise ValueError(
        "无法识别飞书输出目录。请提供 /wiki/<token> Wiki 父节点链接，"
        "或 /drive/folder/<folder_token> 云文档文件夹链接。"
    )


def wiki_mount_payload(space_id: str, parent_node_token: str, doc_id: str) -> dict:
    return {
        "obj_type": "docx",
        "parent_node_token": parent_node_token,
        "node_type": "origin",
        "obj_token": doc_id,
    }


def chunk_text(text: str, limit: int = MAX_BLOCK_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if current and current_len + len(line) > limit:
            chunks.append("".join(current).rstrip())
            current = []
            current_len = 0
        if len(line) > limit:
            if current:
                chunks.append("".join(current).rstrip())
                current = []
                current_len = 0
            for i in range(0, len(line), limit):
                chunks.append(line[i : i + limit].rstrip())
            continue
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current).rstrip())
    return [chunk for chunk in chunks if chunk]


_INLINE_RE = re.compile(r"(?P<code>`[^`\n]+`)|(?P<bold>\*\*[^*\n]+\*\*)")


def text_elements(content: str) -> list[dict]:
    """把文本按行内 Markdown（`code` / **bold**）切成带样式的 text_run。
    飞书 text_run 不解析 Markdown 源码,不在此转样式的话 `code`/**bold** 会按字面(带符号)显示。
    链接/图片语法保持原样(用例正文极少用,且飞书 link.url 需特殊编码,不在此硬转)。
    注意:思维导图 PlantUML 走独立的 code_block(),不经过本函数,不受影响。"""
    if not content:
        return [{"text_run": {"content": ""}}]
    runs: list[dict] = []
    pos = 0
    for m in _INLINE_RE.finditer(content):
        if m.start() > pos:
            runs.append({"text_run": {"content": content[pos:m.start()]}})
        if m.lastgroup == "code":
            runs.append({"text_run": {"content": m.group()[1:-1], "text_element_style": {"inline_code": True}}})
        else:
            runs.append({"text_run": {"content": m.group()[2:-2], "text_element_style": {"bold": True}}})
        pos = m.end()
    if pos < len(content):
        runs.append({"text_run": {"content": content[pos:]}})
    return runs or [{"text_run": {"content": content}}]


def make_block(block_name: str, content: str) -> dict:
    block_types = {
        "text": 2,
        "heading1": 3,
        "heading2": 4,
        "heading3": 5,
        "bullet": 12,
        "code": 14,
    }
    block_type = block_types[block_name]
    field = block_name
    return {"block_type": block_type, field: {"elements": text_elements(content)}}


def code_block(text: str) -> dict:
    """整段文本渲成**单个** code block(14),内部按 MAX_BLOCK_CHARS 无损硬切成多个
    text_run。飞书渲染成一个代码块;硬切不 rstrip、不按行,拼接后与原文逐字符一致,
    保护 PlantUML 的换行与空格(mindmap 必须整段完整才能复制到画板)。
    """
    limit = MAX_BLOCK_CHARS
    elements = [
        {"text_run": {"content": text[i : i + limit]}}
        for i in range(0, len(text), limit)
    ] or [{"text_run": {"content": ""}}]
    return {"block_type": 14, "code": {"elements": elements}}


# 飞书 descendant 接口单次后代块数的保守上限(官方约 500,留余量)
MAX_DESCENDANTS = 490

# markdown 表格识别:内容行 | a | b |、分隔行 |---|---| 或 :--:|:--
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$")


def parse_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    # 支持转义竖线 \|:先占位再拆,避免 cell 内 \| 被误拆成两列、导致整行列错位(飞书展示用普通 |)
    parts = stripped.replace("\\|", "\x00").split("|")
    return [cell.strip().replace("\x00", "|") for cell in parts]


# 发布呈现层裁剪:飞书文档定位评审 + 看图,这三块正文由思维导图承载。
# 本地 testcases.md 始终保留完整 7 块;此处只影响飞书展示。
SKIP_PUBLISH_SECTIONS = ("showcase（提测准入）", "用例设计（", "APP 常驻维度补充")
_CASE_ID = re.compile(r"P[0-2]-\d{2}")
_HEADING2 = re.compile(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$")


def compress_coverage_row(line: str) -> str:
    """覆盖自检表发布态:ID 列压成用例数;完整 ID 追溯回本地 testcases.md。"""
    if _TABLE_SEP.match(line):
        return line
    cells = parse_table_cells(line)
    if len(cells) < 4:
        return line
    if cells[2] in {"对应用例", "覆盖用例"}:
        cells[2] = "用例数"
    else:
        ids = _CASE_ID.findall(cells[2])
        if ids:
            cells[2] = str(len(ids))
    return "| " + " | ".join(cells) + " |"


_ID_LIST = re.compile(r"P[0-2]-\d{2}(?:\s*[、,，/和]\s*P[0-2]-\d{2})*")


def build_case_dimension_map(markdown: str) -> dict:
    """从覆盖自检表建 用例ID → 维度 映射(取首个出现的维度),供风险表「影响」列发布态改写。"""
    id2dim: dict = {}
    in_cov = False
    for line in markdown.splitlines():
        m = _HEADING2.match(line)
        if m:
            in_cov = "覆盖自检表" in m.group(1)
            continue
        if not in_cov or not _TABLE_ROW.match(line) or _TABLE_SEP.match(line):
            continue
        cells = parse_table_cells(line)
        if len(cells) < 3 or cells[0] in {"维度", ""}:
            continue
        for cid in _CASE_ID.findall(cells[2]):
            id2dim.setdefault(cid, cells[0])
    return id2dim


def rewrite_risk_impact_row(line: str, id2dim: dict, impact_col):
    """风险与待确认表发布态(2026-07-08 修复):「影响」列的用例编号改写为所属维度名——
    飞书文档里正文用例块已裁剪、思维导图又隐藏 ID,编号在文档内是死引用(用户实评反馈)。
    与覆盖表「ID 列→用例数」同一呈现原则;完整 ID 仍以本地 testcases.md 为准。
    返回 (改写后的行, 影响列下标);表头行用于定位「影响」列。"""
    if _TABLE_SEP.match(line):
        return line, impact_col
    cells = parse_table_cells(line)
    header = [re.sub(r"\s+", "", c) for c in cells]
    if header and header[0] in {"编号", "ID"}:
        return line, (header.index("影响") if "影响" in header else None)
    if impact_col is None or impact_col >= len(cells):
        return line, impact_col

    def repl(m):
        dims = []
        for cid in _CASE_ID.findall(m.group(0)):
            d = id2dim.get(cid)
            if d and d not in dims:
                dims.append(d)
        return "、".join(dims) if dims else m.group(0)

    cells[impact_col] = _ID_LIST.sub(repl, cells[impact_col])
    return "| " + " | ".join(cells) + " |", impact_col


def split_testcases_for_publish(markdown: str, reserve_mindmap_number: bool):
    """发布呈现裁剪:跳过过程用例块、压缩覆盖表 ID 列、风险表影响列 ID 改写为维度、
    剩余块顺序重编号。首个被跳过块的位置由思维导图占位。
    """
    before: list[str] = []
    after: list[str] = []
    target = before
    skip = False
    in_cov = False
    in_risk = False
    risk_impact_col = None
    id2dim = build_case_dimension_map(markdown)
    num = 0
    mindmap_no: int | None = None
    for line in markdown.splitlines():
        m = _HEADING2.match(line)
        if m:
            head = m.group(1)
            if any(key in head for key in SKIP_PUBLISH_SECTIONS):
                if target is before:
                    target = after
                    if reserve_mindmap_number:
                        num += 1
                        mindmap_no = num
                skip = True
                in_cov = False
                in_risk = False
                continue
            skip = False
            in_cov = "覆盖自检表" in head
            in_risk = "风险与待确认" in head
            num += 1
            target.append(f"## {num}. {head}")
            continue
        if skip:
            continue
        if in_cov and _TABLE_ROW.match(line):
            line = compress_coverage_row(line)
        if in_risk and _TABLE_ROW.match(line):
            line, risk_impact_col = rewrite_risk_impact_row(line, id2dim, risk_impact_col)
        target.append(line)
    return "\n".join(before), "\n".join(after), mindmap_no


def normalized_header(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    return [re.sub(r"\s+", "", str(cell or "")) for cell in rows[0]]


def infer_column_width(rows: list[list[str]]) -> list[int] | None:
    """按 QA 交付里的固定表格类型设置飞书列宽。
    宽度来自 2026-07-06 用户手动调好的飞书文档表格;覆盖表新版保留 ID,因此给
    「对应用例」列比旧「用例数」更宽。
    """
    header = normalized_header(rows)
    column_size = max((len(r) for r in rows), default=0)

    if column_size == 4 and header[:2] in (["ID", "问题"], ["编号", "问题"]):
        third = header[2]
        fourth = header[3]
        if third in {"影响", "影响用例"} and fourth in {"建议确认对象", "建议处理"}:
            return [52, 412, 259, 100]

    if column_size == 4 and header[:4] in (
        ["ID", "问题", "影响", "建议确认对象"],
        ["编号", "问题", "影响", "建议确认对象"],
    ):
        return [52, 412, 259, 100]

    if column_size == 3 and header[:3] in (
        ["ID", "问题", "影响"],
        ["编号", "问题", "影响"],
    ):
        return [60, 500, 263]

    if column_size == 4 and header[:2] == ["维度", "状态"] and header[3:4] in (["说明"], ["备注"]):
        if header[2] in {"对应用例", "覆盖用例"}:
            return [107, 80, 180, 456]
        if header[2] == "用例数":
            return [107, 100, 100, 516]

    if (
        column_size == 5
        and header[0:3] == ["检索词组", "命中笔记", "判定"]
        and header[3].startswith("理由")
        and header[4] == "编入位置"
    ):
        return [100, 215, 63, 347, 100]

    if (
        column_size == 4
        and header[0:3] == ["检索词组", "命中笔记", "判定"]
        and header[3].startswith("理由")
    ):
        return [130, 250, 60, 393]

    return None


def build_table_descendant(rows: list[list[str]]) -> dict:
    """把 markdown 表格行渲成飞书 descendant 接口 payload:
    table(31) → table_cell(32) → text(2) 三层,用临时 block_id 串父子关系。
    不传 merge_info(只读,传了会报错)。空单元格用空 elements。
    """
    row_size = len(rows)
    column_size = max((len(r) for r in rows), default=1)
    cell_ids = [f"c{r}_{c}" for r in range(row_size) for c in range(column_size)]
    property_ = {"row_size": row_size, "column_size": column_size}
    column_width = infer_column_width(rows)
    if column_width and len(column_width) == column_size:
        property_["column_width"] = column_width

    descendants: list[dict] = [{
        "block_id": "tbl",
        "block_type": 31,
        "table": {"property": property_},
        "children": cell_ids,
    }]
    for r in range(row_size):
        for c in range(column_size):
            cell_id = f"c{r}_{c}"
            text_id = f"t{r}_{c}"
            content = rows[r][c] if c < len(rows[r]) else ""
            descendants.append({
                "block_id": cell_id,
                "block_type": 32,
                "table_cell": {},
                "children": [text_id],
            })
            descendants.append({
                "block_id": text_id,
                "block_type": 2,
                "text": {"elements": text_elements(content) if content else []},
            })
    return {"index": -1, "children_id": ["tbl"], "descendants": descendants}


def history_for_publish(markdown: str) -> str:
    """发布呈现:history-hits 表格砍掉「编入位置」列(飞书里用例块已裁、ID 是死引用),
    并去掉自带 h1 标题(与 append 的「历史命中摘要」h2 重复);**保持表格形式**。
    命中笔记本就一行一条(不重复);理由多点如何分行由 history-hits.md 原文决定,此处不改。
    本地 history-hits.md 不变。"""
    out = []
    for line in markdown.splitlines():
        s = line.strip()
        if s.startswith("# "):  # 去掉一级标题,标题由 build 的 h2 统一提供
            continue
        if _TABLE_ROW.match(s):
            cells = parse_table_cells(s)
            if len(cells) >= 5:  # 砍掉第 5 列(编入位置);表头/分隔/数据行同样处理
                cells = cells[:4]
            out.append("| " + " | ".join(cells) + " |")
        else:
            out.append(line)
    return "\n".join(out)


def markdown_to_renderables(markdown: str) -> list[dict]:
    """把 markdown 转成有序渲染项:普通块 dict,或表格项 {"__table__": rows}。
    普通块走 children 接口;表格项走 descendant 接口(飞书原生表格)。
    """
    renderables: list[dict] = []
    in_code = False
    code_lines: list[str] = []
    lines = markdown.splitlines()
    i, n = 0, len(lines)

    while i < n:
        raw_line = lines[i]
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                if code_lines:
                    renderables.append(code_block("\n".join(code_lines)))
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(raw_line)
            i += 1
            continue

        # markdown 表格:当前行是 | 行,紧接分隔行 → 收集整表
        if _TABLE_ROW.match(line) and i + 1 < n and _TABLE_SEP.match(lines[i + 1]):
            rows = [parse_table_cells(line)]
            i += 2  # 跳过表头行 + 分隔行
            while i < n and _TABLE_ROW.match(lines[i].rstrip()) and not _TABLE_SEP.match(lines[i]):
                rows.append(parse_table_cells(lines[i].rstrip()))
                i += 1
            renderables.append({"__table__": rows})
            continue

        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            renderables.append(make_block("heading1", line[2:].strip()))
        elif line.startswith("## "):
            renderables.append(make_block("heading2", line[3:].strip()))
        elif line.startswith("### "):
            renderables.append(make_block("heading3", line[4:].strip()))
        elif line.lstrip().startswith(("- ", "* ")):
            renderables.append(make_block("bullet", line.lstrip()[2:].strip()))
        else:
            for chunk in chunk_text(line):
                renderables.append(make_block("text", chunk))
        i += 1

    if code_lines:
        renderables.append(code_block("\n".join(code_lines)))

    return renderables


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def delivery_file_list(delivery_dir: Path) -> list[str]:
    names = ["testcases.md", "history-hits.md", "mindmap.puml"]
    existing = [name for name in names if (delivery_dir / name).exists()]
    source_meta = delivery_dir / "source" / "meta.json"
    if source_meta.exists():
        existing.append("source/meta.json")
    return existing


def validate_delivery_or_raise(delivery_dir: Path) -> None:
    """发布前强制复用交付校验器,避免把坏结构写进飞书文档。"""
    testcases = delivery_dir / "testcases.md"
    errors: list[str] = []
    cases: dict[str, str] = {}
    if not testcases.exists():
        errors.append(f"missing testcases file: {testcases}")
    else:
        _, _, cases, case_errors = validate_output.validate_testcases(testcases)
        errors.extend(case_errors)

    history = delivery_dir / "history-hits.md"
    if history.exists():
        errors.extend(validate_output.validate_history(history, cases))

    mindmap = delivery_dir / "mindmap.puml"
    if not mindmap.exists():
        errors.append(
            "缺少 mindmap.puml：飞书发布会裁掉 showcase/用例设计/APP 常驻三块正文、改由思维导图承载用例，"
            "无导图会发出不含任何用例的空文档。请先运行 scripts/md_to_mindmap.py 生成 mindmap.puml。"
        )
    else:
        errors.extend(validate_output.validate_mindmap(mindmap))

    if errors:
        detail = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"delivery validation failed before publish:\n{detail}")


def build_delivery_renderables(delivery_dir: Path) -> list[dict]:
    testcases = delivery_dir / "testcases.md"
    if not testcases.exists():
        raise FileNotFoundError(f"missing required file: {testcases}")

    mindmap = delivery_dir / "mindmap.puml"
    if not mindmap.exists():
        # 最终防线:发布固定裁掉三块用例正文、由思维导图承载,无导图会发出不含任何用例的空文档。
        # 覆盖 --skip-validate 绕过校验的路径,任何情况下都不发空用例文档。
        raise RuntimeError(
            "缺少 mindmap.puml：发布会裁掉 showcase/用例设计/APP 常驻三块正文并由思维导图承载用例，"
            "无导图将发出不含任何用例的空文档。请先运行 scripts/md_to_mindmap.py 生成 mindmap.puml。"
        )
    before_md, after_md, mindmap_no = split_testcases_for_publish(
        testcases.read_text(encoding="utf-8"), reserve_mindmap_number=mindmap.exists()
    )
    renderables = markdown_to_renderables(before_md)

    if mindmap.exists():
        title = "用例设计思维导图（PlantUML）"
        if mindmap_no:
            title = f"{mindmap_no}. {title}"
        renderables.append(make_block("heading2", title))
        renderables.append(code_block(mindmap.read_text(encoding="utf-8")))

    if after_md.strip():
        renderables.extend(markdown_to_renderables(after_md))

    history = delivery_dir / "history-hits.md"
    if history.exists():
        renderables.append(make_block("heading2", "历史命中摘要"))
        renderables.extend(markdown_to_renderables(history_for_publish(history.read_text(encoding="utf-8"))))

    renderables.append(make_block("heading2", "交付文件清单"))
    for name in delivery_file_list(delivery_dir):
        renderables.append(make_block("bullet", name))
    return renderables


def infer_title(delivery_dir: Path, explicit_title: str | None = None) -> str:
    if explicit_title:
        base = explicit_title
    else:
        meta_path = delivery_dir / "source" / "meta.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        base = str(meta.get("title") or "").strip()
        if not base:
            text = read_text_if_exists(delivery_dir / "testcases.md")
            match = re.search(r"^#\s+(.+)$", text, re.M)
            base = match.group(1).strip() if match else delivery_dir.name

    stamp = datetime.now().strftime("%Y-%m-%d %H%M")
    if base.startswith("QA测试用例｜") or base.startswith("QA 测试用例｜"):
        return f"{base}｜{stamp}"
    return f"QA测试用例｜{base}｜{stamp}"


_CREDS = None  # (app_id, app_secret, domain),懒加载
_TENANT_TOKEN = None


def _creds() -> tuple[str, str, str]:
    global _CREDS
    if _CREDS is None:
        _CREDS = lark_common.load_credentials()
    return _CREDS


def _tenant_token() -> str:
    global _TENANT_TOKEN
    if _TENANT_TOKEN:
        return _TENANT_TOKEN
    app_id, app_secret, domain = _creds()
    _TENANT_TOKEN = lark_common.tenant_token(domain, app_id, app_secret)
    return _TENANT_TOKEN


def lark_request(method: str, path: str, *, json: dict | None = None,
                 params: dict | None = None, headers: dict | None = None,
                 timeout: int = 60) -> dict:
    """自包含 Lark Open API 调用,签名兼容原 gateway.lark_request。
    凭证/HTTP 内核来自 lark_common(与 read_doc.py 共用);返回解析好的 dict。"""
    domain = _creds()[2].rstrip("/")
    url = f"{domain}/{path.lstrip('/')}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    auth = {"Authorization": f"Bearer {_tenant_token()}"}
    _, body, _ = lark_common.http(url, method.upper(), payload=json, headers=auth, timeout=timeout)
    if not isinstance(body, dict):
        return {"code": -1, "msg": f"响应非预期(凭证/网络异常,需连公司 VPN):{str(body)[:200]}"}
    return body


def import_lark_request() -> Callable[..., dict]:
    return lark_request


def ensure_lark_ok(result: dict, action: str) -> dict:
    if result.get("code") != 0:
        raise RuntimeError(f"{action} failed: code={result.get('code')} msg={result.get('msg')} data={result}")
    return result.get("data") or {}


def create_document(lark_request: Callable[..., dict], title: str, folder_token: str | None = None) -> dict:
    payload = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token
    data = ensure_lark_ok(
        lark_request("POST", "open-apis/docx/v1/documents", json=payload),
        "create docx",
    )
    document = data.get("document") or {}
    if not document.get("document_id"):
        raise RuntimeError(f"create docx response missing document_id: {data}")
    return document


def append_renderables(
    lark_request: Callable[..., dict],
    doc_id: str,
    renderables: list[dict],
    start_index: int = 0,
    on_progress: Callable[[int], None] | None = None,
) -> None:
    """按顺序追加到文档末尾:普通块累积走 children 接口(每批 40),
    表格项走 descendant 接口。都用 index=-1 追加,顺序天然不乱。

    断点续传(2026-07-08):支持从 start_index 开始;每次 API 调用成功后回调
    on_progress(已完成的 renderable 下标),供 --resume 状态落盘——中途失败不再
    只能"手删半成品整篇重发",续传从上次成功位置继续,不产生重复块。
    批次边界(表格单发、children 每批 40)与原实现一致,产出文档结构不变。
    """
    i = max(0, int(start_index))
    total = len(renderables)
    while i < total:
        item = renderables[i]
        if "__table__" in item:
            payload = build_table_descendant(item["__table__"])
            if len(payload["descendants"]) > MAX_DESCENDANTS:
                raise RuntimeError(
                    f"table too large for one descendant call: "
                    f"{len(payload['descendants'])} blocks > {MAX_DESCENDANTS}"
                )
            ensure_lark_ok(
                lark_request(
                    "POST",
                    f"open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/descendant",
                    json=payload,
                ),
                "append docx table",
            )
            i += 1
        else:
            batch: list[dict] = []
            j = i
            while j < total and "__table__" not in renderables[j] and len(batch) < 40:
                batch.append(renderables[j])
                j += 1
            ensure_lark_ok(
                lark_request(
                    "POST",
                    f"open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
                    json={"index": -1, "children": batch},
                ),
                "append docx blocks",
            )
            i = j
        if on_progress:
            on_progress(i)


def set_public_permission(
    lark_request: Callable[..., dict],
    doc_id: str,
    link_share_entity: str,
) -> None:
    if link_share_entity == "skip":
        return
    ensure_lark_ok(
        lark_request(
            "PATCH",
            f"open-apis/drive/v2/permissions/{doc_id}/public",
            params={"type": "docx"},
            json={"link_share_entity": link_share_entity},
        ),
        "set docx public permission",
    )


def resolve_wiki_parent(lark_request: Callable[..., dict], token: str) -> dict:
    data = ensure_lark_ok(
        lark_request(
            "GET",
            "open-apis/wiki/v2/spaces/get_node",
            params={"token": token},
        ),
        "resolve wiki parent",
    )
    node = data.get("node") or {}
    if not node.get("space_id") or not node.get("node_token"):
        raise RuntimeError(f"wiki parent response missing space_id/node_token: {data}")
    return node


def mount_doc_to_wiki(
    lark_request: Callable[..., dict],
    space_id: str,
    parent_node_token: str,
    doc_id: str,
) -> dict:
    payload = wiki_mount_payload(space_id, parent_node_token, doc_id)
    data = ensure_lark_ok(
        lark_request(
            "POST",
            f"open-apis/wiki/v2/spaces/{space_id}/nodes",
            json=payload,
        ),
        "mount docx into wiki parent",
    )
    return data.get("node") or data


PUBLISH_STATE_FILENAME = "publish_state.json"


def publish_state_path(delivery_dir: Path) -> Path:
    return delivery_dir / PUBLISH_STATE_FILENAME


def load_publish_state(delivery_dir: Path) -> dict | None:
    """读上次未完成发布的进度;发布成功后该文件会被删除,存在即意味着有半成品可续传。"""
    path = publish_state_path(delivery_dir)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return state if state.get("document_id") else None


def save_publish_state(delivery_dir: Path, state: dict) -> None:
    publish_state_path(delivery_dir).write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def clear_publish_state(delivery_dir: Path) -> None:
    path = publish_state_path(delivery_dir)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # 部分环境禁止删除文件(EPERM,如受保护的挂载目录):退化为清空内容——
        # load_publish_state 对无 document_id 的内容返回 None,等效"无状态"。
        # 不能让"发布已全部成功、只差删状态文件"被误报成发布失败(2026-07-08 实测踩坑)。
        try:
            path.write_text("{}\n", encoding="utf-8")
        except OSError:
            pass


def update_meta(delivery_dir: Path, info: dict) -> None:
    meta_path = delivery_dir / "source" / "meta.json"
    if not meta_path.exists():
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        meta = {}
    meta["lark_output"] = info
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(delivery_dir: Path, target: PublishTarget, title: str, permission: str,
            resume_state: dict | None = None) -> dict:
    renderables = build_delivery_renderables(delivery_dir)
    lark_request = import_lark_request()

    wiki_node = None
    if resume_state:
        # 续传:复用上次已建文档与进度,不再 create;交付内容或目标变了则拒绝续传(会写错文档)
        if resume_state.get("renderable_count") != len(renderables):
            raise PublishError(
                "resume_check",
                f"本地交付块数已变化({resume_state.get('renderable_count')} → {len(renderables)}),"
                f"不能续传;请删除 {PUBLISH_STATE_FILENAME}(并手动删除半成品文档)后整篇重发",
                resume_state.get("document_id"), resume_state.get("document_url", ""),
            )
        if resume_state.get("target_source") and resume_state["target_source"] != target.source:
            raise PublishError(
                "resume_check",
                f"发布目标已变化({resume_state['target_source']} → {target.source}),不能续传",
                resume_state.get("document_id"), resume_state.get("document_url", ""),
            )
        doc_id = resume_state["document_id"]
        doc_url = resume_state.get("document_url", "")
        title = resume_state.get("title") or title
        if resume_state.get("wiki_space_id"):
            wiki_node = {"space_id": resume_state["wiki_space_id"],
                         "node_token": resume_state["wiki_node_token"]}
        state = dict(resume_state)
        print(f"[publish] --resume: 续传文档 {doc_id},从第 {state.get('next_index', 0)}/{len(renderables)} 项继续", flush=True)
    else:
        folder_token = None
        if target.kind == "wiki_parent":
            try:
                wiki_node = resolve_wiki_parent(lark_request, target.token)
            except Exception as exc:
                raise PublishError("resolve_wiki_parent", str(exc)) from exc
        elif target.kind == "drive_folder":
            folder_token = target.token

        try:
            document = create_document(lark_request, title, folder_token=folder_token)
        except Exception as exc:
            raise PublishError("create_docx", str(exc)) from exc
        doc_id = document["document_id"]
        doc_url = document.get("url") or (f"https://{target.host}/docx/{doc_id}" if target.host else "")
        state = {
            "document_id": doc_id,
            "document_url": doc_url,
            "title": title,
            "target_source": target.source,
            "permission": permission,
            "renderable_count": len(renderables),
            "next_index": 0,
            "wiki_space_id": wiki_node.get("space_id") if wiki_node else None,
            "wiki_node_token": wiki_node.get("node_token") if wiki_node else None,
        }
        save_publish_state(delivery_dir, state)

    def on_progress(next_index: int) -> None:
        state["next_index"] = next_index
        save_publish_state(delivery_dir, state)

    try:
        append_renderables(lark_request, doc_id, renderables,
                           start_index=int(state.get("next_index", 0)), on_progress=on_progress)
    except Exception as exc:
        raise PublishError(
            "append_blocks",
            f"{exc}(已写入 {state.get('next_index', 0)}/{len(renderables)} 项;"
            f"进度已存 {PUBLISH_STATE_FILENAME},重跑加 --resume 从断点续传,勿手动重发以免重复)",
            doc_id, doc_url,
        ) from exc
    try:
        set_public_permission(lark_request, doc_id, permission)
    except Exception as exc:
        raise PublishError("set_permission", str(exc), doc_id, doc_url) from exc

    mounted_node = None
    mount_error = None
    if wiki_node:
        try:
            mounted_node = mount_doc_to_wiki(lark_request, wiki_node["space_id"], wiki_node["node_token"], doc_id)
        except RuntimeError as exc:
            # 挂载失败=发布阻塞(见 lark-output.md)：文档已建在 drive 根、内容已写,但没挂进 wiki 树。
            # 不再静默 exit 0,改为报错退出并附 document_id,供人工移动或删除半成品。
            raise PublishError("mount_wiki", str(exc), doc_id, doc_url) from exc

    result = {
        "document_id": doc_id,
        "document_url": doc_url,
        "title": title,
        "target": {
            "kind": target.kind,
            "token": target.token,
            "source": target.source,
        },
        "wiki_node": mounted_node,
        "mount_status": "mounted" if mounted_node else ("failed" if mount_error else "not_requested"),
        "mount_error": mount_error,
        "link_share_entity": None if permission == "skip" else permission,
    }
    clear_publish_state(delivery_dir)  # 发布完整成功,清除断点状态
    update_meta(delivery_dir, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish qa-testcase-design output into a new Lark docx.")
    parser.add_argument("delivery_dir", type=Path)
    parser.add_argument(
        "--target",
        default="https://wsgh3q8mwfpp.sg.larksuite.com/drive/folder/IL00fkfpolXGovdWl4FlPRe1gyg",
        help="Lark wiki parent URL or Drive folder URL/token. 默认=references/lark-output.md 约定的默认 Drive 文件夹。",
    )
    parser.add_argument("--title", help="Document title; default inferred from source/meta.json or testcases.md.")
    parser.add_argument(
        "--permission",
        default="tenant_editable",
        choices=["tenant_editable", "tenant_readable", "closed", "skip"],
        help="Link sharing permission after creation. Use skip to avoid changing permissions.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Render local payload only; do not call Lark.")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip delivery validation before publish. Only use for manual recovery of archived outputs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从上次中断的发布断点续传(复用已建文档,从 publish_state.json 记录的进度继续追加)。",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="忽略并清除上次的发布断点状态,重新建档发布(半成品文档需自行手动删除)。",
    )
    args = parser.parse_args()

    delivery_dir = args.delivery_dir.expanduser().resolve()
    target = parse_publish_target(args.target)
    title = infer_title(delivery_dir, args.title)

    # 断点状态护栏:存在未完成状态时,必须显式选择 --resume(续传)或 --fresh(重发),
    # 防止无意识重发在飞书里堆出重复半成品文档。
    resume_state = load_publish_state(delivery_dir)
    if args.fresh:
        clear_publish_state(delivery_dir)
        resume_state = None
    if args.resume and not resume_state and not args.dry_run:
        print(json.dumps({
            "status": "failed", "stage": "resume_guard", "code": None, "msg": None,
            "message": f"--resume 指定但 {PUBLISH_STATE_FILENAME} 不存在或无效,没有可续传的发布",
            "document_id": None, "document_url": None,
            "note": "直接去掉 --resume 正常发布即可",
        }, ensure_ascii=False, indent=2))
        return 1
    if resume_state and not args.resume and not args.dry_run:
        print(json.dumps({
            "status": "failed", "stage": "resume_guard", "code": None, "msg": None,
            "message": f"检测到上次未完成的发布(document_id={resume_state.get('document_id')},"
                       f"进度 {resume_state.get('next_index')}/{resume_state.get('renderable_count')})",
            "document_id": resume_state.get("document_id"),
            "document_url": resume_state.get("document_url"),
            "note": "加 --resume 从断点续传(推荐);或手动删除半成品文档后加 --fresh 重发",
        }, ensure_ascii=False, indent=2))
        return 1
    if not args.resume:
        resume_state = None
    try:
        if not args.skip_validate:
            validate_delivery_or_raise(delivery_dir)
        renderables = build_delivery_renderables(delivery_dir)
    except Exception as exc:
        failure = {
            "status": "failed",
            "stage": "validate_delivery",
            "code": None,
            "msg": None,
            "message": str(exc)[:1000],
            "document_id": None,
            "document_url": None,
            "note": "发布前本地交付校验未通过,未创建飞书文档;请先修复 testcases.md/history-hits.md/mindmap.puml",
        }
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 1

    if args.dry_run:
        tables = [r["__table__"] for r in renderables if "__table__" in r]
        print(json.dumps(
            {
                "delivery_dir": str(delivery_dir),
                "title": title,
                "target": target._asdict(),
                "block_count": sum(1 for r in renderables if "__table__" not in r),
                "table_count": len(tables),
                "table_shapes": [f"{len(t)}x{max((len(r) for r in t), default=1)}" for t in tables],
                "files": delivery_file_list(delivery_dir),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    try:
        result = publish(delivery_dir, target, title, args.permission, resume_state=resume_state)
    except Exception as exc:
        # SKILL 约定:发布失败必须报告 code/msg 并保留本地交付,不允许裸 traceback。
        msg = str(exc)
        m = re.search(r"code=(-?\w+)\s+msg=(.*?)(?:\s+data=|$)", msg, re.S)
        failure = {
            "status": "failed",
            "stage": getattr(exc, "stage", "unknown"),
            "code": m.group(1) if m else None,
            "msg": m.group(2).strip() if m else None,
            "message": msg[:500],
            "document_id": getattr(exc, "document_id", None),
            "document_url": getattr(exc, "document_url", "") or None,
            "note": "本地交付文件仍有效,无需重新生成用例;若为 append_blocks 阶段失败,进度已存 publish_state.json,"
                    "重跑加 --resume 从断点续传(不重复建档);其他阶段失败且 document_id 非空时,重发前可手动删除半成品文档",
        }
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
