#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch.py — ingest 第①步:抓取一篇飞书需求文档(正文 + 表格 + 全部图片)存进 raw/<标题>/。

用法:
    python3 scripts/fetch.py "<飞书链接或token>" [版本号]

版本来源(对应 SKILL.md):
    - 给了版本号  → 用你的(权威)。
    - 没给        → 从文档提取候选(基本信息"版本号"字段 / figma 链接 / 正文 VX.X);
                    候选 major.minor 一致 → 取最具体的;冲突 → version=null 标"待确认",列出候选,交 Claude/你定。

凭证:优先环境变量 LARK_APP_ID / LARK_APP_SECRET / LARK_DOMAIN;
      没有则从公司 config 服务拉取(需 VPN)。

产出:raw/<slug>/{content.txt, blocks.json, images/, meta.json};并把正文 + 版本判定打印出来供下一步(读图/提炼)用。
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
        base, ext = os.path.splitext(path)
        rd = base + ".read" + ext
        subprocess.run(["sips", "-Z", str(max_px), path, "--out", rd],
                       capture_output=True, text=True, timeout=30)
        return os.path.basename(rd), (w, h)
    except Exception as e:
        log(f"  缩放失败({e}),读图将退回原图")
        return None, (0, 0)


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
        entry = {"index": i, "file": f"images/{fn}", "bytes": len(body), "dims": list(dims)}
        if read_name:
            entry["read_file"] = f"images/{read_name}"
            log(f"  图{i} {dims[0]}x{dims[1]} 超 {MAX_READ_PX}px → 缩放副本 {read_name}(供读图;原图保留)")
        img_meta.append(entry)
    over = [m for m in img_meta if m.get("read_file")]
    log(f"图片下载完成 {len(img_meta)}/{len(imgs)} 张;其中 {len(over)} 张超大已生成缩放副本")

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
        "tables": sum(1 for b in blocks if b.get("block_type") == 31),
    }
    with open(os.path.join(docdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    log(f"完成。raw 目录:{docdir}")
    print("\n==== INGEST 摘要(供下一步:读图 → 提炼)====")
    print(f"标题   : {title}")
    print(f"版本   : {version if version else '待确认 ⚠️  候选=' + str([c['version'] for c in version_cands])} (来源:{version_source})")
    print(f"图/表  : {img_count} 图 / {meta['tables']} 表 — {read_hint}")
    over_read = [m for m in img_meta if m.get("read_file")]
    if over_read:
        print(f"超大图 : {len(over_read)} 张超 {MAX_READ_PX}px,读图请读缩放副本 → " + ", ".join(m["read_file"] for m in over_read))
    print(f"raw目录: {docdir}")
    print("\n==== RAW CONTENT(全文)====")
    print(content)


if __name__ == "__main__":
    main()
