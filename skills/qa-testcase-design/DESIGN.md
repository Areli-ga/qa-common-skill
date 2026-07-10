# qa-testcase-design 设计文档

> 一个格式无关的「测试用例设计引擎」skill：把产品需求 + QA 覆盖清单，编译成全面、按风险排序、可执行的结构化用例中间产物；可同步产出 PlantUML `.puml` 思维导图。

日期：2026-07-01（2026-07-04 更新：7 块骨架重构 + 代码风险库按端拆分 + 飞书 Drive 发布）
状态：**v2 已实现**（四支柱：逐维防漏 + 风险立场 + 测试设计方法 + 只读检索 qa-knowledge-base 历史编译）。正文按业务功能组织、P0/P1/P2 降为用例 ID 属性；思维导图经 md_to_mindmap.py 确定性生成；代码扫描风险库按端范围按需读取。
本文件是 skill 的设计存档，与 `SKILL.md` / `references/case-schema.md` / `scripts/validate_output.py` 的实现保持一致。

---

## 0. 核心边界

- 本 skill 与 `qa-knowledge-base` 是两个独立系统；本项目**不修改** qa-knowledge-base 知识库本体。
- `qa-testcase-design` 把「本次需求 + 覆盖清单 + qa-knowledge-base 历史知识」编译成用例中间产物；**v2 已接 qa-knowledge-base（只读检索）**。
- 历史知识只读契约见 `references/history-kb-contract.md`：只读检索，不 ingest、不回写、不迁移 qa-knowledge-base。
- 核心产物是格式无关的中间产物；飞书思维导图通过 PlantUML `.puml` 输出，Excel / XMind 留给后续 formatter。

---

## 1. 方法论来源

把「AI 学习之路 · 实战篇」（06–10）套用到"写测试用例"：

- **06 编译 > 检索**：高质量用例是把本次需求 + 覆盖清单（v2 起 + 历史需求）编译在一起，不是把 PRD 拆更细。
- **07 产品思维 / MVP**：从真实痛点「遗漏」出发，砍到最小闭环，明确"不做什么"，拒绝"全面完美"。
- **08 架构思维 · 进存取**：先定义"取"（中间产物）→ 反推"存"（规则/模板）→ 定"进"（需求）。功能做减法、架构留口子（qa-knowledge-base 编译层先留位）。
- **09 技术思维**：优先复用现成（覆盖清单、读图内核、PlantUML mindmap）；`read_doc.py` 零第三方依赖。
- **10 Agentic Coding**：语义活（读懂/判断风险/设计用例）交给 AI；机械活（下载图/缩放/最终格式）交给脚本与下游。

---

## 2. 一页纸 MVP

| 格子 | 内容 |
|---|---|
| 用户 | 我自己（QA 软件测试工程师） |
| 问题 | AI 从需求文档生成的用例不全面、常遗漏跨端/配置/异常场景与图上的 UI/演出细节，也不告诉我这次最该测什么 |
| 输入 | 产品需求文档（飞书链接 / 粘贴文本）+ 可选：本次改动点、影响端范围、提测说明 |
| 处理 | ①保真读取（含图片）→ ②复述需求理解 + 待确认 → ③**只读检索 qa-knowledge-base 编译历史**（步3.5）→ ④判断本次高风险 → ⑤逐维过覆盖清单（含历史回归维）→ ⑥输出结构化用例 + 覆盖自检表 → ⑦本地校验通过后发布到飞书 docx |
| 输出 | 独立交付目录内的 `testcases.md` 完整用例正文 + v2 历史检索证据 `history-hits.md` + 可选 `mindmap.puml`（业务功能思维导图，默认 full / `--compact`）；交付前用 `validate_output.py` 校验；默认新建飞书 docx 发布到默认 Drive 文件夹（见 `references/lark-output.md`）；Excel / XMind 留给后续 formatter |
| 不做什么 | 不做需求录入（qa-knowledge-base）、不改 qa-knowledge-base、不覆盖历史飞书文档、不做用例管理/执行报告（opentest）、不做自动化脚本、不追求"全面完美" |

---

## 3. 在现有 QA 生态中的定位

