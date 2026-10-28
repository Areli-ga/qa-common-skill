# qa-testcase-design 链路与文件说明（团队版）

> 版本 2026-10-28。给同事快速理解：一条飞书 PRD 链接如何变成飞书测试用例文档，链路调用了哪些文件、每个文件干什么、怎么用。
> 本版要点：①规则收敛为**单一权威** `authoring-core.md`（原三份规则文件降为存根）；②工作流统一为 **1-8 整数步**；③`validate_output.py --dir` 一条命令校验整个交付目录，新增分号原子闸、四类检索词闸、读图覆盖闸、数值对账默认开启；④思维导图默认必产（发布依赖）。

## 一、端到端链路

```mermaid
flowchart TD
    A["飞书 PRD 链接（+可选提测范围）"] --> B["步1 进<br/>SKILL.md 总控 · 建交付目录 /tmp/qa-testcase-design-短名-时间/"]
    B --> C["步2 保真读取【飞书·读】<br/>read_doc.py + lark_common.py<br/>→ source/: content.txt·tables.md·images/·meta.json"]
    C --> E["步3 读图代理<br/>>8张拆分片 → images-notes.md"]
    C --> F["步3 历史代理<br/>history-kb-contract.md · kb.py→search.py · 深读 notes<br/>→ history-hits.md"]
    C --> G["步4 主线对齐<br/>读 content.txt+tables.md 复述需求+待确认"]
    E --> H["步5 合流验收<br/>图占位全覆盖 · P0关键图主线亲读 · 检索词组核对<br/>不过则主线串行补做"]
    F --> H
    G --> H
    H --> I["步6 立场与防漏<br/>authoring-core.md 一次装载 · 风险判断 · 逐维过闸<br/>code-risk-*.md 按端命中才读"]
    I --> J["步7 出例<br/>先树后例 · 原子用例 · 覆盖自检表 → testcases.md"]
    J --> L["步8 校验<br/>md_to_mindmap.py → mindmap.puml<br/>validate_output.py --dir 交付目录"]
    L --> M["步8 发布【飞书·写】<br/>publish_to_lark_doc.py：新建 docx + 呈现层裁剪 + 回写 meta.json"]
    M --> N["交付：飞书 docx 链接 + 本地目录<br/>导图代码块可直接粘进飞书画板"]
```

链路只用到两个 skill：**qa-testcase-design**（主流水线）和 **qa-knowledge-base**（历史知识库，只读检索）。

## 二、飞书对接层（本链路自带，不依赖外部 skill）

对接飞书由 qa-testcase-design 自己的 3 个脚本完成，直连 Lark OpenAPI：

| 文件 | 职责 | 触发点 |
|---|---|---|
| `scripts/read_doc.py` | **读飞书**：拉正文+表格+下载全部图片+缩放副本（sips→PIL→头解析三级降级）；中断后 `--resume` 续跑只补缺 | 步 2 |
| `scripts/publish_to_lark_doc.py` | **写飞书**：新建 docx、呈现层裁剪、回写 meta；中断后 `--resume` 从断点续传不重复建档（进度存 `publish_state.json`） | 步 8 |
| `scripts/lark_common.py` | **凭证与 HTTP 共享库**：env → config 服务换 tenant_access_token；网络层错误自动重试 3 次 | 被上面两者调用 |

凭证机制：优先环境变量 `LARK_APP_ID/SECRET/DOMAIN`，缺失则拉 `skill-config.giggletools.com`（需 VPN）。**已不再走 giggle-common gateway / CF Access**。

> **辨析（避免同事混淆）**：系统里的 `giggle:lark-docs` 是通用飞书文档 skill，**本链路未使用**——自带脚本直连更快、凭证独立。`writing-lark-test-mindmaps` 已**完全弃用**并移出 skills 目录，不在链路内。

## 三、Skill 目录逐文件说明

### 3.1 qa-testcase-design（主 · `~/.claude/skills/qa-testcase-design/`）

```
qa-testcase-design/
├── SKILL.md                    【L0 入口·自动加载】1-8 步总控流程 + 边界红线 + 完成门槛
├── PIPELINE.md                 本文件：团队版链路与文件说明
├── DESIGN.md                   设计决策与更新记录（为什么这样设计），改流程前先读
├── references/
│   ├── authoring-core.md       【L1 唯一规则源·步6读一次】§A覆盖维度+风险库触发表 / §B测试设计方法+决策表+反例 / §C 6块骨架+先树后例+原子用例+优先级+自检表+机器校验硬规则
│   ├── output-files.md         【L1】交付目录结构·校验命令(--dir)·校验失败修法
│   ├── history-kb-contract.md  【L1·历史代理读】qa-knowledge-base只读契约：四类检索词·命中筛选·深读·证据格式
│   ├── lark-output.md          【L1】发布规则：默认Drive目录·凭证·呈现层裁剪·续传·失败处理
│   ├── code-risk-backend.md    【L2 命中才读】后端风险库
│   ├── code-risk-unity.md      【L2】Unity风险库
│   ├── code-risk-native.md     【L2】原生风险库
│   ├── code-risk-h5.md         【L2】H5风险库（通用面，具体规律待补）
│   ├── mindmap-plantuml.md     【L2】导图结构来源·校验拦截·粘贴铁律（排查导图时读）
│   ├── example-testcases.md    【L3】标准6块样例（先树后例+原子用例），校验失败排查/初次接触时读
│   ├── example-mindmap-rich.puml 【L3】手写 PlantUML 块的富层级样例（极少用）
│   ├── coverage-dimensions.md  【存根】已并入 authoring-core §A，勿读
│   ├── case-schema.md          【存根】已并入 authoring-core §C，勿读
│   ├── test-design-methods.md  【存根】已并入 authoring-core §B，勿读
│   └── example-output.md       【存根】样例兼容索引
└── scripts/
    ├── read_doc.py             飞书PRD保真读取（--out 落盘 · --resume 续跑 · --quiet 不回显全文）
    ├── publish_to_lark_doc.py  新建飞书docx+呈现裁剪（--target 有默认目录 · --resume/--fresh）
    ├── lark_common.py          凭证/HTTP共享库（不单独运行）
    ├── kb.py                   定位 qa-knowledge-base 并转发 search.py
    ├── validate_output.py      交付硬校验：格式闸+粒度闸+原子闸(长度/分号/「，且」类连接)+需求追溯闸+阻断待确认闸+历史四类检索词闸+读图覆盖闸+数值对账+导图占位闸；--dir 一次校验整个交付目录
    └── md_to_mindmap.py        testcases.md → 合法.puml 确定性转换（树形完全来自 ###/####/… 分解树，不限层数）
```

