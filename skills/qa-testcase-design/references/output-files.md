# 交付文件与校验

## 交付目录

每次真实执行都建一个独立交付目录，避免多次生成互相覆盖。推荐命名：

```text
<系统临时目录>/qa-testcase-design-<需求短名>-<YYYYMMDD-HHMM>/
```

系统临时目录按平台取：macOS 为 `/private/tmp`，Linux 为 `/tmp`（即 Python `tempfile.gettempdir()` 的结果，勿硬编码 macOS 路径）。用户指定目录时用用户目录。不要写入 qa-knowledge-base 知识库本体。

## 必产文件

| 文件 | 何时生成 | 说明 |
|---|---|---|
| `testcases.md` | 每次必产 | 7 块结构化用例正文，供 QA 评审和执行；包含 `showcase（提测准入）`，用例主体按业务功能/需求类目组织 |
| `history-hits.md` | 每次已读 qa-knowledge-base 时必产 | 历史检索证据；qa-knowledge-base 不可达时也写明未读原因 |
| `mindmap.puml` | 用户需要飞书思维导图时生成 | 由 `scripts/md_to_mindmap.py` 从 `testcases.md` 转换 |
| `images-notes.md` | **有图片就必产**（并行读图代理或主线串行读图都要落盘） | 逐图转录（文案/字段/数值/状态/流程/异常）；主线合流验收后作为出例依据之一，关键图仍需主线复核原图。**图少或串行读图也不省略这份留档** |

如果飞书链接读取产出 `content.txt / tables.md / tables.json / blocks.json / images/ / meta.json`，这些读取产物放在同一交付目录的 `source/` 下。

## 飞书文档发布

除非用户明确要求只要本地文件，最终交付还要新建飞书 docx，并把本地交付内容写入用户当次指定目录；没有当次指定目录时，写入默认飞书 Drive 文件夹。**发布成功到该目录才算本轮结束**。默认目录和失败处理只以 `references/lark-output.md` 为准。

发布脚本默认会先复用 `validate_output.py` 做结构校验；校验失败会中止发布，避免把坏结构写进飞书。因此本地校验通过后**直接发布**（`--target` 缺省即默认 Drive 文件夹，见 `lark-output.md`；`--dry-run` 只在排查渲染异常时用）：

```bash
python3 scripts/publish_to_lark_doc.py <交付目录>
```

发布成功后在最终回复里同时给出飞书文档链接和本地交付目录；发布失败时报告飞书 `code/msg`、本地交付目录和建议动作，但不能把本地文件视为最终完成。

`--skip-validate` 只用于手动恢复旧归档，不用于正常交付。

## 校验命令

交付前必须先跑结构校验：

```bash
python3 scripts/validate_output.py testcases.md --history history-hits.md
```

如果生成了思维导图，再跑：

```bash
python3 scripts/md_to_mindmap.py testcases.md mindmap.puml
python3 scripts/validate_output.py testcases.md --history history-hits.md --mindmap mindmap.puml
```

校验通过后再交付文件路径和飞书复制提示。

## 校验失败时

- 先修 `testcases.md` 或 `history-hits.md`，不要让用户手动修格式。
- 用例 ID 不一致时，以 `testcases.md` 的叶子 ID 为准，同步修覆盖自检表和 `history-hits.md`。
- `case id missing from coverage table` 表示用例没有进入覆盖自检表；补到最贴近的业务维度或 APP 常驻维度。
- `coverage table missing APP permanent dimension` 表示常驻维度缺失；无关时补 `N/A`，不要删除。
- `showcase should contain 1-5 cases` 表示把完整回归集放进了提测准入；只保留核心演示路径。
- `pending case ... must be referenced in 风险与待确认` 表示待确认用例没有 Q 项落点；补风险表，不要把待确认原因塞进叶子。
- `history-hits.md` 保留/待确认行没有编入位置时，补落到用例、Q 项、风险判断或覆盖自检表；说不清影响的命中改为丢弃。
- mindmap 中出现 `风险与待确认`、`history-hits`、`历史回归`、`qa-knowledge-base` 等正文/附录信息时，说明正文结构放错了；风险确认和附录不要进思维导图。
