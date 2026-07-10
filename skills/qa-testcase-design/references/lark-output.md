# 飞书文档发布规则

## 默认发布目录

用户已确认默认把每次新的测试用例文档放到以下飞书 **Drive 文件夹**下：

```text
https://wsgh3q8mwfpp.sg.larksuite.com/drive/folder/IL00fkfpolXGovdWl4FlPRe1gyg
```

实测（2026-07-02）：机器人对该文件夹**有写权限**，用 `folder_token` 直接建 docx 成功。此前的 Wiki 节点因挂载权限写不进、已弃用。这是 Drive 文件夹，按 `drive_folder` 处理、传 `folder_token`，不走 wiki 挂载。

**凭证（2026-07-05 起）**：`publish_to_lark_doc.py` 与 `read_doc.py` 用**同一套凭证**——环境变量 `LARK_APP_ID/SECRET/DOMAIN`，缺失则拉 config 服务 `skill-config.giggletools.com`（需 VPN）换 `tenant_access_token` 直调 Lark API，**不再走 giggle-common gateway / CF Access 登录**。注意 config 返回的 `LARK_DOMAIN` 是 `open.feishu.cn`（国内站），而链接/文件夹是 `larksuite.com`（国际站）——二者是**同一租户的两个接入域名、数据互通**：用 feishu.cn 凭证建的 docx，通过 larksuite 链接也能访问（发布返回的 `document_url` 用 larksuite host）。

用户明确要求换目录时，以用户当次提供的目录为准。除非用户明确要求只本地输出，**每次测试用例生成都必须发布到用户当次指定目录；未指定时发布到上述默认目录。发布成功到目标目录才算完成。**

## 发布呈现规则（2026-07-06 起）

飞书文档定位「评审 + 看图」，不是过程存档；`publish_to_lark_doc.py` 发布时自动做**呈现层裁剪**（本地 `testcases.md` / `history-hits.md` 始终保留完整，不受影响）。

- **跳过三个过程块**：`showcase（提测准入）`、`用例设计（按业务功能 / 需求类目组织）`、`APP 常驻维度补充`——它们的全部用例已由思维导图完整承载（showcase 是导图第一个一级节点）。
- **思维导图顶替其位置**：`用例设计思维导图（PlantUML）` 插在风险判断之后、占用顺序编号，剩余块自动重编号（需求理解 → 风险判断 → 思维导图 → 风险与待确认 → 覆盖自检表）。
- **覆盖自检表压缩**：「对应用例」ID 列改为「用例数」——飞书里正文用例块已裁、思维导图又隐藏 ID，ID 是死引用；按 ID 追溯回本地 `testcases.md`。
- **风险与待确认表「影响」列改写（2026-07-08 起，用户实评反馈）**：影响列的用例编号（P0-xx 等）在飞书文档里同样是死引用，发布时按覆盖自检表反查改写为**所属维度名**（如 `P0-09、P0-10 → 连击与必杀状态机`）；编号仍保留在本地 `testcases.md` 供追溯。
- **历史命中摘要**：`history-hits.md` 表格发布时砍掉「编入位置」列，保留「检索词组 ｜ 命中笔记 ｜ 判定 ｜ 理由」四列表格；去掉自带 h1 标题避免与「历史命中摘要」标题重复。
- **固定 QA 表格列宽**：风险与待确认、覆盖自检表、历史命中摘要三类表格按用户手动调好的列宽写入 `column_width`，避免每次发布后手动拖列。
- **发布前强制校验**：脚本默认先跑交付结构校验；只有手动恢复旧归档时才允许加 `--skip-validate` 跳过。

**思维导图交付（2026-07-06 实测）**：发布后飞书文档里的 PlantUML 代码块**可直接复制粘进飞书画板、完美兼容**（长行不折断）。所以首选路径：**打开发布好的飞书文档 → 复制「用例设计思维导图（PlantUML）」代码块 → 粘进画板**，不必再开本地 `.puml`。本地 `mindmap.puml` 仍保留作备份/校验。

## 发布原则

- 先生成并校验本地交付目录，再发布到飞书；飞书发布失败不能导致本地交付丢失。
- 除非用户明确要求只本地输出，发布成功是完成门槛；只生成本地文件不算结束。
- 每次发布都新建一篇 docx，不覆盖、不清空、不修改历史测试文档。
- 不修改原 PRD、不修改 qa-knowledge-base、不把输出写入 qa-knowledge-base 知识库本体。
- 不为了验证发布能力而创建临时测试文档；需要真实写入测试时先得到用户明确同意。
- `mindmap.puml` 以 PlantUML 代码块写入飞书文档；不要承诺 API 能直接生成飞书画板原生思维导图。
- 不发布 `mindmap.puml.txt`，该副本类型已从规则中移除。

## 飞书文档内容

飞书文档承载完整交付内容：

1. `testcases.md` 正文结构
2. `mindmap.puml` PlantUML 代码块（若生成）
3. `history-hits.md` 历史命中证据（若生成）
4. 交付文件清单

本地文件仍是源交付物；飞书文档是便于评审、沉淀和转发的发布渠道。

## 目标类型

| 目标链接 | 处理方式 |
|---|---|
| `/wiki/<token>` | 先 `wiki/v2/spaces/get_node` 解析 `space_id/node_token`，再创建 docx 并挂到该 Wiki 父节点下 |
| `/drive/folder/<folder_token>` | 创建 docx 时直接传 `folder_token` |

当前默认目录属于第二类（Drive 文件夹）。

## 发布命令

在 skill 目录执行（`--target` 缺省即上面的默认 Drive 文件夹，脚本内置同一 URL 作为 default；用户指定其他目录时才传 `--target`）：

```bash
python3 scripts/publish_to_lark_doc.py <交付目录>
```

脚本默认会先校验 `testcases.md`，如果存在 `history-hits.md` / `mindmap.puml` 也会一并校验——所以本地 `validate_output.py` 通过后**直接发布，不需要先跑 `--dry-run`**（那是第三重校验，纯耗时）。`--dry-run` 降级为排查工具：只在渲染结果异常、需要本地检查 payload 时用。`--skip-validate` 只用于手动恢复旧归档，不用于正常交付。发布默认 `--permission=tenant_editable`（**会放开租户内链接分享**，便于团队打开评审）；若不想改分享权限，传 `--permission=skip`。

发布成功后，脚本会把 `document_id/document_url/wiki_node/link_share_entity` 写回 `source/meta.json` 的 `lark_output` 字段（如果 `source/meta.json` 存在）。

**断点续传（2026-07-08 起）**：发布每写入一段就把进度存到交付目录 `publish_state.json`（成功结束自动删除）。append 阶段中途失败时**重跑加 `--resume` 从断点继续**，复用已建文档、不重复建档、不产生重复块；本地交付内容或目标目录变了会拒绝续传。存在未完成状态而未带 `--resume` 时脚本直接报 `resume_guard` 拒绝重发；确要放弃半成品重发，先手动删除半成品文档再加 `--fresh`。

## 失败处理

- 创建 docx 失败：报告 `code/msg` 和本地交付目录；标记为发布阻塞，不要声称完成。
- 追加内容失败：报告已创建的文档 ID/URL 和失败 `code/msg`；进度已存 `publish_state.json`，优先用 `--resume` 续传而不是重发；不要重试到产生重复文档，除非用户要求；标记为发布阻塞。
- Wiki 挂载失败：报告 docx 已创建但未挂到目录下；给出失败 `code/msg`；标记为发布阻塞，让用户决定是否换目录或手动移动。
- 权限设置失败：报告文档已创建但链接权限未放开；不要静默成功；标记为发布阻塞。
