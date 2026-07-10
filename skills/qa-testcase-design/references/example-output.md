# 样例索引

本文件只保留兼容入口，避免旧引用断链；不要把这里当完整输出样例。

## 标准用例正文样例

读取：`references/example-testcases.md`

用途：
- 校准 `testcases.md` 的 7 块结构。
- 校准用例颗粒度、真实数据写法、覆盖自检表和待确认落点。
- 可直接用 `scripts/validate_output.py` 校验。

## 富思维导图样例

读取：`references/example-mindmap-rich.puml`

用途：
- 校准 PlantUML mindmap 的深层级表达。
- 展示测试数据组、等价类/边界值、前置/操作步骤/预期结果如何自然加深。
- 只作为高级样式参考；日常应优先由 `scripts/md_to_mindmap.py` 从 `testcases.md` 确定性生成。

## 运行示例

```bash
python3 scripts/validate_output.py references/example-testcases.md
python3 scripts/md_to_mindmap.py references/example-testcases.md /private/tmp/example-mindmap.puml
python3 scripts/validate_output.py references/example-testcases.md --mindmap /private/tmp/example-mindmap.puml
```
