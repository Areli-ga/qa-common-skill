#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_doc.py — 只读飞书文档(正文 + 表格行列 + 下载全部图片),供写用例时读图。

技术内核与 qa-knowledge-base/scripts/fetch.py 一致(blocks 接口 + 下载图 + sips 缩放),
但**只读**:输出到临时目录、不写 qa-knowledge-base、不做版本判定/入库。保证"读历史文档"与 qa-knowledge-base 同一套读法。

用法:
    python3 scripts/read_doc.py "<飞书链接或token>" [输出目录] [--out 输出目录] [--allow-partial] [--resume]

    输出目录可用位置参数或 --out 指定,二者等价(同时给时 --out 优先);未知 --xxx 参数直接报错退出,
    不会被当成目录名静默吞掉(2026-07-06 曾因此把产物写进字面名为 --out 的目录)。

    --resume(2026-07-08 断点续跑):图多/网络慢导致中途被杀时,带 --resume 重跑同一输出目录,
    会复用已落盘的 content.txt / blocks.json,并跳过 images/ 里已下载完成的图片,只补缺的部分;
    图片一律先写 .part 再原子改名,中断不会留下半截文件被误当完成。不带 --resume 行为与从前一致(全新读取)。

凭证:优先环境变量 LARK_APP_ID / LARK_APP_SECRET / LARK_DOMAIN;没有则从公司 config 服务拉取(需 VPN)。
产出:<out>/{content.txt, blocks.json, tables.md, tables.json, meta.json, images/};并打印正文 + 表格 + 图片清单供 Claude 读图。
"""
import os
import re
import sys
import json
import time
import shutil
import struct
import tempfile
import subprocess
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lark_common  # 凭证/HTTP 内核,与 publish_to_lark_doc.py 共用(同目录)

DEFAULT_OUT_ROOT = os.path.join(tempfile.gettempdir(), "qa-testcase-design")
MAX_READ_PX = 1900  # 读图工具上限 ~2000px;超过则用 sips 生成缩放副本供读图
# raw_content 里图片块只留一行裸文件名占位(如 image.png),无编号 —— 读图时无法对应 images/img-NN
IMG_PLACEHOLDER_RE = re.compile(r"^\s*\S+\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|heic|heif|ico|avif)\s*$", re.I)


def annotate_image_placeholders(content, img_meta, expected_images):
    """把 raw_content 里的裸图片占位行按出现次序替换为「【图NN｜images/img-NN.ext】」,
    使正文位置与落盘图片精确对应。占位行数与图片块数不一致时不猜,原样返回 (content, False)。"""
    if not expected_images:
        return content, False
    lines = content.splitlines()
    slots = [i for i, line in enumerate(lines) if IMG_PLACEHOLDER_RE.match(line)]
    if len(slots) != expected_images:
        return content, False
    by_index = {m["index"]: m for m in img_meta}
    for order, pos in enumerate(slots, 1):
        m = by_index.get(order)
        lines[pos] = f"【图{order:02d}｜{m['file']}】" if m else f"【图{order:02d}｜下载失败,未落盘】"
    return "\n".join(lines), True


ANNOTATED_LINE_RE = re.compile(r"^【图(\d{2})｜.*】$")


def refresh_annotated_placeholders(content, img_meta):
    """已标注过的 content.txt(如 --allow-partial 部分失败后又补图续跑)按当前 img_meta
    刷新【图NN｜...】行,修正「下载失败,未落盘」等过期标注(2026-07-08 修复:此前一经标注
    就无法更新,补下的图在正文里仍显示失败)。返回 (content, changed)。"""
    by_index = {m["index"]: m for m in img_meta}
    changed = False
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = ANNOTATED_LINE_RE.match(line.strip())
        if not m:
            continue
        idx = int(m.group(1))
        meta = by_index.get(idx)
        new = f"【图{idx:02d}｜{meta['file']}】" if meta else f"【图{idx:02d}｜下载失败,未落盘】"
        if line.strip() != new:
            lines[i] = new
            changed = True
    return "\n".join(lines), changed


def log(msg):
    print(f"[read_doc] {msg}", flush=True)


def http(url, method="GET", payload=None, headers=None, raw=False, timeout=60):
    """转发到 lark_common.http(与 publish 共用同一 HTTP 内核)。"""
    return lark_common.http(url, method=method, payload=payload, headers=headers, raw=raw, timeout=timeout)


def load_credentials():
    try:
        app_id, app_secret, domain = lark_common.load_credentials()
    except Exception as e:
        log(f"拉取 config 失败:{e};请确认已连公司 VPN,或先 export LARK_APP_ID / LARK_APP_SECRET")
        sys.exit(1)
    log("凭证:环境变量" if os.environ.get("LARK_APP_ID") else "凭证:config 服务")
    return app_id, app_secret, domain


def parse_link(s):
    """识别 wiki / docx 链接,返回 (kind, token)。裸 token 按 wiki 处理(与 fetch.py 一致)。"""
    m = re.search(r"/wiki/([A-Za-z0-9]+)", s)
    if m:
        return "wiki", m.group(1)
    m = re.search(r"/docx/([A-Za-z0-9]+)", s)
    if m:
        return "docx", m.group(1)
    m = re.search(r"/docs/([A-Za-z0-9]+)", s)
    if m:
        return "legacy-doc", m.group(1)
    return "wiki", s.strip()


def slugify(s):
    s = re.sub(r'[\\/:*?"<>|]+', " ", s or "").strip()
    s = re.sub(r"\s+", "-", s)
    return s[:60] if s else "doc"


def _image_dims(path):
    """纯 Python 解析常见图片头取 (宽, 高):PNG/JPEG/GIF/WebP;识别不了返回 (0, 0)。
    sips/PIL 都不可用时的最后兜底,保证 meta.json 的 dims 与「>6 张挑大图读」策略仍有依据。"""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
                w, h = struct.unpack(">II", head[16:24])
                return int(w), int(h)
            if head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
                return int(w), int(h)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                fmt = head[12:16]
                if fmt == b"VP8X":
                    return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
                if fmt == b"VP8L":
                    b = head[21:25]
                    return (b[0] | ((b[1] & 0x3F) << 8)) + 1, (((b[1] >> 6) | (b[2] << 2) | ((b[3] & 0x0F) << 10))) + 1
            if head[:2] == b"\xff\xd8":  # JPEG:扫 SOF 段
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        break
                    seg_len = struct.unpack(">H", f.read(2))[0]
                    if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                        f.read(1)
                        h, w = struct.unpack(">HH", f.read(4))
                        return int(w), int(h)
                    f.seek(seg_len - 2, 1)
    except Exception:
        pass
    return 0, 0


_NO_SCALER_WARNED = False


def downscale_for_read(path, max_px=MAX_READ_PX):
    """超大图生成缩放副本供读图;原图保留。返回 (副本文件名 or None, (宽, 高))。

    缩放器三级降级(2026-07-08 跨平台修复,此前 sips 为 macOS 专属、Linux/CI 静默退化):
      1. sips(macOS 自带)  2. PIL/Pillow(若环境已装,不新增强制依赖)
      3. 都没有 → 纯 Python 解析图片头取尺寸,不缩放,超大图一次性告警(读图工具可能拒读 >2000px)。"""
    global _NO_SCALER_WARNED
    base, ext = os.path.splitext(path)
    rd = base + ".read" + ext
    if shutil.which("sips"):
        try:
            out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                                 capture_output=True, text=True, timeout=20).stdout
            w = h = 0
            for line in out.splitlines():
                mw = re.search(r"pixelWidth:\s*(\d+)", line)
                mh = re.search(r"pixelHeight:\s*(\d+)", line)
                if mw:
                    w = int(mw.group(1))
                if mh:
                    h = int(mh.group(1))
            if max(w, h) <= max_px:
                return None, (w, h)
            subprocess.run(["sips", "-Z", str(max_px), path, "--out", rd],
                           capture_output=True, text=True, timeout=30)
            return os.path.basename(rd), (w, h)
        except Exception as e:
            log(f"  sips 缩放失败({e}),尝试 PIL/头解析兜底")
    try:
        from PIL import Image  # 可选依赖:装了就用,没装走头解析
        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) <= max_px:
                return None, (int(w), int(h))
            scale = max_px / max(w, h)
            resized = im.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            resized.save(rd)
            return os.path.basename(rd), (int(w), int(h))
    except ImportError:
        pass
    except Exception as e:
        log(f"  PIL 缩放失败({e}),退回头解析")
    w, h = _image_dims(path)
    if max(w, h) > max_px and not _NO_SCALER_WARNED:
        _NO_SCALER_WARNED = True
        log(f"  ⚠️ 本机无 sips 也无 PIL:超大图(>{max_px}px)不生成 .read 缩放副本,读图工具可能拒读原图 —— 建议安装 Pillow 或在 macOS 上运行")
    return None, (w, h)


TEXT_FIELDS = (
    "text",
    "bullet",
    "ordered",
    "heading1",
    "heading2",
    "heading3",
    "heading4",
    "heading5",
    "heading6",
    "page",
    "code",
)


def rich_text_content(value):
    chunks = []

    def walk(item):
        if isinstance(item, dict):
            text_run = item.get("text_run")
            if isinstance(text_run, dict):
                content = text_run.get("content")
                if content:
                    chunks.append(content)
            mention_doc = item.get("mention_doc")
            if isinstance(mention_doc, dict) and mention_doc.get("title"):
                chunks.append(mention_doc["title"])
            mention_user = item.get("mention_user")
            if isinstance(mention_user, dict) and mention_user.get("name"):
                chunks.append(mention_user["name"])
            equation = item.get("equation")
            if isinstance(equation, dict) and equation.get("content"):
                chunks.append(equation["content"])
            for key, val in item.items():
                if key in {"text_run", "mention_doc", "mention_user", "equation"}:
                    continue
                if key in {"elements", "content"} or isinstance(val, (dict, list)):
                    walk(val)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return "".join(chunks).strip()


def block_text(block, by_id, seen=None):
    if not block:
        return ""
    seen = seen or set()
    block_id = block.get("block_id")
    if block_id in seen:
        return ""
    if block_id:
        seen.add(block_id)

    parts = []
    for field in TEXT_FIELDS:
        if field in block:
            text = rich_text_content(block.get(field))
            if text:
                parts.append(text)
    for child_id in block.get("children") or []:
        child = by_id.get(child_id)
        text = block_text(child, by_id, seen)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


# block_type → 人类可读名(仅用于"未解析块"告警;正文/表格/图片已单独处理)
UNREAD_BLOCK_TYPES = {
    # 电子表格 Sheet(30) 已由 fetch_embedded_sheets 实时抓取、并入 tables.md,不再算"未解析";
    # 多维表格 Bitable(33) 同理可抓,待 Bitable 样本验证后再加,当前仍告警。
    33: "多维表格 Bitable",
    40: "同步块",
    41: "分栏",
    23: "文件附件",
    26: "内嵌网页/iframe",
    43: "任务",
    45: "OKR",
}


def detect_unread_blocks(blocks):
    """统计正文/表格(31)/图片(27) 之外、可能承载测试信息却未被读取的容器块。
    返回 [(名称, 数量)],供"读取风险"提示,不静默跳过(违背保真读取原则)。"""
    counter = Counter()
    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = b.get("block_type")
        if bt in UNREAD_BLOCK_TYPES:
            counter[UNREAD_BLOCK_TYPES[bt]] += 1
    return sorted(counter.items(), key=lambda kv: -kv[1])


def extract_tables(blocks):
    by_id = {b.get("block_id"): b for b in blocks if isinstance(b, dict) and b.get("block_id")}
    tables = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("block_type") != 31:
            continue
        table = block.get("table") or {}
        prop = table.get("property") or {}
        cells = table.get("cells") or block.get("children") or []
        column_count = int(prop.get("column_size") or len(prop.get("column_width") or []) or 0)
        if not column_count:
            column_count = len(cells) or 1
        row_count = int(prop.get("row_size") or 0)
        if not row_count:
            row_count = (len(cells) + column_count - 1) // column_count if cells else 0

        rows = []
        for row_index in range(row_count):
            row = []
            for column_index in range(column_count):
                cell_index = row_index * column_count + column_index
                cell_id = cells[cell_index] if cell_index < len(cells) else None
                row.append(block_text(by_id.get(cell_id), by_id).replace("\n\n", "\n"))
            rows.append(row)

        tables.append({
            "index": len(tables) + 1,
            "block_id": block.get("block_id"),
            "row_count": row_count,
            "column_count": column_count,
            "rows": rows,
            "merge_info": prop.get("merge_info") or [],
        })
    return tables


def md_cell(value):
    text = str(value or "").replace("|", "\\|").replace("\n", "<br>")
    return text if text else " "


def render_md_table(rows):
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return "（空表）\n"
    out = [
        "| " + " | ".join(f"C{i + 1}" for i in range(width)) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in rows:
        padded = list(row) + [""] * (width - len(row))
        out.append("| " + " | ".join(md_cell(cell) for cell in padded) + " |")
    return "\n".join(out) + "\n"


def write_tables(out, tables):
    with open(os.path.join(out, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "tables.md"), "w", encoding="utf-8") as f:
        f.write("# 表格抽取\n\n")
        if not tables:
            f.write("未发现表格块。\n")
        for table in tables:
            f.write(f"## 表格 {table['index']} ({table['row_count']}x{table['column_count']})\n\n")
            f.write(f"- block_id: `{table['block_id']}`\n")
            if table.get("merge_info"):
                n = len(table["merge_info"])
                f.write(
                    f"- ⚠️ **本表含 {n} 处合并单元格**：Markdown 无法表达合并,下方按行列网格展开,"
                    f"跨合并区的值可能重复填充或留空、行列可能与原表有出入;涉及此表的关键判定请核对"
                    f"原文档或 `tables.json` 的 `merge_info`。\n"
                )
            f.write("\n")
            f.write(render_md_table(table["rows"]))
            f.write("\n")


def cell_to_text(cell):
    """飞书 Sheets v2 values 单元格 → 纯文本。cell 可能是 None / 数字 / 字符串 / 富文本段列表。"""
    if cell is None:
        return ""
    if isinstance(cell, list):
        out = []
        for seg in cell:
            if isinstance(seg, dict):
                out.append(str(seg.get("text") or seg.get("link") or seg.get("mentionText") or ""))
            elif seg is not None:
                out.append(str(seg))
        return "".join(out).strip()
    return str(cell).strip()


def render_sheet_md(values):
    """内嵌 Sheet 的二维 values → Markdown 表格(首行作表头)。"""
    width = max((len(r) for r in values), default=0)
    if width == 0:
        return "（空表）\n"

    def row_md(row):
        padded = [cell_to_text(c) for c in row] + [""] * (width - len(row))
        return "| " + " | ".join(md_cell(c) for c in padded) + " |"

    lines = [row_md(values[0]), "| " + " | ".join("---" for _ in range(width)) + " |"]
    for row in values[1:]:
        lines.append(row_md(row))
    return "\n".join(lines) + "\n"


def fetch_embedded_sheets(blocks, domain, auth):
    """抓取文档内嵌电子表格(block_type 30)内容。块含 sheet.token=<spreadsheet_token>_<sheet_id>,
    调 Sheets v2 values 读整表。读不了则记失败原因(降级,不中止、不静默丢)。返回 (results, failures)。
    注:内嵌多维表格 Bitable(33) 同理可用 /bitable/v1/apps/{app_token}/tables/{table_id}/records 抓取,
    待有 Bitable 样本验证后再加,当前仍走"未解析块"告警。"""
    results, failures = [], []
    for b in blocks:
        if not isinstance(b, dict) or b.get("block_type") != 30:
            continue
        tk = ((b.get("sheet") or {}).get("token") or "").strip()
        ss, _, sid = tk.partition("_")
        if not ss or not sid:
            failures.append({"token": tk, "reason": "token 非 <spreadsheet>_<sheet_id> 格式,无法定位"})
            continue
        st, body, _ = http(f"{domain}/open-apis/sheets/v2/spreadsheets/{ss}/values/{sid}", headers=auth)
        code = body.get("code") if isinstance(body, dict) else None
        if st != 200 or code != 0:
            msg = body.get("msg") if isinstance(body, dict) else str(body)[:120]
            failures.append({"token": tk, "reason": f"读取失败 HTTP={st} code={code} msg={msg}"})
            continue
        vr = (body.get("data") or {}).get("valueRange") or {}
        values = vr.get("values") or []
        results.append({
            "token": tk, "spreadsheet": ss, "sheet_id": sid,
            "range": vr.get("range", ""), "rows": len(values),
            "md": render_sheet_md(values),
        })
    return results, failures


def append_embedded_sheets_md(out, results, failures):
    """把抓取到的内嵌电子表格追加进 tables.md(Claude 读 tables.md 即含内嵌表内容,不必另开文件)。"""
    if not results and not failures:
        return
    with open(os.path.join(out, "tables.md"), "a", encoding="utf-8") as f:
        f.write("\n# 内嵌电子表格（Sheet，从文档内嵌表格实时抓取）\n\n")
        for r in results:
            f.write(f"## 内嵌表 {r['spreadsheet']}/{r['sheet_id']}（range {r['range']}，{r['rows']} 行）\n\n")
            f.write(r["md"])
            f.write("\n")
        for fl in failures:
            f.write(f"## ⚠️ 内嵌表读取失败：`{fl['token']}`\n\n")
            f.write(f"- 原因：{fl['reason']}\n- **请人工打开原文档查看该内嵌表格,可能含测试点(如埋点定义)**\n\n")


def _fetch_blocks(domain, doc_id, auth, out):
    """分页拉取全部 blocks 并落盘 blocks.json(从 main 提取,供 --resume 复用判断)。"""
    blocks, page_token = [], None
    while True:
        url = f"{domain}/open-apis/docx/v1/documents/{doc_id}/blocks?page_size=500&document_revision_id=-1"
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        _, br, _ = http(url, headers=auth)
        if br.get("code") != 0:
            log(f"blocks 失败 {br.get('code')} {br.get('msg')}")
            sys.exit(1)
        d = br.get("data") or {}
        blocks += d.get("items") or []
        if d.get("has_more") and not d.get("page_token"):
            log("⚠️ blocks 分页 has_more=true 但缺 page_token,可能有内容块未取全 —— 请核对文档完整性(勿静默当作已读全)")
            break
        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break
    with open(os.path.join(out, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)
    return blocks


def main():
    usage = ('用法: python3 scripts/read_doc.py "<飞书链接或token>" [输出目录] [--out 输出目录] [--allow-partial] [--resume]\n'
             '  提示: 建议贴完整 /wiki/ 或 /docx/ URL; 裸 token 默认按 wiki 解析, docx 裸 token 会被误判为 wiki 而失败\n'
             '  --resume: 中断后续跑同一输出目录,复用已落盘正文/blocks/图片,只补缺')
    args = sys.argv[1:]
    allow_partial = "--allow-partial" in args
    resume = "--resume" in args
    args = [a for a in args if a not in ("--allow-partial", "--resume")]
    out_dir = None
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            log(f"--out 后必须跟输出目录。{usage}")
            sys.exit(1)
        out_dir = args[i + 1]
        args = args[:i] + args[i + 2:]
    unknown = [a for a in args if a.startswith("--")]
    if unknown:
        log(f"未知参数:{unknown}。{usage}")
        sys.exit(1)
    if not args:
        log(usage)
        sys.exit(1)
    link = args[0]
    kind, token = parse_link(link)
    log(f"输入={link!r} → kind={kind} token={token}")
    if kind == "legacy-doc":
        log("检测到旧版 /docs/ 链接。当前脚本只支持飞书 wiki/docx 文档；请提供新版 /wiki/ 或 /docx/ 链接，避免把旧 token 当 wiki 误读。")
        sys.exit(1)

    app_id, app_secret, domain = load_credentials()
    domain = domain.rstrip("/")

    _, tok, _ = http(f"{domain}/open-apis/auth/v3/tenant_access_token/internal", "POST",
                     {"app_id": app_id, "app_secret": app_secret})
    token_str = tok.get("tenant_access_token")
    if not token_str:
        log(f"获取 tenant_access_token 失败:{tok}")
        sys.exit(1)
    auth = {"Authorization": f"Bearer {token_str}"}
    log("token ok")

    # 解析文档 id + 标题
    if kind == "wiki":
        _, nr, _ = http(f"{domain}/open-apis/wiki/v2/spaces/get_node?token={token}", headers=auth)
        node = (nr.get("data") or {}).get("node") or {}
        doc_id, title = node.get("obj_token"), node.get("title") or "untitled"
        if not doc_id:
            log(f"解析 wiki node 失败(权限/链接?):{nr}")
            sys.exit(1)
    else:
        doc_id, title = token, None

    if out_dir and len(args) > 1 and args[1] != out_dir:
        log(f"⚠️ 同时给了 --out 和位置参数输出目录,以 --out 为准({out_dir}),忽略位置参数({args[1]})")
    out = out_dir or (args[1] if len(args) > 1 else os.path.join(DEFAULT_OUT_ROOT, slugify(title or token)))
    imgdir = os.path.join(out, "images")
    # 清理上次残留的旧图:图片按 img-NN 序号命名,重跑若图片数变化会残留旧序号文件,
    # 下游按目录读图会吃到过期图。每次读取前清空 images/ 下旧文件(只删文件、不递归删目录)。
    # --resume 时不清理:已下载的图是续跑要复用的进度。
    if os.path.isdir(imgdir) and resume:
        log("--resume: 保留 images/ 已下载图片,续跑只补缺")
    if os.path.isdir(imgdir) and not resume:
        removed = 0
        for old in os.listdir(imgdir):
            op = os.path.join(imgdir, old)
            if os.path.isfile(op):
                try:
                    os.remove(op)
                    removed += 1
                except OSError:
                    pass
        if removed:
            log(f"清理旧图 {removed} 个(避免残留过期图片)")
    os.makedirs(imgdir, exist_ok=True)
    log(f"输出目录:{out}")

    # 正文(--resume 且已落盘则复用,不重新拉取)
    content_path = os.path.join(out, "content.txt")
    if resume and os.path.isfile(content_path) and os.path.getsize(content_path) > 0:
        with open(content_path, encoding="utf-8") as f:
            content = f.read()
        log(f"--resume: 复用已落盘 content.txt({len(content)} 字符)")
    else:
        _, rc, _ = http(f"{domain}/open-apis/docx/v1/documents/{doc_id}/raw_content?lang=0", headers=auth)
        if rc.get("code") != 0:
            log(f"raw_content 失败 {rc.get('code')} {rc.get('msg')}")
            sys.exit(1)
        content = (rc.get("data") or {}).get("content", "")
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)
        log(f"raw_content {len(content)} 字符")
    if title is None:
        title = (content.splitlines() or ["untitled"])[0][:60]
    log(f"标题={title!r}")

    # blocks(分页;--resume 且已落盘则复用)
    blocks_path = os.path.join(out, "blocks.json")
    if resume and os.path.isfile(blocks_path) and os.path.getsize(blocks_path) > 0:
        try:
            with open(blocks_path, encoding="utf-8") as f:
                blocks = json.load(f)
            log(f"--resume: 复用已落盘 blocks.json({len(blocks)} 个块)")
        except (json.JSONDecodeError, OSError):
            log("--resume: blocks.json 损坏,重新拉取")
            blocks = _fetch_blocks(domain, doc_id, auth, out)
    else:
        blocks = _fetch_blocks(domain, doc_id, auth, out)
    log(f"blocks {len(blocks)} 个;类型分布 {dict(Counter(b.get('block_type') for b in blocks))}")

    table_items = extract_tables(blocks)
    write_tables(out, table_items)
    log(f"表格抽取 {len(table_items)} 个;已写 tables.md / tables.json")

    # 抓取内嵌电子表格(block_type 30):PRD 常把埋点/字段规格放进内嵌 Sheet,不抓会整表丢失
    embedded, sheet_fail = fetch_embedded_sheets(blocks, domain, auth)
    append_embedded_sheets_md(out, embedded, sheet_fail)
    if embedded or sheet_fail:
        extra = f",失败 {len(sheet_fail)} 个(已在 tables.md 标注待人工补看)" if sheet_fail else ""
        log(f"内嵌电子表格:抓取成功 {len(embedded)} 个{extra} → 已并入 tables.md")

    unread = detect_unread_blocks(blocks)
    if unread:
        parts = ", ".join(f"{name}×{cnt}" for name, cnt in unread)
        log(f"⚠️ 发现未解析内容块:{parts} —— 正文/表格/图片之外的内容未读取,可能漏测点")

    # 下载图片(block_type 27),统计表格(31)
    imgs = [b for b in blocks if b.get("block_type") == 27]
    tables = len(table_items)
    log(f"图片块 {len(imgs)} 个 / 表格块 {tables} 个;下载图片中...")
    img_meta = []
    failures = []
    for i, b in enumerate(imgs, 1):
        # --resume: 该序号图片已完整落盘(非 .part、非 .read 副本)则直接复用,不重新下载
        if resume:
            done = [f for f in os.listdir(imgdir)
                    if f.startswith(f"img-{i:02d}.") and ".read." not in f and not f.endswith(".part")]
            if done:
                path = os.path.join(imgdir, done[0])
                read_name, dims = downscale_for_read(path)
                entry = {"index": i, "file": f"images/{done[0]}", "dims": list(dims)}
                if read_name:
                    entry["read_file"] = f"images/{read_name}"
                img_meta.append(entry)
                log(f"  图{i:02d} --resume 复用已下载 {done[0]}")
                continue
        tk = (b.get("image") or {}).get("token")
        if not tk:
            msg = f"图{i} 缺 image.token"
            failures.append({"index": i, "reason": msg})
            log(f"  {msg}")
            if not allow_partial:
                write_meta(out, title, doc_id, token, content, blocks, img_meta, len(imgs), tables, failures)
                log("图片未完整下载 —— 默认中止;若接受部分读取,重跑时加 --allow-partial")
                sys.exit(1)
            continue
        st, body, hdrs = 0, b"", None
        for attempt in range(3):
            st, body, hdrs = http(f"{domain}/open-apis/drive/v1/medias/{tk}/download", headers=auth, raw=True)
            if st == 200:
                break
            log(f"  图{i} 下载失败(第 {attempt+1}/3 次)st={st},2s 后重试...")
            time.sleep(2)
        if st != 200:
            msg = f"图{i} 下载失败 HTTP={st}"
            failures.append({"index": i, "reason": msg})
            log(f"  {msg}")
            if not allow_partial:
                write_meta(out, title, doc_id, token, content, blocks, img_meta, len(imgs), tables, failures)
                log("图片未完整下载 —— 默认中止;若接受部分读取,重跑时加 --allow-partial")
                sys.exit(1)
            continue
        ct = (hdrs or {}).get("Content-Type", "image/png")
        ext = ct.split("/")[-1].split(";")[0] if "/" in ct else "png"
        fn = f"img-{i:02d}.{ext}"
        path = os.path.join(imgdir, fn)
        # 先写 .part 再原子改名:中断不会留下半截文件被 --resume 误当完成
        tmp_path = path + ".part"
        with open(tmp_path, "wb") as f:
            f.write(body)
        os.replace(tmp_path, path)
        read_name, dims = downscale_for_read(path)
        entry = {"index": i, "file": f"images/{fn}", "dims": list(dims)}
        if read_name:
            entry["read_file"] = f"images/{read_name}"
        img_meta.append(entry)

    log(f"图片下载完成 {len(img_meta)}/{len(imgs)} 张")

    if imgs and re.search(r"【图\d{2}｜", content):
        # 续跑场景:content.txt 已标注过编号 → 按本次下载结果刷新(补下的图不再显示"下载失败")
        content, annotated = refresh_annotated_placeholders(content, img_meta)
        log("content.txt 已含图片编号标注:" + ("已按本次下载结果刷新" if annotated else "与本次下载结果一致,无需更新"))
    else:
        content, annotated = annotate_image_placeholders(content, img_meta, len(imgs))
    if annotated:
        with open(os.path.join(out, "content.txt"), "w", encoding="utf-8") as f:
            f.write(content)
        log("content.txt 图片占位已标注编号(【图NN｜images/img-NN】,与图片清单一一对应)")
    elif imgs:
        log("图片占位行数与图片块数不一致,未标注编号;读图请按 meta.json images 顺序对应")

    meta = write_meta(out, title, doc_id, token, content, blocks, img_meta, len(imgs), tables, failures)

    # 打印清单供 Claude 读图
    print("\n==== 读取完成 ====")
    print(f"标题 : {title}")
    print(f"图/表: {len(img_meta)}/{len(imgs)} 图 / {tables} 表")
    print(f"完整 : {meta['complete']}")
    print(f"目录 : {out}")
    if table_items:
        print(f"表格 : {os.path.join(out, 'tables.md')}")
    unread = detect_unread_blocks(blocks)
    if failures or unread:
        print("\n==== 读取风险 ====")
        for item in failures:
            print(f"  图{item['index']:02d}: {item['reason']}")
        for name, cnt in unread:
            print(f"  未解析块: {name}×{cnt}(正文/表格/图片之外,内容未读取 —— 若含测试点需人工补看原文档)")
    if img_meta:
        if len(img_meta) <= 6:
            read_hint = "≤6 张: Claude 请全读;超大图读 read_file"
        else:
            read_hint = ">6 张: Claude 请优先读 UI 状态/流程/字段/配置/异常关键图;其余登记未读"
        print(f"\n==== 图片清单({read_hint})====")
        for m in img_meta:
            rf = m.get("read_file", m["file"])
            print(f"  图{m['index']:02d} {m['dims'][0]}x{m['dims'][1]}  读: {os.path.join(out, rf)}")
    print("\n==== RAW CONTENT(全文)====")
    print(content)


def write_meta(out, title, doc_id, token, content, blocks, img_meta, expected_images, tables, failures):
    meta = {
        "title": title,
        "doc_id": doc_id,
        "token": token,
        "raw_content_chars": len(content),
        "blocks": len(blocks),
        "tables": tables,
        "table_files": ["tables.md", "tables.json"],
        "images_expected": expected_images,
        "images_downloaded": len(img_meta),
        "images": img_meta,
        "failures": failures,
        "complete": not failures and len(img_meta) == expected_images,
    }
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    main()
