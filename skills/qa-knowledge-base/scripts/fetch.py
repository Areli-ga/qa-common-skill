#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch.py — ingest 第①步:抓取一篇飞书需求文档(正文 + 正文表格 + 内嵌 Sheet/多维表 + 全部图片)存进 raw/<标题>/。

用法:
    python3 scripts/fetch.py "<飞书链接或token>" [版本号]

版本来源(对应 SKILL.md):
    - 给了版本号  → 用你的(权威)。
    - 没给        → 从文档提取候选(基本信息"版本号"字段 / figma 链接 / 正文 VX.X);
                    候选 major.minor 一致 → 取最具体的;冲突 → version=null 标"待确认",列出候选,交 Claude/你定。

凭证:优先环境变量 LARK_APP_ID / LARK_APP_SECRET / LARK_DOMAIN;
      没有则从公司 config 服务拉取(需 VPN)。

产出:raw/<slug>/{content.txt, blocks.json, images/, sheets.json(有内嵌表格时), meta.json};
     并把正文 + 版本判定打印出来供下一步(读图/提炼)用。
     ⚠️ 内嵌 Sheet(block_type=30)/ 多维表(block_type=18)的内容**既不在 content.txt 也不在 blocks.json**
        (块里只有 token),全部落在 sheets.json —— 提炼前必须读它,否则整段埋点表/文案表会丢。
