#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compress_images.py — 把 raw/ 里的图片原图转成 WebP 归档,并把「读不出的超大图」降级为占位图。

跑的时机:**每批 ingest 落盘之后**(SKILL.md ingest 第 6 步「收尾省空间」),顺序:
    ① read_cache.py --clean --all   清掉派生副本
    ② compress_images.py --write    ← 本脚本
    ③ dedupe_images.py --write      转换会改写文件、打断硬链接,要重新去重
关键:转换发生在**读图之后**,所以首次提炼永远用的是刚下载的无损 PNG,
     有损只影响事后复核 —— 而复核质量已实测通过。

## 为什么是 WebP q80(2026-08-28 实测标定)

格式:
    - **AVIF 否决**:Pillow 能编、大图上体积只有 WebP 一半,但**读图工具不认**(读出来是二进制乱码)。
    - **WebP 通过**:实测读飞书返回的 .webp,中文/字段名/按钮文案全清晰。
质量:
    - q80 在三种最坏场景真读通过 —— ① 直接读的密集文字截图 ② 随机验证码(无法靠上下文猜)
      ③ 有损归档 + 再缩到 1900px 的叠加损失,读到的内容与 PNG 基准完全一致。
    - q90 比 q80 大 20%,最坏单通道偏差只差 7/255,买不到东西。
    - q60 也能读,但全库只比 q80 多省 8MB —— 压缩收益几乎全来自「PNG→WebP」这一步,
      q 值在 60–80 区间是平的,没必要拿质量余量换这 8MB。
    - 颜色语义安全:大偏差全在文字边缘振铃,平坦区(红/绿/黑三色打分所在)最大偏差 ≤39/255、平均 <1/255。

## 不可读的图直接降级为占位

`readability()` 判定 unreadable(缩放比例 <15%)的图,内容本来就一个字都读不出,
却占了压缩后总体积的 **71%**(9 张 = 53.2MB / 74.8MB)。保留原图毫无价值,
故只留一张 1900px 的 WebP 占位(9 张合计 0.2MB),外加已有的 `.UNREADABLE.txt` 标记说明原始尺寸。
事实来源是飞书:`blocks.json` 里存着 image token,实测 2026-06-30 入库的老文档至今仍可重下。
meta.json 里会记下原图的 `dims` / `bytes` / `md5`,将来重下能核验是不是同一张。

用法:
    .venv/bin/python scripts/compress_images.py            # dry-run:只报告,不动文件
    .venv/bin/python scripts/compress_images.py --write    # 执行转换
    .venv/bin/python scripts/compress_images.py --write --only <slug>   # 只处理一篇

