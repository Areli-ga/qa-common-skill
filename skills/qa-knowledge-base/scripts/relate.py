#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relate.py — ingest 第④步:给 notes/ 里的笔记算关联,双向写 related。

打分(对应 SKILL.md;通用词/通用参数字段都不参与):
    score(A,B) = 2·(二级模块完全相同) + 2·|共享功能标识符|
    共享功能标识符 = 两篇都出现的功能专属 token(snake_case 含 `_` 或真驼峰,如 app_unit_reward、app_enter_quiz);
                   排除通用词、通用埋点公参,以及**参数字段命名模式**(见 identifiers)。
    score ≥ THRESHOLD(=2)→ 互相 related(双向)。
    含义:**同一个二级模块(2,= 同一功能的历次迭代)** 或 **≥1 个共享功能标识符(2)** 即关联。

⚠️ 2026-08-28 修正一:**一级模块不再作为关联信号**。实测 102 篇时,426 对关联里 251 对(59%)
   纯粹来自"同属一个一级模块"——AI Tutor 17 篇彼此全连,13 篇顶着 16 条 related,`related` 退化成
   "模块花名册"。而模块视图本就由 `INDEX.md`(按模块排序)和 `search.py --module` 覆盖,不需要 related 重复一遍。
   改用**二级模块**(如 `AI Tutor / Mai主对话`):102 篇里只有 18 对命中,且全部是同一功能的历次迭代——
   正是写用例时要的功能演进线。

⚠️ 2026-08-28 修正二:**不能用 df(文档频率)上限来剔除通用词**。清掉参数字段后实测 df 最高的是
   `lesson_speech_recognition_end`(7 篇)、`app_enter_quiz`(6 篇)—— df 高恰恰说明这个埋点被反复改动,
   是回归最该盯的信号。按 df 砍会砍掉最有价值的关联。

为什么不用中文散文相似度:标准库无可靠中文分词,bigram 重叠在"篇篇都是产品需求"时噪声极大
(实测会把所有文档连成一团)。故只用 二级模块 + 强标识符——宁可少连(漏的由模块视图/关键词检索兜底),不乱连。

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
    parts = [p.strip() for p in re.split(r"[/／]", fm.get("模块", "")) if p.strip()]
    # l2 = 完整「一级/二级」;只有一级(没写二级)时留空,不参与关联
    l2 = "/".join(parts[:2]) if len(parts) >= 2 else ""
    return {"path": path, "file": os.path.basename(path),
            "l1": parts[0] if parts else "", "l2": l2,
            "title": fm.get("标题", ""), "text": text, "body": body}


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
    # 产品名词的驼峰写法(WhatsApp / TikTok / FlashCard / GiggleCast)会被驼峰规则收进来,
    # 但它们只说明"这篇提到了某产品",不指向具体功能,实测各自连起 6–8 篇。
    # 命名规则识别不了(它们不是字段),只能列名单;好在产品名词是有限集,不会像字段名那样无限增长。
    "whatsapp", "tiktok", "flashcard", "gigglecast", "paramvalue",
}


# 参数字段命名模式:`*_id / *_name / *_type / *_count …` 是"字段",不是"功能实体"。
# 用命名规则剔除,而不是往 STOP_IDS 里一个个手加 —— 手工黑名单已经失守三次
# (level_number → image_count → block_type,每次都是新文档带进来的新字段名)。
# 实测:102 篇里被这条规则剔掉的 df≥2 标识符共 19 个,人工复核**全部**是通用参数字段,零误伤。
PARAM_FIELD = re.compile(r"_(id|name|type|count|number|code|key|token|url|time|date|status|index|version)$")
BOOL_FIELD = re.compile(r"^(is|has|need|can)_")


def identifiers(note):
    """有区分度的功能标识符:snake_case(含 _)或真驼峰([a-z][A-Z]);
    丢掉通用词与通用埋点公参(STOP_IDS),再按命名模式丢掉参数字段(PARAM_FIELD / BOOL_FIELD)。
    保留的是埋点事件名(app_enter_quiz)与 AB key(homepage_learning_order)这类功能实体。"""
    src = note["title"] + "\n" + note["body"]
    out = set()
    for t in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", src):
        t = t.strip("_")  # 正文里写 "mai_ 前缀" 会截出 "mai_" 这种碎片
        tl = t.lower()
        if not tl or tl in STOP_IDS:
            continue
        if PARAM_FIELD.search(tl) or BOOL_FIELD.match(tl):
            continue
        if "_" in t or re.search(r"[a-z][A-Z]", t):
            out.add(tl)
    return out


def main():
    write = "--write" in sys.argv
    notes = [parse_note(p) for p in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))]
    ids = {n["file"]: identifiers(n) for n in notes}
    log(f"共 {len(notes)} 篇笔记;THRESHOLD={THRESHOLD}(同二级模块=2 / 每个共享标识符=2;一级模块不计分)")

    related = defaultdict(set)
    for a, b in itertools.combinations(notes, 2):
        same = 2 if (a["l2"] and a["l2"] == b["l2"]) else 0
        shared = ids[a["file"]] & ids[b["file"]]
        score = same + 2 * len(shared)
        mark = "✅" if score >= THRESHOLD else "  "
        log(f"{mark}[{score:>2}] {a['file'][:20]:20}✕{b['file'][:20]:20} 同二级模块={bool(same)} 共享标识符={sorted(shared)[:8]}")
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
