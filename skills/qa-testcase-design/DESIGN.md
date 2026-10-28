# qa-testcase-design 设计文档

> 一个格式无关的「测试用例设计引擎」skill：把产品需求 + QA 覆盖清单，编译成全面、按风险排序、可执行的结构化用例中间产物；可同步产出 PlantUML `.puml` 思维导图。

日期：2026-07-01（2026-07-04 更新：7 块骨架重构 + 代码风险库按端拆分 + 飞书 Drive 发布）
状态：**v2 已实现**（四支柱：逐维防漏 + 风险立场 + 测试设计方法 + 只读检索 qa-knowledge-base 历史编译）。正文按业务功能组织、P0/P1/P2 降为用例 ID 属性；思维导图经 md_to_mindmap.py 确定性生成；代码扫描风险库按端范围按需读取。
本文件是 skill 的设计存档（为什么这样设计 + 更新记录）。**当前行为以 `SKILL.md`（流程）+ `references/authoring-core.md`（唯一规则源）+ `scripts/validate_output.py`（闸门）为准**；§11 更新记录里提到的旧文件名/旧步号是当时口径，不代表现状。

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
- **存**：skill 自身只存规则与模板——`SKILL.md`（工作流/边界）、`references/authoring-core.md`（覆盖维度 + 测试设计方法 + 7 块结构/优先级/自检表，唯一规则源）、`references/code-risk-*.md`（后端/Unity/原生/H5 代码扫描风险库，按端范围按需读取）。
- **取**：独立交付目录中的格式无关中间产物 + 覆盖自检表 + 历史检索证据；校验失败时先修文件，再交下游出格式。

---

## 5. 工作流（1-8 步，详见 SKILL.md）

1. **进** — 收需求，建交付目录。
2. **保真读取** — `read_doc.py`：正文 + `tables.md/json` + 全部图片 + 缩放副本；图没下全默认中止。
3. **并行装载** — 读图代理（→ `images-notes.md`）与历史代理（→ `history-hits.md`）同时派出，只读。
4. **对齐** — 主线复述需求 + 待确认，务必读 `tables.md`；仅影响 P0/发版口径/环境前置时才停下问。
5. **合流验收** — 图占位全覆盖、P0 关键图主线亲读、检索词组核对；不过则主线串行补做。
6. **立场与防漏** — 读一次 `authoring-core.md`：风险判断驱动 P0 与 showcase；逐维过闸；按端读风险库。
7. **出例** — 先树后例、原子用例、方法先选后写；输出 7 块骨架 + 覆盖自检表。
8. **校验与发布** — `md_to_mindmap.py` → `validate_output.py --dir` → `publish_to_lark_doc.py`；拿到飞书链接才算完成。

## 6. 质量支柱

- **v2 四支柱**：①**逐维覆盖闸门**（覆盖清单必逐项过，不默默跳过）②**风险立场**（先答"这次最该测什么"，驱动用例优先级 `priority=P0/P1/P2` 与 showcase；优先级只是 ID 属性，不做正文一级目录）③**测试设计方法**（每个功能点/维度按 `references/authoring-core.md` §B 的「特征→方法」决策表挂等价类/边界值/判定表/状态迁移/场景法/正交/错误推测，把"测哪些面"升级为"面 × 方法"）④**历史编译**（出例前只读检索 qa-knowledge-base，按最小检索词组召回、深读 notes、沉淀 `history-hits.md`，把历史逻辑/旧边界/相邻入口/回归线索编入；基于已沉淀需求知识现算，不是历史 bug 库）。
- **代码风险库（2026-07 增强）**：从后端/Unity/原生/H5 代码扫描沉淀的端侧风险，拆为 `references/code-risk-*.md`，按端范围**按需读取**，把产品特有的代码级失败模式编入用例；不涉及的端标 N/A，不全量灌入。

---