依赖:Pillow(项目级 `.venv/`,不进 fetch.py —— fetch 保持零依赖,同事装 skill 不受影响)。
"""
import os
import re
import sys
import glob
import json
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import readability, MAX_READ_PX  # noqa: E402  —— 可读性判据单一来源

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None  # 库里有 32768x5934 这类超大图,关掉解压炸弹保护
except ImportError:
    print("[compress] 缺少 Pillow。本脚本是维护工具,依赖装在项目级 venv 里:\n"
          "    python3 -m venv .venv && .venv/bin/pip install Pillow\n"
          "    .venv/bin/python scripts/compress_images.py")
    sys.exit(1)

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ROOT = os.path.join(KB_ROOT, "raw")
NOTES_DIR = os.path.join(KB_ROOT, "notes")
QUALITY = 80
SRC_EXTS = (".png", ".jpeg", ".jpg")


def log(m):
    print(f"[compress] {m}", flush=True)


def mb(n):
    return f"{n / 1024 / 1024:.1f} MB"


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def convert_one(src, write):
    """返回 (动作, 原字节, 新字节, 原尺寸, 新尺寸, 原md5)。动作 ∈ {'full','placeholder'}。"""
    with Image.open(src) as im:
        w, h = im.size
        mode = im.mode
        rgb = im.convert("RGBA") if mode in ("RGBA", "LA", "P") else im.convert("RGB")
        level, _ = readability(w, h)
        if level == "unreadable":
            # 读不出的图只留 1900px 占位:内容取不到,留原图纯属浪费
            rgb.thumbnail((MAX_READ_PX, MAX_READ_PX), Image.LANCZOS)
            action = "placeholder"
        else:
            action = "full"
        dst = os.path.splitext(src)[0] + ".webp"
        old_bytes = os.path.getsize(src)
        old_md5 = md5(src)
        if not write:
            import io
            buf = io.BytesIO()
            rgb.save(buf, "WEBP", quality=QUALITY, method=6)
            return action, old_bytes, buf.tell(), (w, h), rgb.size, old_md5
        tmp = dst + ".tmp"
        rgb.save(tmp, "WEBP", quality=QUALITY, method=6)
        new_dims = rgb.size

    # 落盘前自检:新文件能打开、尺寸符合预期,才删原图(原图删了就只能回飞书重下)
    with Image.open(tmp) as chk:
        expect = (w, h) if action == "full" else None
        if expect and chk.size != expect:
            os.remove(tmp)
            raise RuntimeError(f"转换后尺寸不符:{chk.size} != {expect} ({src})")
        if action == "placeholder" and max(chk.size) > MAX_READ_PX:
            os.remove(tmp)
            raise RuntimeError(f"占位图未缩到 {MAX_READ_PX}px:{chk.size} ({src})")
    os.replace(tmp, dst)
    new_bytes = os.path.getsize(dst)
    os.remove(src)
    return action, old_bytes, new_bytes, (w, h), new_dims, old_md5


def update_meta(docdir, changes, write):
    """meta.json 的 images[].file 换成 .webp。
    约定:`file` / `bytes` / `dims` 一律描述**当前磁盘上那个文件**,
    原图的真相收进 `original`(file/bytes/md5/dims)——占位图尤其重要,
    否则 dims 写着 15146x2316、文件其实只有 1900px,会误导后续判断。"""
    mp = os.path.join(docdir, "meta.json")
    if not os.path.exists(mp):
        return
    meta = json.load(open(mp, encoding="utf-8"))
    hit = 0
    for entry in meta.get("images", []):
        base = os.path.basename(entry.get("file", ""))
        if base not in changes:
            continue
        c = changes[base]
        stem = os.path.splitext(base)[0]
        entry["file"] = f"images/{stem}.webp"
        entry["archived_as"] = "webp-placeholder-1900px" if c["action"] == "placeholder" else f"webp-q{QUALITY}"
        entry["original"] = {"file": base, "bytes": c["old"], "md5": c["md5"], "dims": list(c["dims"])}
        entry["bytes"] = c["new"]
        entry["dims"] = list(c["new_dims"])
        if c["action"] == "placeholder":
            # 占位图本身就是 1900px,不需要也不会有 .read 派生副本
            entry.pop("read_file", None)
        elif entry.get("read_file"):
            entry["read_file"] = f"images/{stem}.read.png"
        hit += 1
    if hit and write:
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return hit


def update_notes(write):
    """notes/ 里的图链接 .png/.jpeg → .webp(含 .read. 派生副本的引用)。"""
    # 只改原图引用;`.read.` 是派生副本,统一保持 PNG(sips 只能写 png),不要跟着变
    pat = re.compile(r"(images/img-\d+)\.(?:png|jpeg|jpg)\b")
    touched = 0
    for p in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md"))):
        t = open(p, encoding="utf-8").read()
        new = pat.sub(r"\1.webp", t)
        if new != t:
            touched += 1
            if write:
                open(p, "w", encoding="utf-8").write(new)
    return touched


def main():
    write = "--write" in sys.argv
    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        only = sys.argv[i + 1] if i + 1 < len(sys.argv) else None

    dirs = sorted(d for d in glob.glob(os.path.join(RAW_ROOT, "*")) if os.path.isdir(d))
    if only:
        dirs = [d for d in dirs if os.path.basename(d) == only]
        if not dirs:
            log(f"找不到 raw/{only}")
            sys.exit(1)

    log(f"目标 {len(dirs)} 篇;质量 q{QUALITY};{'执行写入' if write else 'dry-run(不动文件)'}")
    tot_old = tot_new = 0
    n_full = n_place = 0
    for d in dirs:
        srcs = [p for p in sorted(glob.glob(os.path.join(d, "images", "*")))
                if os.path.splitext(p)[1].lower() in SRC_EXTS and ".read." not in os.path.basename(p)]
        if not srcs:
            continue
        changes, d_old, d_new = {}, 0, 0
        for s in srcs:
            try:
                action, old, new, dims, new_dims, m = convert_one(s, write)
            except Exception as e:
                log(f"  ⚠️ 失败,跳过(原图未动):{os.path.relpath(s, KB_ROOT)} — {e}")
                continue
            changes[os.path.basename(s)] = {"action": action, "old": old, "new": new,
                                            "md5": m, "dims": dims, "new_dims": new_dims}
            d_old += old
            d_new += new
            if action == "placeholder":
                n_place += 1
                log(f"  📉 占位 {os.path.relpath(s, KB_ROOT)}  {dims[0]}x{dims[1]} "
                    f"{mb(old)} → {mb(new)}(读不出,只留 {MAX_READ_PX}px)")
            else:
                n_full += 1
        if changes:
            update_meta(d, changes, write)
            tot_old += d_old
            tot_new += d_new
            log(f"  {os.path.basename(d)[:34]:<34} {len(changes):>2} 张  {mb(d_old)} → {mb(d_new)}")

    if only:
        log("笔记图链接改写:跳过(--only 只处理单篇;链接改写是全库一次性动作,全量跑时才做)")
    else:
        touched = update_notes(write)
        log(f"笔记图链接改写:{touched} 篇{'(已写)' if write else '(dry-run 未写)'}")
    saved = tot_old - tot_new
    log(f"合计:全量转 {n_full} 张 / 占位 {n_place} 张;{mb(tot_old)} → {mb(tot_new)},"
        f"省 {mb(saved)}({100 * saved / tot_old:.0f}%)" if tot_old else "无可转换的图片")
    if not write:
        log("dry-run 完成。确认无误后加 --write;写入后记得跑 dedupe_images.py --write 重建硬链接。")


if __name__ == "__main__":
    main()
