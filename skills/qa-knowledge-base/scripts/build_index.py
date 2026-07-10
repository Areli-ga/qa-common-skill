#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — ingest 第⑥步:扫 notes/ 的 frontmatter + 摘要,重新生成 index/INDEX.md。

derived:每次全量重算、幂等,可一键重建(index 坏了不慌)。按 模块(一级) → 版本 排序。
版本号带注释也能取(如 "V1.29   # ...");"待确认"/无版本排到最后。
用法: python3 scripts/build_index.py
"""
import os
import re
import glob

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTES_DIR = os.path.join(KB_ROOT, "notes")
INDEX_PATH = os.path.join(KB_ROOT, "index", "INDEX.md")


def log(m):
    print(f"[index] {m}", flush=True)


def parse_note(path):
    text = open(path, encoding="utf-8").read()
    fm, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            mm = re.match(r"^(\w+):\s*(.*)$", line)
            if mm:
                fm[mm.group(1)] = mm.group(2).strip()
    # 一句话摘要:取 "## 摘要" 段首段,压成一行、截断
    summary = ""
    sm = re.search(r"^##\s*摘要\s*\n+(.+?)(?=\n#|\Z)", body, re.S | re.M)
    if sm:
        summary = re.sub(r"\s+", " ", sm.group(1).strip())
        if len(summary) > 80:
            summary = summary[:78] + "…"
    ver = fm.get("版本", "").split()[0] if fm.get("版本", "").strip() else "待确认"
    return {
        "file": os.path.basename(path),
        "module": fm.get("模块", "(未分类)"),
        "version": ver,
        "title": fm.get("标题", "(无标题)"),
        "url": fm.get("原链接", ""),
        "summary": summary,
    }


def ver_key(v):
    nums = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in nums) if nums else (9999,)  # 待确认/无 → 最后


def main():
    notes = [parse_note(p) for p in glob.glob(os.path.join(NOTES_DIR, "*.md"))]
    notes.sort(key=lambda n: (n["module"], ver_key(n["version"]), n["title"]))
    log(f"扫到 {len(notes)} 篇笔记")

    lines = [
        "# INDEX · 全库目录",
        "",
        "> 脚本生成(`scripts/build_index.py`,derived,可由 notes/ 一键重建)。按 模块 → 版本 排序。",
        "",
        "| 模块 | 版本 | 标题 | 链接 | 一句话摘要 |",
        "|---|---|---|---|---|",
    ]
    for n in notes:
        link = f"[{n['title']}](../notes/{n['file']})"
        feishu = f"[飞书]({n['url']})" if n["url"] else ""
        lines.append(f"| {n['module']} | {n['version']} | {link} | {feishu} | {n['summary']} |")

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"已重建 {INDEX_PATH}({len(notes)} 行)")
    for n in notes:
        log(f"  {n['module']} | {n['version']} | {n['title']}")


if __name__ == "__main__":
    main()