| 能力 | 角色 | 边界 |
|---|---|---|
| `qa-knowledge-base` | 需求知识库：ingest + 检索历史需求逻辑/回归线索 | 只读调用；本 skill 不改它 |
| **`qa-testcase-design`（本设计）** | 用例设计引擎：需求 + 覆盖清单 → 结构化用例中间产物 | 只产格式无关中间产物 |
| 飞书思维导图输出（已闭环） | 本 skill 把用例渲成 PlantUML `.puml` 文件，用户粘进飞书画板，渲染成接近原生样式的思维导图（见 `references/mindmap-plantuml.md`） | Excel/XMind 等其他格式仍交后续 |
| `opentest:*` / `git-branch-diff-qa-doc` | 用例管理/报告 / 分支 diff QA 文档 | 不在本 skill 触发范围（description 已排除） |

---

## 4. 架构（进存取）

```text
产品需求文档(飞书/文本)
   │  scripts/read_doc.py: 正文+表格+下载全部图片(sips 缩放) → Claude 逐张读图
   ▼
[qa-testcase-design 引擎]
   │        ▲
   │        └── 按 references/history-kb-contract.md 只读检索 qa-knowledge-base：最小检索词组 + 深读 notes + history-hits.md
   ▼
结构化用例中间产物(7 块骨架 + 覆盖自检表 + history-hits.md)
   │
   ├── scripts/validate_output.py → 校验失败则回修文件
   ├── PlantUML .puml 文件 → 飞书画板 → 接近原生样式的思维导图（已闭环）
   └── future formatter → Excel / XMind
```

- **进**：飞书链接（`read_doc.py` 读，含图）或粘贴文本 + 可选改动点/端范围。
- **存**：skill 自身只存规则与模板——`SKILL.md`（工作流/边界）、`references/case-schema.md`（7 块结构/优先级/自检表/映射）、`references/coverage-dimensions.md`（高层覆盖清单）、`references/code-risk-*.md`（后端/Unity/原生/H5 代码扫描风险库，按端范围按需读取）。
- **取**：独立交付目录中的格式无关中间产物 + 覆盖自检表 + 历史检索证据；校验失败时先修文件，再交下游出格式。

---

## 5. 工作流（v2 · 8 步，见 SKILL.md）

1. **进** — 收需求 + 可选改动点/端范围。
2. **保真读取** — `scripts/read_doc.py`（blocks + 抽取 `tables.md/json` + 下载全部图 + sips 缩放）；Claude 逐张读图（≤6 全读；>6 优先关键图并登记未读）。图没下全默认中止，接受部分读取才加 `--allow-partial`。
3. **对齐** — 复述需求理解 + 列待确认，不编造。**务必读 `tables.md`**（分支表→状态迁移、数值表→边界值、多条件表→判定表，是用例金矿）。**仅当待确认影响 P0 主链路 / 接口·配置·AB 发版口径 / 测试环境前置**时停下问用户；普通缺口写入「风险与待确认」块并继续。
3.5. **历史编译** — 按 `references/history-kb-contract.md` 只读检索 qa-knowledge-base：按最小检索词组召回，记录 `history-hits.md`，对保留/待确认命中深读 notes，把历史需求逻辑/旧边界/相邻入口/回归线索编入用例；不把 qa-knowledge-base 当事实源覆盖 PRD，冲突进入待确认。
4. **立场** — 判断"本次最该测什么"+ 理由，驱动用例优先级（`priority=P0/P1/P2`）与 showcase 排序，不一碗水端平。
5. **防漏** — 读覆盖清单逐维过闸，每维 已覆盖 / N/A / 待确认，禁止默默跳过；按端范围读对应 `references/code-risk-*.md`（涉及的端才读、不涉及标 N/A）补代码级测试点。
6. **出例** — 先按 `references/test-design-methods.md` 的「特征→方法」决策表给每个功能点/维度挑测试设计方法（等价类/边界值/判定表/状态迁移/场景法/正交/错误推测），再按 7 块骨架输出：正文用例按业务功能/需求类目/状态机组织，P0/P1/P2 只作为用例 ID 属性和执行优先级、不做一级目录；方法只在覆盖自检表说明里短标；缺口汇总进「风险与待确认」块。
7. **自检交付** — 出覆盖自检表；按 `references/output-files.md` 建交付目录，用例正文写入 `testcases.md`，历史检索证据写入 `history-hits.md`，并用 `scripts/validate_output.py` 校验。用户需要思维导图时另产 `mindmap.puml`，再带 mindmap 参数复验。PlantUML 默认完整评审图：按业务/功能维度 + APP 常驻维度组织，并挂前置/操作步骤/预期结果；只要主结构时用 `--compact`。落成文件、提示先清空编辑框再粘一次。默认发布到飞书 Drive 文件夹；提示执行后新缺陷建议回流 qa-knowledge-base（本 skill 不自动做）。

