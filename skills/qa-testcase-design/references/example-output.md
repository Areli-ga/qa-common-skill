# 样例索引（兼容入口）

本文件只保留兼容入口，避免旧引用断链。

- 标准用例正文样例：`references/example-testcases.md`——校准 7 块结构、先树后例、原子用例、自检表与待确认落点；可直接过 `validate_output.py`。
- 富思维导图样例：`references/example-mindmap-rich.puml`——仅示范手写 PlantUML 块的深层表达，日常导图一律由 `md_to_mindmap.py` 从分解树生成。

运行示例（`/tmp` 在 macOS 上即 `/private/tmp`）：

```bash
python3 scripts/validate_output.py references/example-testcases.md
python3 scripts/md_to_mindmap.py references/example-testcases.md /tmp/example-mindmap.puml
```
