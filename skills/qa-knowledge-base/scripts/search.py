#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search.py — 取①:在 notes/ 里按关键词或模块检索,列出命中笔记(写用例前查往期相关)。

用法:
    python3 scripts/search.py 关键词1 [关键词2 ...]   # 关键词检索:在 模块/标题/摘要/正文 里找(OR)
    python3 scripts/search.py --module 奖励            # 列出模块名含"奖励"的所有笔记(供"模块历史问答")
    python3 scripts/search.py --version V1.30          # 列出某版本的所有需求(本次迭代要测啥;V1.30 也匹配 V1.30.0)

注:关键词为 OR 子串匹配;每个参数会再按空格拆词,所以 `search.py Quiz 答题`、`search.py "Quiz 答题"`
   以及 zsh 下传变量串都等价——不会因引号/未分词而静默 0 命中。

打分:命中 标题/模块 +3、摘要 +2、正文 +1(每个关键词取最高位一次)。机械活;跨篇综合交给 Claude。
"""
import os
import re
import sys
import glob

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTES_DIR = os.path.join(KB_ROOT, "notes")


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
    summary = ""
    sm = re.search(r"^##\s*摘要\s*\n+(.+?)(?=\n#|\Z)", body, re.S | re.M)
    if sm:
        summary = re.sub(r"\s+", " ", sm.group(1).strip())
    return {
        "file": os.path.basename(path),
        "module": fm.get("模块", ""),
        "version": fm.get("版本", "").split()[0] if fm.get("版本", "").strip() else "待确认",
        "title": fm.get("标题", ""),
        "related": fm.get("related", "[]"),
        "summary": summary,
        "body": body,
    }


def show(n, extra=""):
    print(f"  [{n['version']:>8}] {n['module']}  |  {n['title']}{extra}")
    if n["summary"]:
        s = n["summary"]
        print(f"            摘要:{s[:70]}{'…' if len(s) > 70 else ''}")
    print(f"            文件:notes/{n['file']}   related:{n['related']}")


def ver_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or ""))


def main():
    args = sys.argv[1:]
    notes = [parse_note(p) for p in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))]
    if not args:
        print("用法: search.py 关键词... | search.py --module 模块名 | search.py --version V1.30")
        return

    if args[0] == "--version":
        q = args[1] if len(args) > 1 else ""
        qt = ver_tuple(q)
        hits = [n for n in notes if qt and ver_tuple(n["version"])[:len(qt)] == qt]
        hits.sort(key=lambda n: (n["module"], n["title"]))
        print(f"[search] 版本匹配「{q}」的需求:{len(hits)} 篇")
        for n in hits:
            show(n)
        if not hits:
            print("  无匹配。")
        return

    if args[0] == "--module":
        key = args[1] if len(args) > 1 else ""
        hits = [n for n in notes if key in n["module"]]
        hits.sort(key=lambda n: (n["module"], n["version"]))
        print(f"[search] 模块含「{key}」的笔记:{len(hits)} 篇")
        for n in hits:
            show(n)
        return

    # 容错:每个参数再按空格拆词,避免「引号包成一串」或「zsh 下未分词的变量串」导致静默 0 命中
    #   search.py Quiz 答题  /  search.py "Quiz 答题"  /  for q in ...; search.py $q  → 都等价
    kws = [w for a in args for w in a.split()]
    scored = []
    for n in notes:
        title_mod = (n["title"] + " " + n["module"]).lower()
        summ = n["summary"].lower()
        body = n["body"].lower()
        score, where = 0, []
        for kw in kws:
            k = kw.lower()
            if k in title_mod:
                score += 3; where.append(f"{kw}@标题/模块")
            elif k in summ:
                score += 2; where.append(f"{kw}@摘要")
            elif k in body:
                score += 1; where.append(f"{kw}@正文")
        if score > 0:
            scored.append((score, n, where))
    scored.sort(key=lambda x: -x[0])
    print(f"[search] 关键词 {kws} → 命中 {len(scored)} 篇(按相关度):")
    for score, n, where in scored:
        show(n, extra=f"   (score={score} 命中:{', '.join(where)})")
    if not scored:
        print("  无命中。")


if __name__ == "__main__":
    main()
