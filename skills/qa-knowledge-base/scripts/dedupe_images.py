#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dedupe_images.py — 把 raw/ 里内容完全相同的图片改成硬链接,回收重复占用的磁盘。

为什么会有重复:同一张设计稿常被多篇需求文档引用,每篇 ingest 各下一份。
实测 102 篇时有 48 组重复图,冗余占用 28.7MB。

为什么用硬链接而不是删文件 + 建软链:
    - **所有路径原样保留** —— `notes/` 里的图链接、`raw/*/meta.json` 的 `images[].file`
      全都不用改,读图行为零变化;
    - 硬链接指向同一份数据,不像软链那样怕相对路径/拷贝时断链;
    - 原料层红线是"只读永不覆盖",既然不会被改写,共享同一份数据是安全的。

注意范围:
    - 只省**工作区磁盘**。git 本身按内容哈希存储,相同内容本来就只存一份,所以这不影响仓库体积。
    - 跨文件系统无法硬链接(会跳过并报出来)。
    - 新 ingest 的文档不会自动去重,批量入库后再跑一次即可(幂等,可反复跑)。

用法:
    python3 scripts/dedupe_images.py           # dry-run:只报告有哪些重复、能省多少
    python3 scripts/dedupe_images.py --write   # 真的改成硬链接
"""
import os
import sys
import glob
import hashlib
from collections import defaultdict

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ROOT = os.path.join(KB_ROOT, "raw")


def log(m):
    print(f"[dedupe] {m}", flush=True)


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


def main():
    write = "--write" in sys.argv
    # 原图与 .read 副本都算(副本平时不留存,留存时同样可能重复)
    files = sorted(glob.glob(os.path.join(RAW_ROOT, "*", "images", "*")))
    log(f"扫描 {len(files)} 个图片文件…")

    # 先按体积分桶,只对同体积的算 md5(省掉绝大部分哈希计算)
    by_size = defaultdict(list)
    for p in files:
        try:
            by_size[os.path.getsize(p)].append(p)
        except OSError as e:
            log(f"  跳过(读不到):{p} {e}")
    cand = [ps for ps in by_size.values() if len(ps) > 1]
    log(f"同体积候选组 {len(cand)} 组,开始比对内容…")

    groups = defaultdict(list)
    for ps in cand:
        for p in ps:
            groups[(os.path.getsize(p), md5(p))].append(p)

    dup = {k: v for k, v in groups.items() if len(v) > 1}
    linked = skipped = 0
    freed = 0
    actionable = 0  # 真正还能省的份数(已硬链接过的不计,否则 dry-run 会报"0 MB / 53 个冗余"自相矛盾)
    for (size, h), paths in sorted(dup.items(), key=lambda kv: -kv[0][0] * (len(kv[1]) - 1)):
        paths.sort()
        keep = paths[0]
        keep_stat = os.stat(keep)
        rest = []
        for p in paths[1:]:
            st = os.stat(p)
            if st.st_ino == keep_stat.st_ino and st.st_dev == keep_stat.st_dev:
                continue  # 已经是同一份数据,跳过
            if st.st_dev != keep_stat.st_dev:
                log(f"  ⚠️ 跨文件系统,无法硬链接:{p}")
                skipped += 1
                continue
            rest.append(p)
        if not rest:
            continue
        freed += size * len(rest)
        actionable += len(rest)
        log(f"  {mb(size)} × {len(rest)} 份冗余 ← {os.path.relpath(keep, KB_ROOT)}")
        for p in rest:
            log(f"      {'链接' if write else '待链接'} {os.path.relpath(p, KB_ROOT)}")
            if write:
                tmp = p + ".dedupe.tmp"
                os.link(keep, tmp)          # 先建新链接,成功后再原子替换,避免中途失败丢文件
                os.replace(tmp, p)
                linked += 1

    if not dup:
        log("没有发现重复图片。")
        return
    if not actionable:
        log(f"发现 {len(dup)} 组重复图,但都已是硬链接共享同一份数据 —— 无可回收空间(幂等)。")
        return
    if write:
        log(f"完成:{linked} 个文件改为硬链接,回收 {mb(freed)};跨盘跳过 {skipped} 个。")
    else:
        log(f"dry-run:可回收 {mb(freed)}(涉及 {actionable} 个尚未共享的冗余文件)。"
            f"确认无误后:python3 scripts/dedupe_images.py --write")


if __name__ == "__main__":
    main()