## 7. 用例中间产物结构（规则见 authoring-core.md §C）

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
  SKILL.md                  # 1-8 步总控流程 + 边界 + 完成门槛
  DESIGN.md                 # 本文件
  PIPELINE.md               # 团队版链路说明
  PLAN-archived.md          # 初版实施计划,仅存档
  references/
    authoring-core.md       # 唯一规则源:覆盖维度 + 测试设计方法 + 7 块结构/优先级/自检表
    code-risk-*.md          # 后端/Unity/原生/H5 代码风险库(按端命中才读)
    history-kb-contract.md  # qa-knowledge-base 只读契约(四类检索词/深读/证据)
    output-files.md         # 交付目录结构 / 校验命令 / 失败修法
    lark-output.md          # 飞书发布规则(默认目录/呈现裁剪/续传/失败处理)
    mindmap-plantuml.md     # 导图结构来源 / 校验拦截 / 粘贴铁律
    example-testcases.md    # 标准 7 块样例(先树后例 + 原子用例,可过 validate)
    example-mindmap-rich.puml # 手写 PlantUML 块富层级样例
    coverage-dimensions.md / case-schema.md / test-design-methods.md / example-output.md  # 存根(已并入或索引)
  scripts/
    read_doc.py             # 只读飞书(正文+表+图),--resume/--quiet
    md_to_mindmap.py        # testcases.md → .puml(结构完全来自分解树)
    validate_output.py      # 交付硬校验,--dir 一次校验整个交付目录
    publish_to_lark_doc.py  # 校验通过后新建飞书 docx 发布,--resume/--fresh
    lark_common.py          # 凭证/HTTP 共享库
    kb.py                   # 定位 qa-knowledge-base 并转发 search.py