"""
import os
import re
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from collections import Counter

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ROOT = os.path.join(KB_ROOT, "raw")
CONFIG_URL = "https://skill-config.giggletools.com/api/config"
MAX_READ_PX = 1900  # 读图工具上限 ~2000px;超过则用 sips 生成缩放副本供读图


def log(msg):
    print(f"[fetch] {msg}", flush=True)


def http(url, method="GET", payload=None, headers=None, raw=False, timeout=60):
    h = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        h.update(headers)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if raw:
                return r.status, body, dict(r.headers)
            return r.status, json.loads(body.decode("utf-8")), None
    except urllib.error.HTTPError as e:
        b = e.read()
        if raw:
            return e.code, b, dict(e.headers)
        try:
            return e.code, json.loads(b.decode("utf-8")), None
        except Exception:
            return e.code, {"_raw": b.decode("utf-8", "replace")[:300]}, None
    except (urllib.error.URLError, OSError) as e:
        # 网络层异常(SSL 握手超时 / 连接失败 / 读超时):不让脚本崩溃,返回 st=0 交调用方处理(可重试)
        if raw:
            return 0, b"", None
        return 0, {"_neterr": str(e)}, None


def load_credentials():
    app_id = os.environ.get("LARK_APP_ID", "")
    app_secret = os.environ.get("LARK_APP_SECRET", "")
    domain = os.environ.get("LARK_DOMAIN", "")
    if app_id and app_secret:
        log("凭证:来自环境变量")
        return app_id, app_secret, domain or "https://open.feishu.cn"
    log("环境变量无凭证,改从 config 服务拉取(需公司 VPN)...")
    try:
        req = urllib.request.Request(CONFIG_URL, headers={"User-Agent": "curl/8.4.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cfg = json.loads(r.read().decode("utf-8"))
        log("config 服务凭证拉取成功")
        return cfg.get("LARK_APP_ID", ""), cfg.get("LARK_APP_SECRET", ""), cfg.get("LARK_DOMAIN", "https://open.feishu.cn")
    except Exception as e:
        log(f"拉取 config 失败:{e}")
        log("请确认已连公司 VPN,或先 export LARK_APP_ID / LARK_APP_SECRET")
        sys.exit(1)


def extract_token(s):
    """从完整 wiki 链接提取 node token,或直接当作 token。"""
    m = re.search(r"/wiki/([A-Za-z0-9]+)", s)
    return m.group(1) if m else s.strip()


def slugify(s):
    s = re.sub(r'[\\/:*?"<>|]+', " ", s or "").strip()
    s = re.sub(r"\s+", "-", s)
    return s[:60] if s else "doc"


# 读图可读性判据:**只看缩放比例**(= MAX_READ_PX / 长边),不看长宽比、也不看短边像素。
# 实测标定(2026-08-28,真读同一批图验证):
#   缩到 12.5%(15146×2316)→ 只剩布局轮廓,**一个字读不出**;
#   缩到 20%  (9556×1347) → 标题、榜单行、按钮文案都读得出;
#   缩到 53%  (3568×750)  → 完全清晰;
#   缩到 91%  (2086×220,原图本身就扁)→ 照样可读。
# 所以「长宽比≥6」和「短边<900px」这两个判据都是错的 —— 文字是按比例缩小的,只有比例说了算。
UNREADABLE_SCALE = 0.15   # < 15%:确定读不出,不生成副本、不读、不猜
MARGINAL_SCALE = 0.25     # 15–25%:灰区,生成副本但提示"读不清就如实标注"


def readability(w, h, max_px=MAX_READ_PX):
    """返回 (等级, 缩放比例)。等级 ∈ {'ok', 'marginal', 'unreadable'}。"""
    long_side = max(w, h)
    if long_side <= 0:
        return "ok", 1.0
    if long_side <= max_px:
        return "ok", 1.0
    scale = max_px / long_side
    if scale < UNREADABLE_SCALE:
        return "unreadable", scale
    if scale < MARGINAL_SCALE:
        return "marginal", scale
    return "ok", scale


def write_unreadable_marker(path, w, h, scale):
    """在不可读的原图旁边落一个同名标记文件。

    为什么光靠 meta.json + SKILL.md 不够:原图**本身还在**,读图工具会自动把它压到 ~2000px 再显示,
    压出来和那条糊掉的细条一模一样 —— 后续会话直接去读原图,照样会拿到糊图然后从布局形状瞎猜。
    标记文件跟原图并排放,`ls images/` 一眼就看见,是"看到就知道别读"的前置拦截。"""
    marker = os.path.splitext(path)[0] + ".UNREADABLE.txt"
    with open(marker, "w", encoding="utf-8") as f:
        f.write(
            f"❌ 这张图不可读,不要读、不要猜。\n\n"
            f"原图      : {os.path.basename(path)}\n"
            f"原始尺寸  : {w} x {h}\n"
            f"缩放比例  : 缩到 {scale:.0%} 才能进读图工具(上限 {MAX_READ_PX}px)\n"
            f"判定依据  : 缩放比例 < {UNREADABLE_SCALE:.0%} —— 文字按比例缩小,此比例下正文字号只剩几个像素,\n"
            f"            实测同类图(15146x2316,缩到 13%)只剩布局轮廓,一个字读不出。\n\n"
            f"注意:直接打开原图也没用 —— 读图工具会自动把它压到 ~2000px,结果同样糊。\n\n"
            f"笔记里请如实写:「原图 {w}x{h},缩放后仅 {scale:.0%},文字不可读,未读取"
            f"(原图存档:images/{os.path.basename(path)})」。\n"
            f"**严禁从布局形状推断内容** —— 猜出来的描述会以事实身份进笔记,比留空危险得多。\n"
        )
    return marker


def downscale_for_read(path, max_px=MAX_READ_PX):
    """超大图(读图工具上限 ~2000px)用 macOS sips 生成缩放副本供读图;原图保留为事实来源。
    返回 (副本文件名 or None, (宽, 高))。"""
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
        level, scale = readability(w, h, max_px)
        if level == "unreadable":
            # 生成了也读不出,只会诱导"从布局形状瞎猜" —— 不生成,并就地落一个前置拦截标记
            mk = write_unreadable_marker(path, w, h, scale)
            log(f"  {os.path.basename(path)} {w}x{h} 缩放后仅 {scale:.0%},文字不可读 "
                f"→ 不生成副本,已落标记 {os.path.basename(mk)}")
            return None, (w, h)
        base, ext = os.path.splitext(path)
        rd = base + ".read" + ext
        subprocess.run(["sips", "-Z", str(max_px), path, "--out", rd],
                       capture_output=True, text=True, timeout=30)
        return os.path.basename(rd), (w, h)
    except Exception as e:
        log(f"  缩放失败({e}),读图将退回原图")
        return None, (0, 0)


def col_letter(n):
    """列序号 → A1 记法列名:1→A、26→Z、27→AA(表宽超 Z 时不会截断)。"""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def flatten_cell(c):
    """把单元格压成纯文本 / 标量。飞书单元格有三种非标量形态:
    ① 富文本段数组 [{type:text, text:..., segmentStyle:{...}}, ...]
    ② 图片 dict {fileToken, link, text, ...}  ③ @人 dict {en_name, link, mentionType, ...}
    只保留文字与链接(样式对测试无价值),避免原料被样式噪音淹没。"""
    if isinstance(c, list):
        parts = []
        for seg in c:
            if isinstance(seg, dict):
                parts.append(str(seg.get("text") or seg.get("en_name") or seg.get("link") or ""))
            else:
                parts.append(str(seg))
        return "".join(parts)
    if isinstance(c, dict):
        return c.get("text") or c.get("en_name") or c.get("link") or json.dumps(c, ensure_ascii=False)
    return c


def trim_grid(values):
    """裁掉尾部整行 / 整列空白(表格网格大小 ≠ 实际内容大小,不裁会拖出成片 null)。"""
    def blank(v):
        return v is None or (isinstance(v, str) and not v.strip())
    rows = [list(r) for r in values]
    while rows and all(blank(c) for c in rows[-1]):
        rows.pop()
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [None] * (width - len(r)) for r in rows]
    while width > 0 and all(blank(r[width - 1]) for r in rows):
        width -= 1
        rows = [r[:width] for r in rows]
    return rows


def fetch_sheet_block(domain, auth, token, meta_cache):
    """内嵌电子表格(block_type=30)。block token 形如 <spreadsheet_token>_<sheet_id>。
    先读 metainfo 拿真实行列数构造精确 range —— 固定 A1:Z300 会「宽表截断 + 空表填 null」。"""
    sp, sid = token.rsplit("_", 1)
    if sp not in meta_cache:
        st, r, _ = http(f"{domain}/open-apis/sheets/v2/spreadsheets/{sp}/metainfo", headers=auth)
        if r.get("code") != 0:
            return None, f"metainfo 失败 st={st} code={r.get('code')} msg={r.get('msg')}"
        meta_cache[sp] = {s.get("sheetId"): s for s in ((r.get("data") or {}).get("sheets") or [])}
    info = meta_cache[sp].get(sid) or {}
    rc, cc = int(info.get("rowCount") or 0), int(info.get("columnCount") or 0)
    if rc <= 0 or cc <= 0:
        return {"token": token, "spreadsheet_token": sp, "sheet_id": sid,
                "title": info.get("title") or sid, "row_count": rc, "column_count": cc,
                "range": "", "values": []}, None
    rng = f"{sid}!A1:{col_letter(cc)}{rc}"
    # 按文档里「人看到的样子」取值:不加这两个参数,时间会变成表格序列值(14:00 → 0.5833)、
    # 百分比会变成小数(70.60% → 0.706),落进原料层就是错的事实。
    q = "?dateTimeRenderOption=FormattedString&valueRenderOption=FormattedValue"
    st, r, _ = http(f"{domain}/open-apis/sheets/v2/spreadsheets/{sp}/values/{urllib.parse.quote(rng)}{q}",
                    headers=auth, timeout=90)
    if r.get("code") != 0:
        return None, f"values 失败 st={st} code={r.get('code')} msg={r.get('msg')} range={rng}"
    raw_vals = ((r.get("data") or {}).get("valueRange") or {}).get("values") or []
    vals = trim_grid([[flatten_cell(c) for c in row] for row in raw_vals])
    return {"token": token, "spreadsheet_token": sp, "sheet_id": sid,
            "title": info.get("title") or sid, "row_count": rc, "column_count": cc,
            "range": rng, "values": vals}, None


def fetch_bitable_block(domain, auth, token):
    """内嵌多维表格(block_type=18)。block token 形如 <app_token>_<table_id>。"""
    app, tbl = token.rsplit("_", 1)
    st, fr, _ = http(f"{domain}/open-apis/bitable/v1/apps/{app}/tables/{tbl}/fields?page_size=100", headers=auth)
    if fr.get("code") != 0:
        return None, f"fields 失败 st={st} code={fr.get('code')} msg={fr.get('msg')}"
    fields = [f.get("field_name") for f in ((fr.get("data") or {}).get("items") or [])]
    records, page_token = [], None
    while True:
        url = f"{domain}/open-apis/bitable/v1/apps/{app}/tables/{tbl}/records?page_size=500"
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        st, rr, _ = http(url, headers=auth, timeout=90)
        if rr.get("code") != 0:
            return None, f"records 失败 st={st} code={rr.get('code')} msg={rr.get('msg')}"
        d = rr.get("data") or {}
        for it in (d.get("items") or []):
            records.append({k: flatten_cell(v) for k, v in (it.get("fields") or {}).items()})
        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break
    return {"token": token, "app_token": app, "table_id": tbl,
            "fields": fields, "records": records, "record_count": len(records)}, None


def fetch_embedded_tables(domain, auth, blocks, docdir):
    """抓文档里所有内嵌表格,落 raw/<slug>/sheets.json。
    这类内容既不在 raw_content 也不在 blocks(块里只有 token),漏抓 = 整段核心内容丢失
    (实测有正文仅 402 字符、埋点表与文案表全在内嵌 Sheet 里的需求文档)。
    对齐红线:任一张抓取失败即中止,不产出缺内容的坏原料。"""
    sheet_blocks = [b for b in blocks if b.get("block_type") == 30]
    bitable_blocks = [b for b in blocks if b.get("block_type") == 18]
    if not sheet_blocks and not bitable_blocks:
        log("内嵌表格:无(无 block_type=30/18)")
        return [], []
    log(f"内嵌表格 {len(sheet_blocks)} 张 Sheet + {len(bitable_blocks)} 张多维表,抓取中...")

    meta_cache, sheets, bitables = {}, [], []
    for i, b in enumerate(sheet_blocks, 1):
        tk = (b.get("sheet") or {}).get("token") or ""
        if "_" not in tk:
            log(f"  Sheet{i} token 异常({tk!r}) —— 中止,避免产出缺内容的坏原料")
            sys.exit(1)
        item, err = None, None
        for attempt in range(3):
            item, err = fetch_sheet_block(domain, auth, tk, meta_cache)
            if item:
                break
            log(f"  Sheet{i} {err}(第 {attempt+1}/3 次),2s 后重试...")
            time.sleep(2)
        if not item:
            log(f"  Sheet{i} token={tk} 抓取失败:{err} —— 重试 3 次仍失败,中止")
            sys.exit(1)
        item["block_id"] = b.get("block_id")
        sheets.append(item)
        log(f"  Sheet{i} {item['title']} {len(item['values'])} 行 × "
            f"{len(item['values'][0]) if item['values'] else 0} 列(网格 {item['row_count']}×{item['column_count']})")

    for i, b in enumerate(bitable_blocks, 1):
        tk = (b.get("bitable") or {}).get("token") or ""
        if "_" not in tk:
            log(f"  多维表{i} token 异常({tk!r}) —— 中止")
            sys.exit(1)
        item, err = None, None
        for attempt in range(3):
            item, err = fetch_bitable_block(domain, auth, tk)
            if item:
                break
            log(f"  多维表{i} {err}(第 {attempt+1}/3 次),2s 后重试...")
            time.sleep(2)
        if not item:
            log(f"  多维表{i} token={tk} 抓取失败:{err} —— 重试 3 次仍失败,中止")
            sys.exit(1)
        item["block_id"] = b.get("block_id")
        bitables.append(item)
        log(f"  多维表{i} {item['record_count']} 条记录,字段 {item['fields']}")

    payload = {"fetched_at": datetime.now().astimezone().isoformat(),
               "sheets": sheets, "bitables": bitables}
    with open(os.path.join(docdir, "sheets.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"内嵌表格已落 sheets.json:{len(sheets)} Sheet / {len(bitables)} 多维表")
    return sheets, bitables


def major_minor(v):
    """取版本号的 major.minor 用于一致性比较:V1.30.0 / V1.30 -> '1.30'。"""
    nums = re.findall(r"\d+", v)
    return ".".join(nums[:2]) if len(nums) >= 2 else (nums[0] if nums else v)


def extract_version_candidates(raw_content):
    cands = []
    m = re.search(r"版本号\s*\n+\s*(V?\d[\w.]*)", raw_content)
    if m:
        cands.append({"source": "版本号字段", "version": m.group(1)})
    for mm in re.finditer(r"figma\.com/design/[^\s)]*?/(V?\d+\.\d+(?:\.\d+)?)", raw_content):
        cands.append({"source": "figma链接", "version": mm.group(1)})
    for mm in re.finditer(r"(?<![\w.])V\d+\.\d+(?:\.\d+)?", raw_content):
        cands.append({"source": "正文", "version": mm.group(0)})
    # 去重(按原始串)
    seen, uniq = set(), []
    for c in cands:
        if c["version"] not in seen:
            seen.add(c["version"])
            uniq.append(c)
    return uniq


def decide_version(version_arg, raw_content):
    if version_arg:
        log(f"版本:{version_arg}(你提供,权威)")
        return version_arg, "user", []
    cands = extract_version_candidates(raw_content)
    if not cands:
        log("版本:待确认(文档里没提取到版本线索)")
        return None, "extract-none", []
    groups = {major_minor(c["version"]) for c in cands}
    if len(groups) == 1:
        # 取最具体(最长)的候选
        best = max(cands, key=lambda c: len(c["version"]))["version"]
        log(f"版本:{best}(文档提取,候选一致)候选={[c['version'] for c in cands]}")
        return best, "extract-consistent", cands
    log(f"版本:待确认 ← 候选 major.minor 冲突:{[(c['source'], c['version']) for c in cands]}")
    return None, "extract-conflict", cands


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    if not args:
        log('用法: python3 scripts/fetch.py "<飞书链接或token>" [版本号] [--force]')
        sys.exit(1)
    link = args[0]
    version_arg = args[1] if len(args) > 1 else None
    token = extract_token(link)
    log(f"输入链接/token={link!r} → wiki token={token} ; 版本入参={version_arg!r}")

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

    _, nr, _ = http(f"{domain}/open-apis/wiki/v2/spaces/get_node?token={token}", headers=auth)
    node = (nr.get("data") or {}).get("node") or {}
    doc_id, title, obj_type = node.get("obj_token"), node.get("title") or "untitled", node.get("obj_type")
    log(f"node: title={title!r} type={obj_type} doc_id={doc_id} code={nr.get('code')} msg={nr.get('msg')}")
    if not doc_id:
        log(f"解析 wiki node 失败(权限/链接?):{nr}")
        sys.exit(1)

    docdir = os.path.join(RAW_ROOT, slugify(title))
    # 原料层只读、永不覆盖(红线):meta.json 存在 = 上次已抓完整,默认拒绝覆盖;半成品(无 meta)可重抓
    if os.path.exists(os.path.join(docdir, "meta.json")) and not force:
        log(f"原料已存在且完整:{docdir}/ —— 原料层永不覆盖(红线)。确需重抓请加 --force。")
        sys.exit(1)
    imgdir = os.path.join(docdir, "images")
    os.makedirs(imgdir, exist_ok=True)

    _, rc, _ = http(f"{domain}/open-apis/docx/v1/documents/{doc_id}/raw_content?lang=0", headers=auth)
    if rc.get("code") != 0:
        log(f"raw_content 失败 {rc.get('code')} {rc.get('msg')} —— 中止,避免产出空正文的坏原料")
        sys.exit(1)
    content = (rc.get("data") or {}).get("content", "")
    with open(os.path.join(docdir, "content.txt"), "w", encoding="utf-8") as f:
        f.write(content)
    log(f"raw_content {len(content)} 字符")

    blocks, page_token = [], None
    while True:
        url = f"{domain}/open-apis/docx/v1/documents/{doc_id}/blocks?page_size=500&document_revision_id=-1"
        if page_token:
            url += f"&page_token={urllib.parse.quote(page_token)}"
        _, br, _ = http(url, headers=auth)
        if br.get("code") != 0:
            log(f"blocks 失败 {br.get('code')} {br.get('msg')} —— 中止,避免产出缺失内容的坏原料(meta 不会生成,此目录视为未完成)")
            sys.exit(1)
        d = br.get("data") or {}
        blocks += d.get("items") or []
        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break
    with open(os.path.join(docdir, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)
    log(f"blocks {len(blocks)} 个;类型分布 {dict(Counter(b.get('block_type') for b in blocks))}")

    imgs = [b for b in blocks if b.get("block_type") == 27]
    log(f"图片块 {len(imgs)} 个,下载中...")
    img_meta = []
    for i, b in enumerate(imgs, 1):
        tk = (b.get("image") or {}).get("token")
        if not tk:
            log(f"  图{i} 缺少 image.token —— 中止,避免产出缺图的坏原料(规则:下载文档里所有图片)")
            sys.exit(1)
        st, body, hdrs = 0, b"", None
        for attempt in range(3):  # 应对网络抖动/SSL 超时:最多 3 次
            st, body, hdrs = http(f"{domain}/open-apis/drive/v1/medias/{tk}/download", headers=auth, raw=True)
            if st == 200:
                break
            log(f"  图{i} 下载失败(第 {attempt+1}/3 次)st={st},2s 后重试...")
            time.sleep(2)
        if st != 200:
            log(f"  图{i} 下载失败 HTTP={st} —— 重试 3 次仍失败,中止(规则:下载文档里所有图片;网络恢复后重抓即可)")
            sys.exit(1)
        ct = (hdrs or {}).get("Content-Type", "image/png")
        ext = ct.split("/")[-1].split(";")[0] if "/" in ct else "png"
        fn = f"img-{i:02d}.{ext}"
        path = os.path.join(imgdir, fn)
        with open(path, "wb") as f:
            f.write(body)
        read_name, dims = downscale_for_read(path)
        level, scale = readability(dims[0], dims[1])
        entry = {"index": i, "file": f"images/{fn}", "bytes": len(body), "dims": list(dims),
                 "readable": level, "read_scale": round(scale, 3)}
        if read_name:
            entry["read_file"] = f"images/{read_name}"
            log(f"  图{i} {dims[0]}x{dims[1]} 超 {MAX_READ_PX}px → 缩放副本 {read_name}"
                f"(缩至 {scale:.0%}{',可读性存疑' if level == 'marginal' else ''};原图保留)")
        img_meta.append(entry)
    over = [m for m in img_meta if m.get("read_file")]
    unread = [m for m in img_meta if m.get("readable") == "unreadable"]
    marg = [m for m in img_meta if m.get("readable") == "marginal"]
    log(f"图片下载完成 {len(img_meta)}/{len(imgs)} 张;超大已生成缩放副本 {len(over)} 张;"
        f"不可读 {len(unread)} 张;可读性存疑 {len(marg)} 张")

    sheets, bitables = fetch_embedded_tables(domain, auth, blocks, docdir)

    version, version_source, version_cands = decide_version(version_arg, content)
    img_count = len(img_meta)
    read_hint = "≤6 张 → 全读" if img_count <= 6 else f">6 张({img_count}) → 只读关键图、其余存档+链接"
    log(f"读图建议(SKILL 智能读):{read_hint}")

    meta = {
        "title": title, "doc_id": doc_id, "wiki_token": token,
        "url": f"https://wsgh3q8mwfpp.sg.larksuite.com/wiki/{token}",
        "fetched_at": datetime.now().astimezone().isoformat(),
        "version": version, "version_source": version_source, "version_candidates": version_cands,
        "raw_content_chars": len(content), "blocks": len(blocks),
        "images": img_meta, "image_count": img_count,
        # tables 只统计正文表格(block_type=31);内嵌 Sheet / 多维表另计,别再用 tables 判断"有没有表"
        "tables": sum(1 for b in blocks if b.get("block_type") == 31),
        "embedded_sheets": len(sheets), "embedded_bitables": len(bitables),
        "embedded_tables_file": "sheets.json" if (sheets or bitables) else None,
    }
    with open(os.path.join(docdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    log(f"完成。raw 目录:{docdir}")
    print("\n==== INGEST 摘要(供下一步:读图 → 提炼)====")
    print(f"标题   : {title}")
    print(f"版本   : {version if version else '待确认 ⚠️  候选=' + str([c['version'] for c in version_cands])} (来源:{version_source})")
    print(f"图/表  : {img_count} 图 / {meta['tables']} 正文表 — {read_hint}")
    if sheets or bitables:
        print(f"内嵌表 : {len(sheets)} 张 Sheet / {len(bitables)} 张多维表 —— ⚠️ 内容不在正文,"
              f"提炼前必须读 {docdir}/sheets.json")
    over_read = [m for m in img_meta if m.get("read_file")]
    if over_read:
        print(f"超大图 : {len(over_read)} 张超 {MAX_READ_PX}px,读图请读缩放副本 → " + ", ".join(m["read_file"] for m in over_read))
    if marg:
        detail = ", ".join(f"{m['file']} 缩至 {m['read_scale']:.0%}" for m in marg)
        print(f"存疑图 : {len(marg)} 张({detail}) —— 读得清就写、读不清就如实标注,"
              f"**禁止从布局形状推断内容**")
    if unread:
        print(f"❌ 不可读: {len(unread)} 张 —— 缩放后文字不可读,**不要读、不要猜**;"
              f"笔记图说明如实写「原图 W×H,缩放后仅 X%,不可读,未读取」:")
        for m in unread:
            print(f"          {m['file']}  {m['dims'][0]}x{m['dims'][1]}  缩放后仅 {m['read_scale']:.0%}")
    print(f"raw目录: {docdir}")
    print("\n==== RAW CONTENT(全文)====")
    print(content)


if __name__ == "__main__":
    main()