---

## 6. 质量支柱

- **v2 四支柱**：①**逐维覆盖闸门**（覆盖清单必逐项过，不默默跳过）②**风险立场**（先答"这次最该测什么"，驱动用例优先级 `priority=P0/P1/P2` 与 showcase；优先级只是 ID 属性，不做正文一级目录）③**测试设计方法**（每个功能点/维度按 `references/test-design-methods.md` 的「特征→方法」决策表挂等价类/边界值/判定表/状态迁移/场景法/正交/错误推测，把"测哪些面"升级为"面 × 方法"）④**历史编译**（出例前只读检索 qa-knowledge-base，按最小检索词组召回、深读 notes、沉淀 `history-hits.md`，把历史逻辑/旧边界/相邻入口/回归线索编入；基于已沉淀需求知识现算，不是历史 bug 库）。
- **代码风险库（2026-07 增强）**：从后端/Unity/原生/H5 代码扫描沉淀的端侧风险，拆为 `references/code-risk-*.md`，按端范围**按需读取**，把产品特有的代码级失败模式编入用例；不涉及的端标 N/A，不全量灌入。

---

## 7. 用例中间产物结构（见 case-schema.md）

- **7 块骨架**：需求理解 / 风险判断 / **showcase（提测准入）** / **用例设计（按业务功能 / 需求类目组织）** / **APP 常驻维度补充** / 风险与待确认 / 覆盖自检表。P0/P1/P2 不作为正文一级目录，只体现在用例 ID（`priority=P0/P1/P2`）、覆盖自检表和执行优先级。
- **稳定 ID 格式**（无「来源/待确认」字段）：
  ```
  [P0-01/P1-01/P2-01] 用例标题（依赖未确认信息时加「（待确认）」）｜前置：...｜步骤：...｜期望：...
  ```
  ID 在 Markdown 正文、`mindmap.puml`、覆盖自检表、`history-hits.md` 中保持一致；缺口明细统一进「风险与待确认」块；依赖未确认信息的用例标题后加「（待确认）」。
- **优先级**：P0 不通过不能发版；P1 重要路径；P2 边界/兼容。
- **覆盖自检表**：维度 | 状态（已覆盖/N/A/待确认）| 对应用例 | 说明。禁"已检查""正常验证"空泛结论。
- **中间产物 → 思维导图映射**：`md_to_mindmap.py` 读第 4 块「用例设计」的 `###/####…` 业务功能标题层级 + 第 5 块「APP 常驻维度补充」，把用例按业务功能/常驻维度组织（showcase 置顶），隐藏内部 ID；需求理解 / 风险判断 / 风险与待确认 / 覆盖自检表 / history-hits 不进图。规则见 `mindmap-plantuml.md`。

---

## 8. read_doc.py（只读读图脚本）

- 与 qa-knowledge-base `fetch.py` 同一套读法（blocks 接口 + 下载图 + `sips` 缩放），但**只读**：输出临时目录、不写 qa-knowledge-base、零第三方依赖。
- 支持 wiki / docx 链接与裸 token；凭证走环境变量或公司 config（VPN）。
- 产出 `content.txt / blocks.json / tables.md / tables.json / meta.json / images/`；超大图（>1900px）生成 `.read` 缩放副本供读图。
- **不静默截断**：图没下全默认中止（`--allow-partial` 才继续）；未读/失败图登记进 meta 与终端"读取风险"。

---

## 9. 文件结构与复用

