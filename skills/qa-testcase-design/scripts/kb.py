#!/usr/bin/env python3
"""定位 qa-knowledge-base 知识库本体并转发检索(不写死任何绝对路径)。

探测顺序(全部基于 $HOME / 本文件位置,无用户名硬编码):
  1. 环境变量 QA_KNOWLEDGE_BASE_HOME(显式覆盖,最高优先)
  2. 同级 skill 目录:<skills>/qa-knowledge-base（本地或分发自包含）
找到含 scripts/search.py 的目录即用;都没有 → 退出码 3 + 降级信号,
调用方据此把「历史编译」降级为「未读 qa-knowledge-base」(SKILL.md 已有兜底)。

用法:
  python3 scripts/kb.py --locate            # 只打印定位到的本体根目录
  python3 scripts/kb.py <关键词...>         # 转发给本体 scripts/search.py
  python3 scripts/kb.py --module <模块> / --version <版本>
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

NOT_FOUND = "QA_KNOWLEDGE_BASE_NOT_FOUND"


def candidates() -> list[Path]:
    skills_dir = Path(__file__).resolve().parent.parent.parent
    out: list[Path] = []
    env = os.environ.get("QA_KNOWLEDGE_BASE_HOME", "").strip()
    if env:
        out.append(Path(os.path.expanduser(env)))
    out.append(skills_dir / "qa-knowledge-base")
    return out


def locate() -> Path | None:
    for d in candidates():
        try:
            if (d / "scripts" / "search.py").is_file():
                return d.resolve()
        except OSError:
            continue
    return None


def main() -> int:
    args = sys.argv[1:]
    kb = locate()
    if args and args[0] == "--locate":
        if kb:
            print(kb)
            return 0
        print(NOT_FOUND, file=sys.stderr)
        return 3
    if not kb:
        sys.stderr.write(
            f"{NOT_FOUND}: 未找到 qa-knowledge-base 知识库本体;历史编译降级为「未读 qa-knowledge-base」。\n"
            "  修法:设 QA_KNOWLEDGE_BASE_HOME 指向知识库根目录,或把 qa-knowledge-base 放到 skills 同级目录。\n"
        )
        return 3
    return subprocess.call([sys.executable, str(kb / "scripts" / "search.py"), *args])


if __name__ == "__main__":
    sys.exit(main())