```

**复用（不重造）**：
- 覆盖清单：`references/authoring-core.md` §A（本 skill 自持，不依赖旧思维导图 skill）。
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

## 11.8 更新记录（2026-10-28 · 规则收敛与闸门补强）

- **背景**：两个多月迭代后规则文本自相矛盾（authoring-core 声明「冲突以原文件为准」而原文件缺 7-08 的原子规则；样例违反原子规则；导图必产与否、飞书内容、查历史时机多处说法不一），模型按文本执行导致行为不稳。改前全量备份在 `Workspace/qa-skill-backups/qa-testcase-design-20261028-before-opt/`。
- **单一规则源**：`authoring-core.md` 成为唯一权威，吸收原三件缺失内容（拆解检查单「要问的问题」、低质量反例、复杂交互拆解表、自检表状态判定、后端摆放）；`coverage-dimensions.md` / `case-schema.md` / `test-design-methods.md` 降为存根。
- **SKILL.md 精简**：18.4KB → 7.4KB，工作流统一为 1-8 整数步，按步骤给出「读什么」对照表；踩坑经过迁入本文件。
- **样例原子化**：`example-testcases.md` 30 → 44 例，边界三点各一例、多断言全部拆开，首行改为需求名。
- **文档对齐**：`mindmap-plantuml.md` 重写为「结构完全来自分解树」；`lark-output.md` 飞书内容改为与呈现裁剪一致的 7 段；`history-kb-contract.md` 时机统一为步 3 并行、检索词组加类型前缀；`output-files.md` 交付目录统一 `/tmp/…`（`tempfile.gettempdir()` 在 macOS 返回 `/var/folders`，原表述错误）、导图改为默认必产。
- **validate_output.py**：新增 `--dir` 整目录校验（发布脚本复用同一函数）、分号原子闸、四类检索词闸、读图覆盖闸、风险表未知 ID 闸、P0 占比与首行标题 WARN；数值对账去掉领域词并只对账用例与风险表；ID 支持三位；常驻维度改精确匹配；删除旧 P0/P1/P2 骨架兼容。
- **脚本清理**：`read_doc.py --quiet` 不回显全文；`md_to_mindmap.py` 删旧骨架分支、业务维度不再被关键词劫持、showcase 不受覆盖表行序影响；`publish_to_lark_doc.py` 续传增加内容指纹校验、交付清单含 `images-notes.md`、删除死代码。
- **验证**：样例 PASS；构造负用例逐项命中新闸；导图 211 节点 6 层无占位；publish `--dry-run` 通过；离线模拟 append 中断 → 续传成功、发布内容变化 → 拒绝续传。

## 11.9 更新记录（2026-10-28 · 触发收敛）

- **description 改写**：去掉尾句流程摘要「产出结构化用例并发布为飞书文档」（description 只写触发条件，避免模型照描述执行而不读正文）；「PlantUML 思维导图」改为「用例思维导图」；补三条分流：只录入/检索历史需求 → `qa-knowledge-base`，OpenTest 变更流程 → `opentest-*`，按 Git 分支差异出 QA 文档 → `git-branch-diff-qa-doc`。
- **移除抢触发的旧 skill**：已弃用的 `writing-lark-test-mindmaps`（description 与本 skill 高度重叠）已由用户手动移出 `~/.codex/skills`；本 skill 运行时不依赖它（仅 `PLAN-archived.md` 历史提及）。

## 11.10 更新记录（2026-10-28 · 质量闸补强）

- **背景**：现有闸门只查「写得对不对」，查不出「测得全不全」——PRD 有 3 条规则只写了 2 条的用例照样 PASS；另有 3 个漏洞可被构造输入绕过；飞书文档裁掉用例正文后，导图里看不出优先级。
- **需求追溯闸（新增）**：第 1 块「需求理解」末尾加 `### 业务规则追溯` 表（`编号 | 规则 | 来源 | 落点`）。SKILL 步 4 拆规则写表、步 5 补图里的规则、步 7 回填落点。validate 检查：表存在且非空、编号 `R\d{2,3}` 唯一、规则与来源非空、落点至少一个已存在的用例 ID 或第 6 块已定义的 Q 编号、引用不存在的 ID / Q 也 FAIL。局限：拆规则阶段漏掉的规则拦不住，靠「来源」列给评审对照 PRD 兜底。
- **漏洞修复**：①历史闸「未读」只认表格判定列以 `未读` 开头且无保留/待确认/丢弃行，表外备注不算；声明未读但本机能定位知识库 → WARN；②读图闸只认行首 `【图NN` 节标题，一行列多个图号不再算覆盖；③原子闸子句分隔加入「，且 / ，并且 / ，而且 / ，同时 / ，并」；④history 数据行不是 5 列直接 FAIL（原先静默跳过）。
- **导图带优先级**：`md_to_mindmap.py` 用例节点写成 `P0｜用例标题`（full / compact 都带），完整 ID 仍隐藏。
- **发布**：追溯表「落点」列的用例 ID 发布时改写为维度名（复用风险表影响列的改写函数，参数化列名），Q 编号保留；新增该表固定列宽 `[52, 420, 160, 191]`。
- **样例**：`example-testcases.md` 补 12 条规则的追溯表。
- **验证**：样例 PASS，导图 44 个用例节点全部带前缀，validate_mindmap PASS；负用例逐项 FAIL（缺追溯表 / 落点为空 / 不存在 ID 与未定义 Q / R 重复 / 来源为空 / 「，且」串 3 断言 / 备注写未读 / history 4 列行 / 一行列多个图号）；规范未读行 PASS 并出 WARN；`publish_to_lark_doc.py --dry-run` 通过，追溯表落点列改写为维度名、Q 保留、列宽生效。改前备份在会话 scratchpad，未真发飞书。

## 11.11 更新记录（2026-10-28 · 真实 PRD 试跑修复）

- **背景**：用「复习单元动态词池」PRD 试跑时暴露两个脚本问题：数值对账 6 条 WARN 全是误报；PRD 里两张 SVG 图（飞书把截图包成 SVG，内嵌 base64 PNG）`read_doc.py` 报尺寸 0x0，读图代理只能手动解码。
- **数值对账去误报**（`validate_output.py collect_value_phrases`）：①先去掉表格里的 URL（Figma 链接的 `id=67437` 不再被当数值）；②两侧都是数字的「+」只去掉加号（「1 + 1」不再拆出「+1」，「2+3 个」仍抽出「3个」）；③跳过飞书 PRD 模板的文档信息行（产品文档 / 产品Owner / 需求背景 / 产品目标 / 主要特性 / 修订记录），背景里的「70%」不再对账。
- **SVG 读图**（`read_doc.py`）：新增 `extract_svg_raster` 取 SVG 里最大的内嵌位图另存 `img-NN.embed.<ext>`，尺寸与超大图缩放都以位图为准，图片清单的「读」路径指向它；纯矢量 SVG 在日志和图片清单标 ⚠️，meta.json 记 `note`。新增 `image_entry` 合并首次下载与 `--resume` 两处相同的条目构造；`--resume` 识别已下载原图时排除 `.embed.` 文件。
- **验证**：试跑 tables.md 抽取结果从 11 个短语降为 4 个，交付目录 validate PASS 且无 WARN；构造表格确认「+50」「3星」仍会 WARN、链接 / 需求背景 / 「6 + 2」不再 WARN；样例 PASS。真实 PRD 重新 `read_doc.py`（首次 + `--resume`）两种路径下图 02、03 都输出 `img-NN.embed.read.png`，尺寸 2600x2164 / 2344x2670，已目视确认可读；构造纯矢量 SVG 出 ⚠️ 提示。改前脚本备份在会话 scratchpad。