```text
qa-testcase-design/
  SKILL.md
  DESIGN.md                 # 本文件
  PLAN-archived.md          # 初版实施计划,仅存档
  references/
    case-schema.md          # 7 块结构 / 优先级 / 自检表 / 思维导图映射边界
    coverage-dimensions.md  # 高层覆盖维度清单 + 代码风险库索引
    code-risk-backend.md    # 后端代码风险库(按需读取)
    code-risk-unity.md      # Unity 代码风险库(按需读取)
    code-risk-native.md     # 原生 Android/iOS 代码风险库(按需读取)
    code-risk-h5.md         # H5/WebView 代码风险库(按需读取)
    example-testcases.md    # 标准 7 块正文样例(可过 validate_output.py)
    example-mindmap-rich.puml # 富 PlantUML 层级样例
    example-output.md       # 兼容索引(指向 example-testcases.md,防旧引用断链)
    history-kb-contract.md  # 历史知识只读契约(只读 qa-knowledge-base,不写入;含 history-hits.md 证据链)
    output-files.md         # 交付目录 / 必产文件 / validate_output.py 校验规则
    test-design-methods.md  # 测试设计方法 + 特征→方法决策表
    mindmap-plantuml.md     # 飞书思维导图输出(业务功能一级,隐藏ID,含"必须落文件"铁律)
    lark-output.md          # 飞书发布规则(默认发布/默认 Drive 文件夹/新建不覆盖/失败处理)
  scripts/
    read_doc.py             # 只读飞书(正文+表+图)
    md_to_mindmap.py        # testcases.md → 业务功能 .puml(读「用例设计」块标题层级,隐藏ID,默认full/--compact)
    validate_output.py      # 校验 testcases/history-hits/mindmap 的结构与 ID 引用
    publish_to_lark_doc.py  # 默认:校验通过后新建飞书 docx 发布;凭证与 read_doc.py 同源(self-contained,不依赖 gateway)
```

**复用（不重造）**：
- 覆盖清单：`references/coverage-dimensions.md`（本 skill 自持，不依赖旧思维导图 skill）。
- 读图内核：对齐 qa-knowledge-base `fetch.py`。
- 历史知识（v2）：按 `references/history-kb-contract.md` 只读调用 `qa-knowledge-base` skill 与 qa-knowledge-base 知识库本体；按最小检索词组召回、深读 notes，并输出 `history-hits.md`。
- 出飞书思维导图：本 skill 生成 PlantUML `.puml` 文件，用户粘进飞书画板（不 API 写飞书）。默认完整评审图，按需 `--compact`。**铁律：必须落成文件让用户从文件复制 + 粘前先清空编辑框**——聊天里长行会被折行搞坏、编辑框残留会重复，都会导致飞书解析报错（实测踩坑）。Excel/XMind 交后续。
- 交付校验：按 `references/output-files.md` 使用 `scripts/validate_output.py` 校验 `testcases.md`、`history-hits.md` 和可选 `mindmap.puml`；校验失败不交付，先回修。

**运行时**：`~/.claude/skills/` 与 `~/.codex/skills/` 实测同步（在一处新建，另一处即时可见），**无需手动镜像**。

---

## 10. 版本边界（当前 v2）

| 能力 | 状态 |
|---|---|
| 历史编译（只读检索 qa-knowledge-base） | ✅ **v2 已启用**：工作流步 3.5，按 `history-kb-contract.md` 只读检索、深读 notes、沉淀 `history-hits.md`，再编入用例/风险/待确认 |
| 交付校验 | ✅ **v2 已启用**：按 `output-files.md` 落盘，`validate_output.py` 校验结构、ID 引用和 mindmap 附录污染 |
| 飞书发布（新建 docx 到 Drive 文件夹） | ✅ **默认做**：本地校验通过后新建 docx 发布到默认 Drive 文件夹（新建不覆盖历史）；正文/表格/思维导图代码块均已端到端真跑验证；`publish_to_lark_doc.py` 凭证与 `read_doc.py` 同源（self-contained：环境变量或 config 服务 → tenant_access_token → urllib 直调，**不依赖 gateway/CF 登录**） |
| 代码扫描风险库（按端按需读取） | ✅ **2026-07 增强**：后端/Unity/原生已扫码沉淀 `code-risk-*.md`；H5 库暂为通用面、具体规律待补 |
| 反馈回流（新缺陷/回归点 ingest 回 qa-knowledge-base） | ❌ 仍不自动做，仅末尾提示（避免污染 qa-knowledge-base） |
| 多格式输出（Excel/XMind） | 中间产物已格式无关；思维导图已闭环（PlantUML），Excel/XMind 交后续 formatter |

历史编译不改叶子/骨架格式：命中只作设计素材，编译进既有 7 块，不新增块、不覆盖 PRD、冲突进「风险与待确认」；检索词组、深读 notes 结果、保留/丢弃理由与落点进入 `history-hits.md`。

