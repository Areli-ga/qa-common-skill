---
name: qa-testcase-design
description: Use when 用户提供 Giggle Academy PRD、飞书链接、粘贴需求、提测范围或回归关注点，并要求设计中文 QA 测试用例、测试覆盖方案或 PlantUML 思维导图。
---

# 测试用例设计引擎

把「本次需求 + 覆盖清单 + qa-knowledge-base 历史知识」编译成全面、按风险排序、可执行的结构化用例中间产物。v2 质量靠四支柱：逐维防漏、风险立场、测试设计方法、历史编译。

## 边界（先读）

- 核心产物是**格式无关的结构化用例**；可再渲成**飞书思维导图**（PlantUML `.puml` 文件，见 `references/mindmap-plantuml.md`）；Excel/XMind 等其他格式交后续。
- 不编造产品逻辑 / 接口字段 / AB 策略 / 视觉标准；缺信息一律写「待确认」。
- 出例前**只读检索 qa-knowledge-base 历史**补足用例（按 `references/history-kb-contract.md`：只读、不 ingest、不回写、不迁移）。
- 不做：往回织回流、用例管理、执行报告、自动化脚本。飞书发布只负责新建交付 docx，不修改原 PRD、不覆盖历史测试文档、不写 qa-knowledge-base。除非用户明确要求只本地输出，否则**发布成功到用户指定/默认飞书目录才算完成**。

## 复用资源（不重造）

- **出例核心手册（一次读取，覆盖步 4-7）**：`references/authoring-core.md` = 覆盖维度（§A）+ 测试设计方法（§B）+ 用例结构/优先级/自检表（§C）合并装载版；原文件 `coverage-dimensions.md` / `case-schema.md` / `test-design-methods.md` 保留作深度参考，冲突时以原文件为准
- 代码风险库按端命中才读：`references/code-risk-backend.md`、`code-risk-unity.md`、`code-risk-native.md`、`code-risk-h5.md`
- 交付目录 / 文件落盘 / 校验：`references/output-files.md` + `scripts/validate_output.py`
- 样例输出（**只在校验失败排查或首次接触本 skill 时读**）：`references/example-testcases.md`（标准 7 块正文样例）+ `references/example-mindmap-rich.puml`（富 PlantUML 层级样例）；`references/example-output.md` 仅作兼容索引
- 只读取图脚本：`scripts/read_doc.py`（飞书正文 + `tables.md/json` + 下载全部图片；技术内核同 qa-knowledge-base `fetch.py`；凭证走环境变量或公司 config/VPN）
- 历史知识只读契约（**已启用**）：`references/history-kb-contract.md` + 检索脚本 `qa-knowledge-base/scripts/search.py`
- 出飞书思维导图：`scripts/md_to_mindmap.py`（testcases.md → 合法 `.puml`，确定性转换，默认完整评审图；按需 `--compact`）+ 规则 `references/mindmap-plantuml.md`
- 发布到飞书文档：`references/lark-output.md` + `scripts/publish_to_lark_doc.py`（本地交付校验通过后，新建 docx 并写入默认飞书 Drive 文件夹；具体目录只以 `lark-output.md` 为准）

## 工作流（v2 · 8 步）

**1 进** — 接收需求。飞书链接 / 粘贴文本 + 可选：本次改动点、影响端范围、提测说明、配置/AB 范围。**第一步先按 `references/output-files.md` 命名建独立交付目录**（`<系统临时目录>/qa-testcase-design-<短名>-<YYYYMMDD-HHMM>/`，macOS 为 /private/tmp、Linux 为 /tmp，含时分避免同日覆盖），后续所有产物落该目录。

**2 保真读取** — 飞书链接调 `scripts/read_doc.py`（与 qa-knowledge-base `fetch.py` 同一类读法：blocks 接口 + 表格抽取 + 下载全部图片 + sips 缩放）。调用签名：`python3 scripts/read_doc.py "<飞书链接>" --out <交付目录>/source [--allow-partial] [--resume]`（输出目录也可用第二个位置参数；未知 `--xxx` 会报错退出）。**读取中断（图多/网络慢/进程被杀）时，用同一输出目录加 `--resume` 重跑**：复用已落盘的正文/blocks/图片、只补缺的部分，不必整篇重来。产出 `content.txt / blocks.json / tables.md / tables.json / images/ / meta.json`；图片下载失败默认中止，只有用户接受部分读取时才加 `--allow-partial`（注意 `--allow-partial` **只放宽图片下载失败**；正文/blocks/凭证读取失败仍会中止）。脚本报「未解析内容块」（电子表格 Sheet/任务等）时，把它登记进「风险与待确认」，不要静默忽略。粘贴文本无图，跳过步 2.5 的读图代理，并标「未读取图片/表格原始结构」风险。

