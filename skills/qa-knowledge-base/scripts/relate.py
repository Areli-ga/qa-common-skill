#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relate.py — ingest 第④步:给 notes/ 里的笔记算关联,双向写 related。

打分(对应 SKILL.md 修正:只看模块 + 功能标识,通用词/通用埋点公参都不参与):
    score(A,B) = 3·(同一级模块) + 2·|共享功能标识符|
    共享功能标识符 = 两篇都出现的功能专属 token(snake_case 含 `_` 或真驼峰,如 app_unit_reward、app_enter_quiz);
                   排除 Hello/Sunny/App 这类通用词,以及 level_number/unit_number 等通用埋点公参(见 STOP_IDS)。
    score ≥ THRESHOLD(=2)→ 互相 related(双向)。
    含义:**同模块(3)** 或 **≥1 个共享功能标识符(2)** 即关联(doc1↔doc3 靠 app_unit_reward 连;公参排除后不再误连无关文档)。

为什么不用中文散文相似度:标准库无可靠中文分词,bigram 重叠在"篇篇都是产品需求"时噪声极大
(实测会把所有文档连成一团)。故只用 模块 + 强标识符——宁可少连(漏的由模块视图/关键词检索兜底),不乱连。

幂等:每次从所有笔记重算,可反复跑。
用法:
    python3 scripts/relate.py            # dry-run:只打分,不改文件
    python3 scripts/relate.py --write    # 回写每篇 frontmatter 的 related 行
"""
import os
import re
import sys
import glob
import itertools
from collections import defaultdict

KB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTES_DIR = os.path.join(KB_ROOT, "notes")
THRESHOLD = 2


def log(m):
    print(f"[relate] {m}", flush=True)


def parse_note(path):
    text = open(path, encoding="utf-8").read()
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    body = text
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            mm = re.match(r"^(\w+):\s*(.*)$", line)
            if mm:
                fm[mm.group(1)] = mm.group(2).strip()
    l1 = re.split(r"[/／]", fm.get("模块", ""))[0].strip()
    return {"path": path, "file": os.path.basename(path),
            "l1": l1, "title": fm.get("标题", ""), "text": text, "body": body}


# 通用埋点公参:几乎篇篇埋点都带,无功能区分度,不计入关联(否则会把无关文档连一起)
# 平台/通用词:iOS/Android 等会被驼峰规则([a-z][A-Z],如 iOS)误判成功能标识符,实则无区分度,一并排除
STOP_IDS = {
    "level_number", "unit_number", "level_id", "unit_id", "course_id", "course_name",
    "course_type", "part_number", "lesson_id", "lesson_number",
    "lesson_completed_count", "lesson_total_count", "user_id", "pathway",
    "ios", "android", "ipad", "iphone", "macos", "ipados",
    # fetch/meta 元信息字段名(笔记里描述抓取结果时可能出现,非功能标识符)
    "image_count", "raw_content_chars", "read_file", "doc_id", "wiki_token",
    "version_source", "version_candidates", "fetched_at",
    # 神策全埋点公参:页面/元素通用字段,篇篇埋点都带,无功能区分度(同 level_number)
    "page_name", "page_title", "page_path", "page_id", "element_name", "element_type", "position", "duration", "scene",
    # 通用内容生命周期事件:只表示"涉及课程/故事/游戏内容",不指向具体功能,会让课程类需求互相弱连。
    # 注意:功能专属事件(app_enter_quiz / app_unit_reward / word_review_* / voicerecognitionend 等)不在此列,保留其关联价值。
    "interactivelessonstart", "interactivelessonend", "lessonquit",
    "storybookstart", "storybookexit", "storybookcomplete",
    "app_game_play", "app_game_quit", "app_game_complete",
    "app_music_start", "app_flashcard_start", "app_page_view",
    "appviewscreen", "appclick",
}


def identifiers(note):
    """有区分度的功能标识符:snake_case(含 _)或真驼峰([a-z][A-Z]);
    丢掉 Hello/Sunny/App 这类通用词,以及 level_number/unit_number 等通用埋点公参(STOP_IDS)。"""
    src = note["title"] + "\n" + note["body"]
    out = set()
    for t in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", src):
        tl = t.lower()
        if tl in STOP_IDS:
            continue
        if "_" in t or re.search(r"[a-z][A-Z]", t):
            out.add(tl)
    return out


def main():
    write = "--write" in sys.argv
    notes = [parse_note(p) for p in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))]
    ids = {n["file"]: identifiers(n) for n in notes}
    log(f"共 {len(notes)} 篇笔记;THRESHOLD={THRESHOLD}(同模块=3 / 每个共享标识符=2)")

    related = defaultdict(set)
    for a, b in itertools.combinations(notes, 2):
        same = 3 if (a["l1"] and a["l1"] == b["l1"]) else 0
        shared = ids[a["file"]] & ids[b["file"]]
        score = same + 2 * len(shared)
        mark = "✅" if score >= THRESHOLD else "  "
        log(f"{mark}[{score:>2}] {a['file'][:20]:20}✕{b['file'][:20]:20} 同模块={bool(same)} 共享标识符={sorted(shared)[:8]}")
        if score >= THRESHOLD:
            related[a["file"]].add(b["file"])
            related[b["file"]].add(a["file"])

    log("=== 关联结果 ===")
    for n in notes:
        log(f"  {n['file']}  →  {sorted(related[n['file']]) or '[]'}")

    if not write:
        log("dry-run 完成(未改文件)。确认无误后:python3 scripts/relate.py --write")
        return
    for n in notes:
        rel_line = "related: [" + ", ".join(sorted(related[n["file"]])) + "]"
        new = re.sub(r"^related:.*$", rel_line, n["text"], count=1, flags=re.M)
        if new != n["text"]:
            open(n["path"], "w", encoding="utf-8").write(new)
            log(f"  回写 {n['file']}: {rel_line}")
    log("已回写所有 related。")


if __name__ == "__main__":
    main()