---

## 11. 验证记录（2026-07-01）

- **对象**：跟读挑战课 PRD（飞书 wiki，v1.33.0，语音识别 Boss 对战挑战课）。
- **读取**：`read_doc.py` 读到正文 4241 字 + 6 表 + **14/14 图全下载**，`complete=True`。
- **读图价值**：挖出纯文本漏掉的 UI/演出测试点（选择屏布局、对战 HUD 双血条/combo 计数器、结局页构图、格斗服造型基准）。
- **关键发现**：图06 词卡显示单词文本，与 PRD 正文"出题仅显示图片"矛盾 → 纯文本读不出、读图才逮到的高价值待确认点。
- **结论**：保真读取、风险判断、覆盖自检与思维导图输出链路已走通；v2 历史证据链后续按 `history-hits.md` 规则验收。

## 11.1 更新记录（2026-07-04）

- **发布链路端到端**：`publish_to_lark_doc.py` 完整链路（建 docx + 写正文 blocks + 写思维导图代码块）用现成交付真跑通过并读回确认。修复三处发布保真：`- ` 列表 → 飞书原生 bullet、Markdown 表格 → 飞书原生表格（descendant 嵌套接口）、PlantUML/代码块聚合为**单个** code block（无损硬切多 text_run，保护 PlantUML 换行）。
- **7 块骨架重构**：正文从「按 P0/P1/P2 优先级分块」改为「按业务功能/需求类目组织」的 7 块骨架，优先级降为用例 ID 属性；`validate_output.py` / `md_to_mindmap.py` 同步适配，并保留旧骨架向后兼容（NEW/OLD 双检测）。
- **代码风险库接入**：只读扫描后端 / Unity / 原生三端代码，沉淀端侧风险为 `references/code-risk-*.md`，按端范围按需读取；`coverage-dimensions.md` 只留高层清单 + 风险库索引，不再全量堆叠。H5 库为通用面、具体规律待补。

## 11.2 更新记录（2026-07-05）

- **发布凭证自包含化**：`publish_to_lark_doc.py` 从依赖 giggle-common gateway（CF Access token，会过期需登录）改为**与 `read_doc.py` 同源的 self-contained 凭证**（环境变量 / config 服务 → `tenant_access_token` → urllib 直调）——读写统一一套凭证、零第三方依赖、**不再需要 gateway 登录**；并把 gateway 时代「响应非 JSON 直接崩栈」修为友好 `code=-1` 报错。已用跟读挑战课 v2 交付**端到端真发验证成功**。
- **域名事实**：config 服务 `LARK_DOMAIN=open.feishu.cn`（国内站）与目标 `larksuite.com`（国际站）是**同一租户的两个接入域名、数据互通**——feishu.cn 凭证建的 docx 通过 larksuite 链接可访问。
- **代码风险库补 A 类具体规律**：`code-risk-backend/unity/native.md` 在通用面骨架下补「本产品已知规律（A 类）」；B 类 bug / 拼写错等具体缺陷线索另出 `docs/giggle-潜在缺陷清单-20260704.md`（不进风险库，避免过时）。
- **case-schema 补规则**：用例标题禁带来源 / 归属标注（历史回归 / 风险库 / 端差异），避免污染思维导图触发 validate。
- **发布呈现裁剪（几经反复，最终恢复裁剪）**：曾把飞书文档定位「评审 + 看图」裁剪 showcase / 用例设计 / APP 常驻三块，7-06 一度改为完整渲染；**最终（2026-07-07 起）确认恢复裁剪这三块、由思维导图承载用例，完整 7 块正文以本地 `testcases.md` 为准**，呈现规则以 `references/lark-output.md` 最新版为准。

## 11.3 更新记录（2026-07-06）

