#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_cache.py — 读图缩放副本的按需重建 / 清理。

背景:读图工具上限 ~2000px,超大图要缩到 1900px 才读得了,fetch 会就地生成 `img-NN.read.png`。
     这些副本是 **derived**(`sips -Z 1900` 从原图算出来的,实测字节级可精确重建),不是事实来源。
     实测 102 篇时它们占 123MB / 全库 23% —— 常驻磁盘毫无必要,读完即可清掉,要时再建。

所以约定:
    - `.read.*` 已加进 `.gitignore`,不入版本库;
    - 平时不留存(`--clean` 清掉),需要读图/复核时用本脚本就地重建;
    - **路径与 fetch 生成的完全一致**,所以 `notes/` 里的图链接和 `raw/*/meta.json` 的 `read_file`
      不用改、也不会失效 —— 文件不在时重建一次即可。

用法:
    python3 scripts/read_cache.py <slug 或 raw 路径>   # 重建某篇的所有超大图副本
    python3 scripts/read_cache.py --all                # 重建全库(会吃掉 ~123MB,慎用)
    python3 scripts/read_cache.py --clean <slug>       # 清掉某篇的副本
    python3 scripts/read_cache.py --clean --all        # 清掉全库副本(回收空间)
    python3 scripts/read_cache.py --status             # 只看当前占用,不动文件
"""
import os
import re
import sys
import glob
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import readability, write_unreadable_marker, MAX_READ_PX  # noqa: E402  —— 判据与标记单一来源,避免规则漂移

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ROOT = os.path.join(KB_ROOT, "raw")


def log(m):
    print(f"[read_cache] {m}", flush=True)


def mb(n):
    return f"{n / 1024 / 1024:.1f} MB"


def dims(path):
    """用 sips 读像素尺寸;读不到返回 (0, 0)。"""
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
        return w, h
    except Exception as e:
        log(f"  读尺寸失败({e}):{path}")
        return 0, 0


def doc_dirs(target):
    """target 为 None → 全库;否则按 slug 或路径定位一篇。"""
    if target is None:
        return sorted(d for d in glob.glob(os.path.join(RAW_ROOT, "*")) if os.path.isdir(d))
    cand = target if os.path.isdir(target) else os.path.join(RAW_ROOT, target)
    if not os.path.isdir(cand):
        log(f"找不到原料目录:{target}(既不是路径,也不是 raw/ 下的 slug)")
        sys.exit(1)
    return [cand]


def originals(docdir):
    """该篇的原图(排除 .read 副本本身)。"""
    return sorted(p for p in glob.glob(os.path.join(docdir, "images", "*"))
                  if ".read." not in os.path.basename(p)
                  and not p.endswith(".UNREADABLE.txt"))


def read_path(orig):
    """派生副本统一用 PNG:原图已转 WebP 归档,而 sips 能**读** WebP 但只能**写** PNG
    (`sips --formats` 里 webp 没有 Writable)。统一 .read.png 可让本脚本保持零依赖。"""
    return os.path.splitext(orig)[0] + ".read.png"


def do_build(dirs):
    built = skipped = existed = unreadable = 0
    total = 0
    bad = []
    for d in dirs:
        imgs = originals(d)
        if not imgs:
            continue
        made = []
        for p in imgs:
            w, h = dims(p)
            if max(w, h) <= MAX_READ_PX:
                skipped += 1
                continue
            level, scale = readability(w, h)
            if level == "unreadable":
                # 缩出来也读不出,生成只会占空间 + 诱导瞎猜;补上前置拦截标记(幂等,已有则覆盖为最新口径)
                unreadable += 1
                write_unreadable_marker(p, w, h, scale)
                bad.append((os.path.relpath(p, KB_ROOT), w, h, scale))
                continue
            rd = read_path(p)
            if os.path.exists(rd):
                existed += 1
                total += os.path.getsize(rd)
                continue
            subprocess.run(["sips", "-Z", str(MAX_READ_PX), "-s", "format", "png", p, "--out", rd],
                           capture_output=True, text=True, timeout=60)
            if os.path.exists(rd):
                built += 1
                total += os.path.getsize(rd)
                made.append(f"{os.path.basename(rd)}({w}x{h}→{MAX_READ_PX}px)")
            else:
                log(f"  ⚠️ 生成失败:{p}")
        if made:
            log(f"  {os.path.basename(d)}: {len(made)} 张 → {', '.join(made[:6])}"
                + (" …" if len(made) > 6 else ""))
    log(f"重建完成:新建 {built} 张,已存在 {existed} 张,无需缩放 {skipped} 张;副本共占 {mb(total)}")
    if bad:
        log(f"❌ 另有 {len(bad)} 张**不可读**(缩放后文字糊掉),未生成副本 —— 不要读、不要猜:")
        for rel, w, h, s in bad:
            log(f"     {rel}  {w}x{h}  缩放后仅 {s:.0%}")


def do_clean(dirs):
    removed = freed = 0
    for d in dirs:
        for p in glob.glob(os.path.join(d, "images", "*.read.*")):
            freed += os.path.getsize(p)
            os.remove(p)
            removed += 1
    log(f"已清理 {removed} 张缩放副本,回收 {mb(freed)}(原图未动,随时可 read_cache.py 重建)")


def do_status(dirs):
    n = size = 0
    over = 0
    for d in dirs:
        for p in glob.glob(os.path.join(d, "images", "*.read.*")):
            n += 1
            size += os.path.getsize(p)
        for p in originals(d):
            w, h = dims(p)
            if max(w, h) > MAX_READ_PX:
                over += 1
    log(f"扫描 {len(dirs)} 篇:超大原图 {over} 张;当前留存缩放副本 {n} 张,占 {mb(size)}")


def main():
    args = sys.argv[1:]
    clean = "--clean" in args
    status = "--status" in args
    all_docs = "--all" in args
    rest = [a for a in args if not a.startswith("--")]
    target = rest[0] if rest else None

    if not args:
        print(__doc__)
        sys.exit(1)
    if target is None and not all_docs:
        log("需要指定 <slug> 或 --all")
        sys.exit(1)

    dirs = doc_dirs(None if all_docs else target)
    log(f"目标:{'全库 ' + str(len(dirs)) + ' 篇' if all_docs else os.path.basename(dirs[0])}")

    if status:
        do_status(dirs)
    elif clean:
        do_clean(dirs)
    else:
        do_build(dirs)


if __name__ == "__main__":
    main()