**2.5 并行装载（省时关键）** — 保真读取落盘后，**在同一条消息里并行派出两个只读子代理**（**默认就派代理**；仅当图 ≤6 张且需求简单、无复杂交互时才可主线串行读图/检索，产物一样不能少），主线不等待、直接继续步 3：
- **读图代理**（有图片时）：输入交付目录 `source/images/` 全部图片 + `content.txt` 的图片占位编号。任务：逐图转录**图内全部文案原文、字段名、数值/阈值、状态、按钮、流程走向、异常/空态**，产出交付目录下 `images-notes.md`（每图一节 `【图NN｜文件名】` + 结构化转录 + 一行「本图对用例的信号」）。读图策略：≤6 张全读；>6 张先全量粗筛再精读 UI 状态/流程/字段/配置/异常关键图，竞品图/纯装饰图略读但必须登记原因。**耗时约束（防止读图卡住合流）**：>8 张时拆 2-3 个读图代理分片并行（每代理 ≤6 张，各写 `images-notes-<分片>.md`，主线合并）；每图以一次通读为主，仅超宽/文字密集且通读不清的图允许**至多一轮**局部放大复核，不做反复裁剪迭代。禁止推断图里没画的逻辑；看不清的写「不清晰待人工复核」，交给主线合流时定夺。
- **历史代理**：严格按步 3.5 全文 + `references/history-kb-contract.md` 执行（全程只读 qa-knowledge-base），产出交付目录下 `history-hits.md` 草稿。**需求背景必须由代理自己读交付目录 `source/content.txt` + `tables.md` 提取检索词，主线只传交付目录路径，禁止凭记忆转述需求主题**（转述失真会让整轮检索跑偏且难以察觉）。
- **合流验收（出例前必须完成）**：主线核对 ①`images-notes.md` 覆盖 `content.txt` 全部图占位（或登记略读原因），**P0 主链路判定所依赖的关键图，主线必须亲自读原图复核**，不能只信转录；②`history-hits.md` 满足最小检索词组且抽查 1-2 条保留/丢弃判定合理。任一代理失败、超时或产物验收不过 → 主线按老串行流程自己补做（读图按上面策略、历史按步 3.5），**不允许缺着产物出例**。无子代理能力的环境直接走串行；**串行读图时主线同样把逐图转录落盘为 `images-notes.md`（有图就产，图少也不省略）**。

**3 对齐** — 用自己的话复述需求理解（目标/入口/路径/状态/端/接口/AB/配置/埋点/验收口径），并列出 PRD 没写清的**待确认项**。不编造。**务必读 `read_doc` 产出的 `tables.md`**：反馈分支表→状态迁移、数值设定表→边界值、多条件表→判定表，是用例金矿，别只读正文。只有待确认影响 P0 主链路、接口/配置/AB 发版口径、测试环境前置条件时才停下问用户；普通缺口写入「风险与待确认」并继续产出。

**3.5 历史编译（读 qa-knowledge-base）** — 默认由步 2.5 的历史代理按本步全文执行，主线只做合流验收；代理不可用或验收不过时主线自己执行本步。规则：先读 `references/history-kb-contract.md`，随后先按 `qa-knowledge-base` skill 读取本体规则与现状；全程只读，不写 qa-knowledge-base 知识库本体。在本次输出目录维护 `history-hits.md` 检索证据，至少覆盖最小检索词组：模块词、功能词、埋点或字段词、相邻入口词（有版本再加版本词）。从 PRD 提检索词（模块/版本/需求标题/核心功能/入口/状态/配置/AB/接口字段/埋点事件/端范围），跑：
```bash
python3 scripts/kb.py <关键词>   # 或 --module 模块 / --version 版本；kb.py 自动定位 qa-knowledge-base 本体，找不到则历史编译降级为「未读 qa-knowledge-base」
```
按契约筛命中（**同模块或共享标识符才留**；排除 登录/首页/按钮/level_number 等通用高频词），并在 `history-hits.md` 记录检索证据：检索词组、命中笔记、判定、保留/丢弃理由、编入位置。**不能只看 search.py 摘要**；`search.py` 只负责召回，保留/待确认的命中必须深读 `notes/*.md` 后，才能把相关**历史逻辑 / 旧边界 / 相邻入口 / 回归线索**编入后续 风险判断 / 用例 / 待确认。**只读，绝不写 qa-knowledge-base；不覆盖 PRD，冲突进「风险与待确认」**。qa-knowledge-base 不可达或未命中时，明确写「未读 qa-knowledge-base」/「未命中相关历史」，继续产出。
对 Top 1-3 个高风险历史命中，如果 notes 信息不足（接口字段、AB/配置、埋点、阈值、端差异、图表细节或 PRD 冲突没写清），必须回看 `raw/` 原料或原飞书链接；仍只读，不写 qa-knowledge-base，并在 `history-hits.md` 记录“已回看 / 不足 / 不可达”及最终落点。