- **发布失败友好化**：`publish_to_lark_doc.py` 全链路分段捕获（resolve_wiki_parent / create_docx / append_blocks / set_permission），失败输出 JSON（status/stage/code/msg/document_id）并 exit 1，不再裸 traceback；建档后失败会给出**半成品文档 id** 提示可手动删除。已用假 folder token 真跑验证（code=1770039 → 友好报错）。
- **read_doc 图片占位编号**：`content.txt` 里裸 `image.png` 占位按出现次序替换为「【图NN｜images/img-NN.ext】」，正文位置与落盘图片精确对应；占位行数与图片块数不一致时不猜、原样保留并提示。
- **凭证内核抽公共模块**：`load_credentials` / `http` / `tenant_token` 抽到 `scripts/lark_common.py`，read_doc 与 publish 共用一份,根治"两份拷贝漂移"(读能用写坏了的老病根)。
- **未解析块告警**：read_doc 对 电子表格/多维表格/同步块/附件/iframe 等正文·表格·图片之外的容器块统计并在「读取风险」提示,不静默跳过。
- **思维导图交付路径**：实测发布后飞书文档里的 PlantUML 代码块可直接复制进画板、完美兼容,首选从飞书文档复制(省开本地文件);`case-schema` 补第 4/5 块「后端」归属判定。
- **上线前护栏收紧**：`validate_output.py` 默认禁止旧 P0/P1/P2 一级目录骨架（仅 `--allow-old-schema` 兼容旧归档）；`publish_to_lark_doc.py` 默认发布前强制校验交付结构后新建 docx（**注：本条“完整渲染、不再裁剪”是 7-06 当时口径；此后按用户确认最终改回裁剪 showcase / 用例设计 / APP 常驻三块、由思维导图承载，当前发布态以 `references/lark-output.md` 为准**）。
- **飞书表格样式固化**：从用户手动调整后的 docx 读取到三类 QA 表格列宽并固化到发布脚本：风险表 4 列版 `[52,412,259,100]`（旧 3 列版兜底 `[60,500,263]`）、覆盖表（完整 ID 版）`[107,80,180,456]`、历史命中表 `[100,215,63,347,100]`；history 表后说明段发布时转无序列表。

## 11.4 更新记录（2026-07-08）

- **背景**：用「跟读挑战课」PRD 真跑全流程（Linux 沙盒、单进程时长受限、DNS 抖动频发）暴露两个 P0 健壮性缺口，均已修复并真跑/离线双重验证。
- **网络重试统一下沉 `lark_common`**：`http()` 新增 `retries=3` 网络层重试（URLError/OSError 指数退避；HTTP 4xx/5xx 不在此重试）；config 拉取同样重试 3 次。此前仅图片下载有重试，token/raw_content/blocks/发布任一环节被 DNS 瞬断打断即整体失败——实测确认。所有调用方自动受益，无需改动。
- **read_doc.py 断点续跑 `--resume`**：中断后同一输出目录加 `--resume` 重跑——复用已落盘 `content.txt`/`blocks.json`、跳过 `images/` 已完成图片只补缺；图片先写 `.part` 再原子改名，杜绝半截文件被误当完成；content 已含【图NN】标注时跳过重复标注。默认（不带 `--resume`）行为与从前一致。e2e 验证：14 图文档被强杀 6 次后续跑至 `complete=True`。
- **publish_to_lark_doc.py 断点续传 `--resume`/`--fresh`**：每次 append 成功即把进度写交付目录 `publish_state.json`（成功结束自动删除）；中途失败重跑加 `--resume` 复用已建文档从断点继续，不重复建档、不产生重复块；本地交付块数或目标变化则拒绝续传（`resume_check`）。存在未完成状态而未带 `--resume` 时报 `resume_guard` 拒绝直接重发（防重复半成品），`--fresh` 显式放弃。`append_renderables` 重构为索引推进式（批次边界与原实现一致：表格单发、children 每批 40）。离线状态机测试验证：中断→护栏拦截→续传完成→状态清除→交付变化拒绝续传。

## 11.5 更新记录（2026-07-08 · P1 健壮性）

- **缩放器跨平台三级降级**：`downscale_for_read` 从 sips 硬依赖（macOS 专属，Linux/CI 静默退化 dims=0x0）改为 sips → PIL（可选依赖，装了就用）→ 纯 Python 图片头解析（PNG/JPEG/GIF/WebP，新增 `_image_dims`）。无缩放器且遇超大图时一次性明确告警，不再静默。实测：PIL 路径正确生成 1900px `.read` 副本；无 PIL 时头解析取真实尺寸。
- **图片占位标注可刷新**：新增 `refresh_annotated_placeholders`——content.txt 已标注过（如 `--allow-partial` 部分失败）后补图续跑，按本次下载结果刷新【图NN｜...】行，修正过期的「下载失败,未落盘」；幂等，无变化不写盘。根治"一经标注无法更新"。
- **validate_history 判定词前缀匹配**：`保留(Top1 高风险)`/`待确认(弱)` 这类带说明后缀的判定此前被集合精确匹配整体跳过落点强校验（漏检"保留却没编入位置"）；改为 `startswith` 前缀匹配。负用例验证已能查出。
- **交付目录表述平台无关**：SKILL.md / output-files.md / PIPELINE.md 中 `/private/tmp` 改为「系统临时目录（macOS /private/tmp、Linux /tmp）」，勿硬编码 macOS 路径。

