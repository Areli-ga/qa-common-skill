#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search.py — 取①:在 notes/ 里按关键词或模块检索,列出命中笔记(写用例前查往期相关)。

用法:
    python3 scripts/search.py 关键词1 [关键词2 ...]   # 关键词检索:在 模块/标题/摘要/正文 里找(OR)
    python3 scripts/search.py --module 奖励            # 列出模块名含"奖励"的所有笔记(供"模块历史问答")
    python3 scripts/search.py --version V1.30          # 列出某版本的所有需求(本次迭代要测啥;V1.30 也匹配 V1.30.0)

注:每个参数会再按空格拆词,所以 `search.py Quiz 答题`、`search.py "Quiz 答题"`
   以及 zsh 下传变量串都等价——不会因引号/未分词而静默 0 命中。

匹配:**英文/数字关键词按词边界匹配**(前后不是 [A-Za-z0-9_]),中文照常子串。
   —— 否则 `id` 会命中 video/width,`AB` 会命中 Bahasa;中文相邻不算边界,所以 `AB` 仍能命中「AB测试」。

打分:命中 标题/模块 +3、摘要 +2、正文 +按区分度加权(每个关键词取最高位一次)。
   **正文权重按该词的库内覆盖率衰减**:≤10% 记 1.0、≤30% 记 0.6、≤60% 记 0.3、>60% 记 0.1(低区分度)。
   —— 实测改前 `search.py AB` 命中 63/102 篇、`id` 命中 68/102 篇,等于没筛;高覆盖词降权后自然沉底。
排序:先看**命中了几个关键词**(多词全中的排前),再看分数。
输出:默认只列前 15 条,`--all` 列全部(避免低分噪音刷屏、稀释注意力)。

机械活;跨篇综合交给 Claude。
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


def matcher(kw):
    """英文/数字关键词按词边界匹配,中文(或含中文)照常子串。
    词边界用 [A-Za-z0-9_] 的前后视断言,不用 \\b —— \\b 把中文也算词字符,
    会让 `AB` 匹配不上「AB测试」(B 与 测 之间没有 \\b)。"""
    k = kw.lower()
    if re.fullmatch(r"[a-z0-9_]+", k):
        pat = re.compile(r"(?<![a-z0-9_])" + re.escape(k) + r"(?![a-z0-9_])")
        return lambda text: bool(pat.search(text))
    return lambda text: k in text


def body_weight(coverage):
    """正文命中的权重按该词的库内覆盖率衰减:覆盖越广越没区分度。"""
    if coverage <= 0.10:
        return 1.0
    if coverage <= 0.30:
        return 0.6
    if coverage <= 0.60:
        return 0.3
    return 0.1


def main():
    show_all = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--all"]
    notes = [parse_note(p) for p in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))]
    if not args:
        print("用法: search.py 关键词... [--all] | search.py --module 模块名 | search.py --version V1.30")
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
    fields = [((n["title"] + " " + n["module"]).lower(), n["summary"].lower(), n["body"].lower())
              for n in notes]

    # 先算每个词的库内覆盖率(命中多少篇),用来给正文命中定权重
    hit_fns, weights = {}, {}
    for kw in kws:
        fn = matcher(kw)
        hit_fns[kw] = fn
        cov = sum(1 for tm, sm, bd in fields if fn(tm) or fn(sm) or fn(bd)) / max(len(notes), 1)
        weights[kw] = (cov, body_weight(cov))
    print("[search] 关键词区分度:" + " · ".join(
        f"{kw} 覆盖 {weights[kw][0]:.0%}→正文权重 {weights[kw][1]}"
        + ("(低区分度)" if weights[kw][1] <= 0.1 else "") for kw in kws))

    scored = []
    for n, (title_mod, summ, body) in zip(notes, fields):
        fn_score, where, matched = 0.0, [], 0
        for kw in kws:
            fn = hit_fns[kw]
            if fn(title_mod):
                fn_score += 3; where.append(f"{kw}@标题/模块"); matched += 1
            elif fn(summ):
                fn_score += 2; where.append(f"{kw}@摘要"); matched += 1
            elif fn(body):
                w = weights[kw][1]
                fn_score += w; where.append(f"{kw}@正文×{w}"); matched += 1
        if fn_score > 0:
            scored.append((matched, round(fn_score, 2), n, where))
    # 多词全中的优先,再按分数
    scored.sort(key=lambda x: (-x[0], -x[1]))

    limit = len(scored) if show_all else 15
    print(f"[search] 关键词 {kws} → 命中 {len(scored)} 篇(先按命中词数、再按相关度):")
    for matched, score, n, where in scored[:limit]:
        show(n, extra=f"   (命中{matched}/{len(kws)}词 score={score} — {', '.join(where)})")
    if len(scored) > limit:
        print(f"  … 另有 {len(scored) - limit} 篇低分命中未列出,需要全量加 --all")
    if not scored:
        print("  无命中。")


if __name__ == "__main__":
    main()