**4 立场** — 先读一次 `references/authoring-core.md`（覆盖步 4-7 全部规则，后续步骤不再重复读原三件）。然后判断「**本次改动真正的高风险在哪、最该测什么**」，写风险判断 + 理由。这决定后面 P0 排序，不是一碗水端平。写法按 §C「风险判断写法」：一句点题 + 3-5 个 `- ` 要点分行，不要写成一大坨长段落。

**5 防漏** — 按 `authoring-core.md` §A 覆盖维度**逐维过闸**。每维只能是「已覆盖 / N/A / 待确认」，禁止默默跳过；判定标准见 §C 覆盖自检表。代码风险库按端范围读取：涉及后端读 `code-risk-backend.md`，涉及 Unity 读 `code-risk-unity.md`，涉及 Android/iOS 原生读 `code-risk-native.md`，涉及 H5/WebView 读 `code-risk-h5.md`；不涉及的风险库标 N/A，不全量灌入。若手册读取失败（路径变动），停下提示用户，不要凭记忆编维度。

**6 出例** — **先树后例**：先在第 4 块用 `###/####/#####` 多级标题把需求拆成分解树（业务功能→状态机/分支矩阵/数值组→细分支；数值逐项、分支逐行、结局逐个成节点），用例只挂叶层——思维导图直接由这棵树长出来，结构塞进用例行文字里等于丢失。每条用例是**原子断言**（一例只验一个可判定结果，禁止打包多个数值/链路）。出例前，对每个功能点/维度**先按 `authoring-core.md` §B 的「特征→方法」决策表挑 1–2 个测试设计方法**（边界值/判定表/状态迁移/场景法/正交/错误推测等），再用该方法把用例设计到位。复杂交互类需求先按 PRD 表格/流程图拆成状态机与分支矩阵：状态表→状态迁移，新旧差异表→回归对比，提前发声/未发声/正确/错误/超时/跳过→判定表，行为绑定埋点→行为 + 数据成对校验。先提取 `showcase（提测准入）`：从核心主路径中抽 1–5 条演示测试 case，供开始提测时现场演示；这些 case 不通过，就不达到提测标准。方法只用于设计推导；输出时不展开方法论长篇，只在覆盖自检表「说明」里按需短标 `方法=边界值/判定表/状态迁移`。然后按 `authoring-core.md` §C 的 7 块骨架 + 叶子格式输出用例（⚠️ 格式硬规则：用例行必须放进 ```text 代码块、行首 `[Px-xx]` 不带 `- `、七块标题逐字一致，否则 `validate_output.py` 直接 FAIL、无法自动发布；详见 §C「机器校验硬规则」）：正文用例按业务功能/需求类目/状态机组织，P0/P1/P2 只作为 `priority=P0/P1/P2` 和 ID 追踪，不作为一级目录。步骤具体可执行，禁空泛。缺口不在叶子里逐条标，统一汇总到「风险与待确认」块。

**7 自检、发布与交付** — 按 `authoring-core.md` §C 输出**覆盖自检表**（维度 | 状态 | 对应用例 | 说明），让用户一眼看漏没漏。按 `references/output-files.md` 建独立交付目录（目录名含 `<YYYYMMDD-HHMM>` 到分钟，避免同日多次生成互相覆盖），落盘 `output-files.md` 必产清单里的文件（`testcases.md`、`history-hits.md`，**有图时含 `images-notes.md`**），再跑 `python3 scripts/validate_output.py testcases.md --history history-hits.md`；校验通过后继续发布。用例用**单一格式**交付（不带 `来源/待确认` 字段）。除非用户明确要求“只本地输出”，最终必须按 `references/lark-output.md` 新建飞书 docx，并发布到用户当次指定目录；没有当次指定目录时发布到默认飞书 Drive 文件夹。**发布成功并拿到飞书文档链接后才算完成；发布失败只算阻塞，不能把本地文件当最终完成。**

> **出飞书思维导图（用户要时）**：先把用例正文落成 `testcases.md`，再跑 `python3 scripts/md_to_mindmap.py testcases.md mindmap.puml`（**确定性转换，不要 AI 手抄渲染**——手抄会重复/断行/报错）。默认输出**完整评审图**：`showcase（提测准入）` + 按需求/业务功能归类的一级菜单 + APP 常驻维度（边界/兼容、跨端联动、后端/配置、AB、埋点、多语言兼容），并在用例下挂 `前置 / 操作步骤 / 预期结果`。`需求理解`、`P0/P1/P2`、`风险与待确认`、`覆盖自检表`、`history-hits.md` 不进入思维导图；P0/P1/P2 只作为优先级属性和 ID 追踪。用户只要主结构时加 `--compact`。生成后跑 `python3 scripts/validate_output.py testcases.md --history history-hits.md --mindmap mindmap.puml`。规则细节见 `references/mindmap-plantuml.md`。交付提示：**先清空飞书 PlantUML 编辑框 → 复制来源全选 → 只粘一次**（编辑框残留叠加、或长行从对话复制被折断，都会导致飞书解析报错，已实测踩坑）。复制来源二选一:①**已发布飞书文档里的思维导图代码块**（2026-07-06 实测可直接复制、完美兼容,推荐,省去开本地文件）②本地 `mindmap.puml` 全选。**都不要从对话里复制**（长行会折断）。

> **发布到飞书文档（默认要做，完成门槛）**：本地文件和校验全部通过后，按 `references/lark-output.md` 运行 `python3 scripts/publish_to_lark_doc.py <交付目录>`；用户当次指定目录时传 `--target "<用户指定目录>"`，否则使用默认 Drive 文件夹。发布脚本默认会再次校验 `testcases.md` / `history-hits.md` / `mindmap.puml`，只新建 docx；飞书文档承载评审所需内容：需求理解、风险判断、**用例设计思维导图（PlantUML，承载 showcase / 用例设计 / APP 常驻三块用例）**、风险与待确认、覆盖自检表、历史命中摘要、交付文件清单；**showcase / 用例设计 / APP 常驻三块正文不在飞书展示、由思维导图承载**，完整 7 块正文以本地 `testcases.md` 为准（呈现规则详见 `references/lark-output.md`）。不承诺 API 直接生成飞书画板原生思维导图。默认目录和失败处理只看 `references/lark-output.md`。如果飞书发布失败，报告失败 `code/msg`、本地交付目录和下一步处理建议；**不要声称任务完成，也不要等用户提醒才重试或改目录**。写入中途失败时进度已存交付目录 `publish_state.json`，**重跑加 `--resume` 从断点续传**（复用已建文档、不重复建档）；检测到未完成状态而未带 `--resume` 时脚本会拒绝直接重发（防止堆出重复半成品），确要重发用 `--fresh` 并手动删除半成品文档。

末尾提示：执行后如发现新缺陷/新回归点，建议后续 ingest 回 qa-knowledge-base（v1 不自动做）。

## 质量门槛（交付前自检）

- [ ] 覆盖清单每一维都有明确状态，无默默跳过
- [ ] 已提取 `showcase（提测准入）`，且它覆盖核心主路径；这些 case 不通过则不达到提测标准
- [ ] `showcase（提测准入）` 只保留 1-5 条核心演示 case，没有把完整回归集塞进去
- [ ] 关键功能点用了对应测试设计方法（边界值/判定表/状态迁移等），非平铺
- [ ] 正文用例已按业务功能/需求类目/状态机组织，P0/P1/P2 只作为优先级属性
- [ ] 复杂交互已按状态机/分支矩阵拆解，不按优先级平铺
- [ ] 第 4 块是多级分解树（###/####/#####），数值逐项、分支逐行、结局逐个成节点；无「功能点/其他」占位层
- [ ] 每条用例是原子断言（一例一个可判定结果），无打包多数值/多链路的长期望
- [ ] 已跑 `validate_output.py --tables source/tables.md` 数值对账，PRD 表格里的数值全部落入用例或已说明
- [ ] 每条用例可直接执行，无「验证功能正常」空泛叶子
- [ ] 缺口已汇总到「风险与待确认」块，无编造
- [ ] 若生成思维导图，`mindmap.puml` 不包含「需求理解 / P0 / P1 / P2 / 风险与待确认」节点，也不展示内部用例 ID
- [ ] 有一段「本次最该测什么」的风险判断
- [ ] 图/表未保真读取时已标覆盖风险
- [ ] 已注明 已读/未读/未命中 qa-knowledge-base；`history-hits.md` 已记录检索词组、保留/丢弃理由、深读 `notes/*.md` 情况和编入位置
- [ ] Top 1-3 个高风险历史命中若 notes 信息不足，已回看 raw/原料或原飞书链接，或已把不可达/仍不足写入「风险与待确认」
- [ ] 保留的历史线索都落到了用例/风险/待确认，且覆盖自检表有「历史回归」维度
- [ ] 每条用例 ID 都已进入覆盖自检表；APP 常驻维度都有 `已覆盖 / N/A / 待确认` 状态
- [ ] 已在交付目录落盘 `testcases.md` / `history-hits.md`，并用 `scripts/validate_output.py` 校验通过；若生成思维导图，也已校验 `mindmap.puml`
- [ ] 除非用户明确要求只本地输出，已按 `references/lark-output.md` 发布到用户指定/默认飞书目录，并在最终回复给出飞书文档链接；发布失败时只报告阻塞，不标记完成