## 11.12 更新记录（2026-10-28 · 必须修 3 项）

- **背景**：全景梳理发现 3 个会直接出错或违背意图的问题：飞书单表 490 块上限（试跑 58 条规则的追溯表已占 473 块，dry-run 查不出）；「冲突影响 P0 / 配置口径时停下问用户」只是提示词，试跑时没执行；发布默认放开租户内可编辑。
- **大表自动拆分**（`publish_to_lark_doc.py`）：新增 `split_table_rows`，按 `1 + 2 × 列数 × 行数 ≤ 490` 把超限表按行切成多张相邻表、每张重复表头（4 列表每张最多 60 行数据），在 `markdown_to_renderables` 收表时调用；`--dry-run` 输出 `max_table_blocks`，单行都放不下导致超限时退出 1，与真发布同一判据；`append_renderables` 原有超限报错保留作最后防线。
- **阻断级待确认闸**：第 6 块表头改为 `编号 | 级别 | 问题 | 影响`，级别 `阻断 / 已确认 / 记录`。`validate_output.py` 新增 `validate_risk_levels`：缺级别列、级别非法、存在阻断行、已确认行无「用户确认：」均 FAIL。规范同步：authoring-core §C 第 6 块定义与硬规则第 9 条；SKILL 步 4 分级并立即停下问、步 5 汇总代理产出里的阻断冲突、步 8 禁止自行改级别；history-kb-contract 停下问用户的三种情况对应阻断级；output-files 修法表两行；lark-output 发布态说明；example-testcases 风险表补级别列（全部为记录）。发布新增该表列宽 `[52, 60, 448, 263]`。
- **发布默认权限**：`--permission` 默认值从 `tenant_editable` 改为 `tenant_readable`，需要可编辑时显式传参；lark-output 同步。
- **兼容影响**：旧交付目录（风险表无级别列）重新校验或发布会 FAIL，需补级别列；旧的 `publish_state.json` 因内容指纹变化不能续传。
- **验证**：样例 PASS；阻断闸负用例 4 项逐项 FAIL（缺级别列 / 级别非法 / 阻断行 / 已确认无答复），规范已确认行 PASS；试跑目录副本风险表标 Q16 阻断时 `publish --dry-run` 在 validate_delivery 阶段拒绝；追溯表扩到 130 条后 dry-run 显示切成 61/61/11 行三片、`max_table_blocks=489`、列宽逐片生效；构造 300 列宽表 dry-run 报 `dry_run_table_limit` 退出 1；`--permission` 默认值核对为 `tenant_readable`。未真发飞书，改前整目录备份在会话 scratchpad。

## 11.13 更新记录（2026-10-28 · 取消 showcase 块）