文件分级含义：**L0** 自动加载；**L1** 每次执行都读；**L2** 命中对应场景才读；**L3** 平时不读，排查或溯源时才读。

### 3.2 qa-knowledge-base（历史知识库 · 与主 skill 平级）

qa-knowledge-base 是自带 `SKILL.md` 的独立 skill，和 `qa-testcase-design` **平级放在同一个 `skills/` 目录**下：本地是软链指向知识库真身，分发给同事时是自包含实体目录（不带 raw）。主 skill 靠 `scripts/kb.py` 按「`QA_KNOWLEDGE_BASE_HOME` → 同级 `../qa-knowledge-base`」探测定位，找不到则历史编译降级为「未读 qa-knowledge-base」，本地/分发都零配置。知识库本体内容：

```
~/.codex/skills/qa-knowledge-base/
├── SKILL.md                本体规则入口
├── CLAUDE.md               目录约定与红线（什么放哪、命名、只读边界）
├── AGENTS.md               协作代理约定
├── RESUME.md               断点续录进度
├── taxonomy.md             模块分类体系（检索/归类依据）
├── scripts/
│   ├── fetch.py            录入：拉飞书需求 → 存 raw/ 并生成 notes/（qa-knowledge-base 自己维护用，本链路不碰）
│   ├── search.py           检索：关键词/--module/--version（★本链路历史代理调用的就是它）
│   ├── build_index.py      重建 index/INDEX.md 全库索引
│   └── relate.py           计算笔记间关联关系
├── notes/                  结构化历史笔记（篇数随入库增长，以 index/INDEX.md 为准），命名 YYYY-MM-DD-模块-标题.md（人读+被检索的主体）
├── raw/                    每篇需求一个目录，每个存飞书原始产物（blocks.json/content.txt/images/meta.json），供溯源回看
├── index/INDEX.md          全库索引（search 的召回底座）
├── docs/                   知识库自身项目文档（mvp/architecture/tech-stack/pending-confirmations）
└── wiki/                   预留目录
```

**本链路与 qa-knowledge-base 的关系**：只读 `search.py` 检索 + 深读 `notes/*.md`，必要时回看 `raw/`。**绝不写入** qa-knowledge-base（录入是 `fetch.py` 的职责，与本链路分离）。

## 四、使用方法

**触发**（一句话）：
> 设计测试用例：<飞书 PRD 链接>

带提测范围会提升风险判断精度：
> 设计测试用例：<链接>。本次只改原生+后端，重点关注反馈回复推送链路。

**产出**：
- 本地交付目录 `/tmp/qa-testcase-design-<短名>-<YYYYMMDD-HHMM>/`（macOS 上 /tmp 即 /private/tmp；含时分，避免同日覆盖）：`testcases.md` · `history-hits.md` · `images-notes.md` · `mindmap.puml` · `source/`
- 新建飞书 docx（默认 Drive 目录）：需求理解 → 风险判断 → 思维导图代码块 → 风险与待确认 → 覆盖自检表；**复制文档里的 PlantUML 代码块直接粘进飞书画板即得导图**

**可选控制**：
| 想要 | 说法 |
|---|---|
| 只出本地不发飞书 | 「只本地输出」 |
| 发到别的飞书目录 | 给出目录链接（当次生效） |
| 图片下载失败仍继续 | 同意后加 `--allow-partial` |
| 读取中断后续跑 | 同一输出目录加 `--resume`（复用已落盘正文/图片只补缺） |
| 发布中断后续传 | `publish_to_lark_doc.py <目录> --resume`（复用已建文档，不重复建档；直接重发会被护栏拦截，放弃半成品用 `--fresh`） |
| 手动重发旧交付 | `python3 scripts/publish_to_lark_doc.py <旧目录>` |

**不可关闭的质量四支柱**：保真读取（未解析块登记待确认）· 历史编译（线索必须编入+留证据）· 逐维过闸（validate 机械拦截漏项，含**粒度闸**：分组必须多级细分、期望必须原子断言、PRD 表格数值逐个对账）· 方法出例（先落分解树、再挑方法、再落可执行叶子）。

**导图质量口径（2026-07-08 根治后）**：思维导图由 testcases.md 第 3 块「用例设计」的分解树确定性生成——第一层按端分（Admin / App），往下按页面 → 功能区 → 条件逐层细化、不限层数，节点用页面/控件/真实数据命名；数值逐项、分支逐行、结局逐个成节点，无「功能点」占位层，用例写成「操作 → 结果」短链，共用前置是树上的一层节点。低粒度结构（平铺分组、打包期望）会被 validate 直接 FAIL，过不了发布关。