## 11.6 更新记录（2026-07-08 · 发布呈现修复）

- **风险与待确认表「影响」列发布态改写为维度**：用户实评发布文档发现影响列仍显示 P0-xx 编号——正文用例块已裁剪、导图隐藏 ID，编号在飞书文档内是死引用（与覆盖表 7-06 已修的同类问题，当时漏了风险表）。`publish_to_lark_doc.py` 新增 `build_case_dimension_map`（从覆盖自检表建 ID→维度映射）+ `rewrite_risk_impact_row`（影响列 ID 列表改写为去重后的维度名），接入 `split_testcases_for_publish`；本地 `testcases.md` 不受影响，完整 ID 仍以本地为准。真实交付离线验证：12 行 Q 项影响列全部正确映射。

## 11.7 更新记录（2026-07-08 · 出例质量根治：先树后例 + 原子用例）

- **问题**（用户实评对比旧版富导图）：流程充足但导图/用例粒度低——根因是结构在出例时被"单行用例格式"压平（多个数值/分支打包进一行期望）、转换器只能搬运结构不能创造结构、质量门全是格式门没有粒度门、每组无 #### 时转换器还插"功能点"占位层。
- **契约层**：`authoring-core.md` §C 第 4 块改为**先树后例**硬规则——先用 `###/####/#####` 多级标题落分解树（数值逐项、分支逐行、结局逐个成节点），用例只挂叶层且为**原子断言**（一例一个可判定结果）；SKILL.md 步 6 与质量门槛同步。
- **闸门层**：`validate_output.py` 新增 ①分组细分闸（### 组下 >4 条用例且无 #### → FAIL）②原子性闸（期望 >140 字 FAIL、>90 字 WARN）③`--tables` 数值对账（tables.md 数值短语未落入用例 → WARN 清单）；新增 WARN 机制不影响退出码。
- **转换器层**：`md_to_mindmap.py` 删除「功能点」占位兜底（推断不出中间层就直挂分类节点）；多级 #### 本就支持，无需改动。
- **验证**（同一 PRD 重出对比）：旧版 37 例/177 节点/5 层/3 组平铺被新闸 FAIL + 数值对账抓出 3 个漏测数值（2伤害/3档音效/血量=3）；新版 **74 例原子断言/344 节点/6 层**，校验+数值对账全绿，占位层归零，并新挖出 Q13（1词课对手血量=0 的最小词数边界）。旧样例 example-testcases.md 在新闸下仍 PASS。
- **首次真跑树形体检又修 3 个转换器缺陷**：①标题序号剥离正则裸剥 `^\d+`，把「3★ 大获全胜」吃成「★」——改为数字后必须跟 `.`/`、` 才剥；②维度归类关键词扫描顺序劫持——「多语言兼容」被「边界/兼容」的关键词"兼容"抢走导致多语言分类清空——改为先全量精确匹配再关键词扫描；③清空 SUBMODULE_RULES 关键词推断层（内含上代需求领域词"战斗数值/反馈分支/结算"，属跨需求污染，且"命中才有层"导致树深不一致）——结构一律来自 testcases.md 分解树。validate_mindmap 新增占位节点闸（「功能点」「其他业务场景」出现即 FAIL）防回归。

---

## 12. 明确不在范围

- 不修改 / 迁移 / 扩展 qa-knowledge-base；不自动回流数据到 qa-knowledge-base。
- 飞书发布只新建交付 docx，不覆盖历史文档、不修改原 PRD、不承诺 API 直接生成飞书画板原生思维导图；不做用例管理、执行报告、缺陷跟踪；不做自动化脚本生成。
- 不把 opentest / git-branch-diff-qa-doc 的职责纳入本 skill。
- 不做非 Giggle 场景的通用测试平台。