- **背景**：用户反馈 showcase（提测准入）目前用不上，要求从输出去掉。showcase 用例只写在第 3 块、不在用例设计里重复，只隐藏导图节点会让这些用例从飞书交付里消失，所以整块取消。
- **骨架 7 块 → 6 块**：需求理解 → 风险判断 → 用例设计 → APP 常驻维度补充 → 风险与待确认 → 覆盖自检表。规范里的块号整体顺移（原第 4-7 块 → 第 3-6 块）；风险判断改为只决定 P0 排序；覆盖自检表必含维度去掉 showcase；历史线索落点、导图一级节点、发布裁剪块（三块 → 两块）同步去掉 showcase。涉及 SKILL / authoring-core / history-kb-contract / output-files / lark-output / mindmap-plantuml / PIPELINE。
- **脚本**：`validate_output.py` 去掉 showcase 必需块、1-5 条检查与覆盖表 showcase 维度检查，新增旧骨架拦截（出现 showcase 块即 FAIL 并给修法）；`md_to_mindmap.py` 去掉 showcase 置顶与相关分支，一级节点从第一个业务维度开始；`publish_to_lark_doc.py` 发布裁剪只跳过用例设计、APP 常驻两块，思维导图占第 3 号。
- **样例**：`example-testcases.md` 删 showcase 块，P0-01 改写为「闪卡正确跟读后 Unity 回顾可播放本次录音」挂到 Unity 单词回顾 / 已跟读词，P0-02 改写为「失败两次后点击下一步跳到下一个词」挂到失败递进 / 跳过，均为单断言、ID 不变；`example-mindmap-rich.puml` 删 showcase 分支。
- **兼容影响**：含 showcase 块的旧交付目录重新校验或发布会 FAIL，需按修法把用例移入用例设计。
- **验证**：样例 PASS；导图 210 节点、一级节点为 4 个业务维度 + 6 个常驻维度、无 showcase，P0-01/02 出现在对应分组，validate_mindmap 无错误；改前样例被拦下并给出取消提示；样例交付目录 dry-run 发布顺序为 需求理解 → 风险判断 → 用例设计思维导图 → 风险与待确认 → 覆盖自检表，编号 1-5 连续。改前整目录备份在会话 scratchpad。

## 11.14 更新记录（2026-10-28 · 飞书文档只留风险视角）

- **背景**：用户反馈飞书文档里的历史命中摘要（检索词组、命中取舍表、历史线索、冲突汇总）和交付文件清单增加阅读成本，只需要知道哪些有风险。
- **发布**：`publish_to_lark_doc.py` 不再发布 `history-hits.md` 和交付文件清单，飞书文档固定为 需求理解 → 风险判断 → 用例设计思维导图 → 风险与待确认 → 覆盖自检表；删除随之不用的 `history_for_publish` 与历史表列宽分支。`history-hits.md` 仍在本地生成并受 validate 校验，`--dry-run` 的 `files` 字段仍列本地文件。
- **规范**：有风险的历史线索（与 PRD 冲突、口径差异、可能被影响的旧逻辑）必须落成「风险与待确认」Q 项，问题列以「历史：」开头（authoring-core §C 第 5 块、history-kb-contract 合并规则）；lark-output 发布态说明同步。
- **验证**：样例交付目录 dry-run 只剩 5 个二级标题、3 张表（追溯 / 风险 / 覆盖），无历史与文件清单；大表拆分仍为 61/61/11；样例 validate PASS。改动中曾误删紧邻的 `split_table_rows`，已从改前备份原样恢复并逐段 diff 核对。

## 11.15 更新记录（2026-10-28 · 用例改为「操作 → 结果」短链）

