# 交付文件与校验

## 交付目录

每次执行第一步就建独立交付目录，后续所有产物落这里：

```text
/tmp/qa-testcase-design-<需求短名>-<YYYYMMDD-HHMM>/
```

`/tmp` 在 macOS 上即 `/private/tmp`、Linux 上即 `/tmp`，两端通用，不要写 `tempfile.gettempdir()`（macOS 上它返回 `/var/folders/...`）。名字含时分，避免同日多次生成互相覆盖。用户指定目录时用用户目录。不要写入 qa-knowledge-base 知识库本体。系统临时目录重启可能被清空，交付以飞书文档为长期留档。

## 交付目录结构

| 文件 | 何时生成 | 说明 |
|---|---|---|
| `source/` | 飞书链接输入时必产 | `read_doc.py` 产物：`content.txt / tables.md / tables.json / blocks.json / images/ / meta.json` |
| `images-notes.md` | **有图片就必产** | 逐图转录（每图一节 `【图NN｜文件名】`）；分片读图时为 `images-notes-<分片>.md`，主线合并为 `images-notes.md` |
| `history-hits.md` | 每次必产 | 历史检索证据；qa-knowledge-base 不可达时也要产出，写一行判定为 `未读` 的数据行并说明原因（格式见 `history-kb-contract.md`） |
| `testcases.md` | 每次必产 | 6 块结构化用例正文（规则：`authoring-core.md` §C），完整用例与 ID 的唯一源 |
| `mindmap.puml` | 每次必产（发布依赖） | `md_to_mindmap.py` 从 `testcases.md` 确定性生成；仅「只本地输出且明确不要导图」时可省 |
| `publish_state.json` | 发布中断时自动生成 | 发布断点；成功后自动删除 |

## 校验命令（交付前必须 PASS）

一条命令校验整个交付目录（自动发现上表文件）：

```bash
python3 scripts/md_to_mindmap.py <交付目录>/testcases.md <交付目录>/mindmap.puml
python3 scripts/validate_output.py --dir <交付目录>
```

`--dir` 会依次检查：`testcases.md` 结构与粒度、`history-hits.md` 证据与四类检索词、`mindmap.puml` 结构、`source/tables.md` 数值对账（WARN）、`images-notes.md` 是否覆盖 `content.txt` 全部【图NN】占位。只校验单个文件时仍可用 `validate_output.py testcases.md [--history …] [--mindmap …] [--tables …]`。

WARN 不阻断发布，但每条都要处理：数值对账遗漏 → 补用例或写进「风险与待确认」；期望过长/分号串联 → 拆原子用例。

## 飞书发布

除非用户明确要求只本地输出，校验 PASS 后直接发布（发布脚本会以同样规则再校验一次，`--dry-run` 只在排查渲染异常时用）：

```bash
python3 scripts/publish_to_lark_doc.py <交付目录> [--target "<用户指定目录>"]
```

**发布成功并拿到飞书文档链接才算完成**；最终回复同时给出飞书链接和本地交付目录。发布失败时报告 `code/msg`、本地交付目录和建议动作，不能把本地文件视为完成。默认目录、呈现规则、续传与失败处理见 `lark-output.md`。`--skip-validate` 只用于手动恢复旧归档。

## 校验失败时

先修文件，不要让用户手动修格式。

| 报错 | 修法 |
|---|---|
| `missing section` | 六块标题逐字对齐 authoring-core §C 骨架 |
| `no executable case lines found` | 用例行放进 ` ```text ` 块，行首直接 `[P0-01]` |
| `case id missing from coverage table` | 把该 ID 补进最贴近的业务维度或 APP 常驻维度 |
| `coverage table missing APP permanent dimension` | 补该常驻维度行，无关写 `N/A` + 理由 |
| `showcase 块已取消` | 删掉 `## showcase（提测准入）` 块，其中用例移入用例设计对应分组（期望改成单断言），覆盖表删除 showcase 行 |
| `pending case … must be referenced in 风险与待确认` | 补 Q 项并在影响列写该 ID |
| `风险与待确认 …级别` | 表头改为 `编号 \| 级别 \| 问题 \| 影响`，级别填 `阻断 / 已确认 / 记录` |
| `风险与待确认 Qn 为阻断级` | 停下把这些 Q 问用户；答复后改 `已确认` 并在问题列写「用户确认：…」，不得自行改级别 |
| `组下 N 条用例但无 #### 细分` | 按分解树拆：数值逐项、分支逐行、结局逐个成节点 |
| `期望 … 字` / `期望用「；」串联` | 拆成多条原子用例 |
| `第一层 ### 须按端分` | 第 3 块先分 `### Admin`、`### App`（需要直接调接口才加 `### 服务端`），原分组下移一层到对应端下；跨端用例挂在看结果的一端，另一端操作写成 `前置：…` 节点 |
| `用了 PRD 表号/图号/规则编号/示例` | 分组改用页面、控件、数据或状态命名（如「表 4 示例路径」→「第 15 单元复习 / 单元目标（只读）」）；规则对应关系只写在业务规则追溯表 |
| `叶子不再写前置/步骤` | 共用前置写成上一层树标题（如 `##### 前置：N=5`），步骤压成一句操作，叶子只留 `操作｜期望：结果` |
| `missing ｜期望：` | 每条用例补 `｜期望：<一个可判定结果>` |
| `history … 编入位置` | 保留/待确认行补落点（用例 ID / Q 项 / 风险判断 / 覆盖自检表）；说不清影响就改判丢弃 |
| `history missing query group` | 补该类检索词行；PRD 确无对应信息时判定写 `未命中` 并说明 |
| `images-notes … 未覆盖` | 每张图单独一节、行首写 `【图NN｜文件名】`；略读图也要一节写原因，不能在一行里列多个图号 |
| `业务规则追溯 …` | 第 1 块末尾补 `### 业务规则追溯` 表（`编号 \| 规则 \| 来源 \| 落点`）；落点为空 → 补用例或在第 5 块加 Q 项后写 Q 编号；引用了不存在的 ID / Q → 改成真实编号 |
| `history row has N columns` | 每个数据行写满 5 列，空值写 `-` |
| `history missing query group`（声明了未读） | 未读要写成判定列为 `未读` 的数据行，表外备注不算 |
| mindmap 附录 / 占位节点 | 正文结构放错了：附录内容不进导图；「其他业务场景」= 用例没挂树也没进自检表 |

用例 ID 不一致时，以 `testcases.md` 叶子 ID 为准，同步修覆盖自检表和 `history-hits.md`。