- **背景**：同事认为导图里每条用例挂「前置 / 操作步骤 / 预期结果」三个长句节点太啰嗦，希望沿用团队手写导图（跟读挑战课）的写法：一条用例就是一条路径，中间节点是操作或条件，叶子是短结果，同一操作的多个结果并列；无编号、无优先级。用户确认一级结构（业务维度 + 6 个常驻维度）保持不变。
- **叶子格式**：`[P1-03] 操作或条件｜期望：结果` 两段短句。共用前置写成分解树标题（如 `##### 前置：配置目标词数 N=5`），不再写进叶子；同一操作多个结果拆成多条、操作文字一致。本地仍保留 ID 与 P0/P1/P2，追溯闸、阻断闸、覆盖自检表不变。
- **validate**：叶子必须含 `｜期望：`，出现 `｜前置：/｜步骤：` 即 FAIL；期望 >80 字 FAIL、>50 字 WARN，操作 >40 字 WARN；子句串联规则不变。
- **导图**：`md_to_mindmap.py` 用例输出为「操作节点 → 结果叶子」，同一树位置操作文字相同的用例合并为一个操作节点；去掉 11.10 加的 `P0｜` 优先级前缀；`--compact` 只出操作节点。
- **规范**：authoring-core（硬规则 4、6，先树后例补前置节点与同操作多结果，叶子格式，导图映射）、SKILL 步 7 与自检、history-kb-contract、mindmap-plantuml、lark-output、output-files 修法表、PIPELINE 同步。
- **样例**：`example-testcases.md` 44 条全部改写为短链；原「出现失败反馈且不解锁跳过」「解锁下一步且不自动跳词」两条复合断言各拆出一条（新增 P0-14、P1-27，并入覆盖表），用来示范同操作多结果合并。
- **兼容影响**：旧格式（含前置 / 步骤）的交付目录重新校验会 FAIL。待确认节点标黄未做，需先在飞书画板实测 PlantUML 颜色是否保留。
- **验证**：样例 PASS 且无 WARN；导图节点 210 → 122，无优先级前缀和前置 / 步骤 / 期望子节点，validate_mindmap 无错误，「读错一次」「点击下一步按钮」各合并为一个操作节点挂两个结果；构造 `##### 前置：N=5` 下 3 条同操作用例，导图为 前置 → 进入课程 → 3 个结果叶子；负用例：叶子带前置 FAIL、缺期望 FAIL、期望 85 字 FAIL、60 字 WARN、操作 45 字 WARN；样例交付目录 dry-run 通过。改前整目录备份在会话 scratchpad。

## 11.16 更新记录（2026-10-28 · 分解树按端分、不限层数、测试者视角命名）

- **背景**：用户用「复习单元动态词池」试跑后反馈三点：①需求同时有 Admin 和 App，用例却按 PRD 章节平铺（词池计算 / 每局抽词 / Admin 单元设置…），没先按端分；②树只到三级标题，没有按链路继续细化；③分组用了「表 4 示例路径」「排除规则」「开局现算」这类 PRD 术语，叶子也没写在哪个页面看，不看 PRD 读不懂。根因是 authoring-core 只示范 `###/####/#####`、第一层写「业务功能 / 需求类目」，且没有命名约束。
- **规范**：第 3 块标题改为「用例设计（按端 / 页面 / 功能组织）」；先树后例改为第一层按端分（Admin / App / 按需 服务端、H5、Web；单端时直接按页面/模块），往下按 页面 → 功能区 → 条件/状态 → 操作 → 结果 逐层细化、不设层数上限；跨端用例挂在看结果的一端、另一端操作写成前置节点，同一计算只在最直接可见的一端验；节点只用页面名、控件/字段名、真实数据，禁用 PRD 章节名、表号/图号、规则编号、概念词；可读标准为从根读到叶子是一句完整测试步骤。覆盖自检表业务维度改为「端 + 页面/模块」。6 个常驻维度仍是一级节点。涉及 authoring-core（含硬规则 10、11）、SKILL 步 7 与自检、mindmap-plantuml、output-files 修法表、history-kb-contract、lark-output、PIPELINE。
- **脚本**：`validate_output.py` 新增按端分组闸（端范围同时含 Admin/后台 和 App/Android/iOS/Unity/客户端 时，第 3 块每个 `###` 须以 Admin / App / 服务端 / H5 / Web 开头且至少 2 个）和命名闸（第 3、4 块分组标题含表号、图号、R 编号或「示例」即 FAIL）；第 3 块标题集中为 `BUSINESS_SECTION` 常量。`md_to_mindmap.py` 标题层级从 `#{3,9}` 放开为 `#{3,}`。
- **样例**：`example-testcases.md` 加入合成的 Admin「闪卡跟读题编辑页 / 音素打分开关」（R13，新增 P1-28、P1-29，跨端用例 P1-30 挂在 App 闪卡跟读题的「前置：Admin 关闭 rad 题的音素打分」下），第 3 块改为 Admin / App 两端，App 下按 闪卡跟读题 / 学习路径跟读题 / Unity 单词回顾页 → 功能区 → 状态逐层细化，最深 7 层；覆盖表业务维度改为端 + 页面。
- **兼容影响**：旧标题「用例设计（按业务功能 / 需求类目组织）」的交付目录重新校验会报 missing section。
