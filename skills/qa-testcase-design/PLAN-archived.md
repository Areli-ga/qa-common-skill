# qa-testcase-design Implementation Plan

> 归档存根：运行时不要读取本文件，不要按本文件派生当前行为。当前事实只看 `SKILL.md` / `DESIGN.md` / `references/case-schema.md` / `references/test-design-methods.md` / `scripts/read_doc.py`。

> ⚠️ **已完成 / 仅存档（2026-07-01）** — 本 skill 已建成并验证通过。这是**当初的实施计划**，实现过程中有偏离：coverage-pointer.md 被砍（清单路径直接写进 SKILL.md）、"镜像到 .codex"一步取消（两运行时实测自动同步）、叶子格式几经调整（最终为单格式 +「（待确认）」后缀）、新增了 `scripts/read_doc.py` 读图。**当前事实以 `SKILL.md` + `DESIGN.md` 为准**，本文件不再维护，仅作过程留档。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建一个格式无关的「测试用例设计引擎」skill，把产品需求 + 覆盖清单 + 按需检索的 qa-kb 历史需求知识，编译成全面、按风险排序、可执行的结构化用例中间产物。

**Architecture:** skill 由 1 个 SKILL.md（8 步语义工作流）+ 2 个 reference 文件（用例结构模板、覆盖清单指针）组成。几乎零新代码：检索复用 `qa-knowledge-base/scripts/search.py`，覆盖清单复用兄弟 skill `writing-lark-test-mindmaps`，出格式交下游。

**Tech Stack:** Markdown（skill 定义与 reference）；调用现成 Python 脚本 `qa-knowledge-base/scripts/search.py`；无新依赖、无新脚本。

## Global Constraints

- 交付物是 skill，不是带单测的代码；每个任务的"验证"= 内容自检 / 路径解析检查 / dry-run，不是 pytest。
- `.claude/skills` 与 `.codex/skills` 均非 git 仓库 —— **不做 git commit**；用"写入并验证"收尾。
- skill 主目录：`/Users/dong/.claude/skills/qa-testcase-design/`，完成后镜像到 `/Users/dong/.codex/skills/qa-testcase-design/`。
- 覆盖清单用相对路径引用：`../writing-lark-test-mindmaps/references/giggle-qa-coverage.md`（禁止硬编码 `.claude`/`.codex` 绝对路径）。
- qa-knowledge-base 只读调用，**不修改、不新增、不回写** `/Users/dong/.codex/skills/qa-knowledge-base/`。
- 用例叶子格式与 `writing-lark-test-mindmaps` 对齐：`[P0/P1/P2] 标题｜前置：…｜步骤：…｜期望：…｜来源：…｜待确认：…`。
- 禁止编造产品逻辑/接口字段/AB 策略/视觉标准；缺信息写「待确认」。
- 禁止「验证功能正常」「检查页面无问题」这类空泛用例。
- v1 不做：往回织回流、用例管理/报告、自动写飞书、自动化脚本、opentest 必达。

---

### Task 1: 脚手架 + 覆盖清单指针

**Files:**
- Create: `/Users/dong/.claude/skills/qa-testcase-design/references/coverage-pointer.md`

**Interfaces:**
- Produces: skill 目录结构 `qa-testcase-design/references/`；`coverage-pointer.md` 供 SKILL.md 步 6 引用。

- [ ] **Step 1: 建目录**

Run:
```bash
mkdir -p /Users/dong/.claude/skills/qa-testcase-design/references
```

- [ ] **Step 2: 写 coverage-pointer.md**

写入 `/Users/dong/.claude/skills/qa-testcase-design/references/coverage-pointer.md`：

```markdown
# 覆盖维度清单指针

本 skill 不复制覆盖清单，只引用同运行时下兄弟 skill 的现成清单：

`../writing-lark-test-mindmaps/references/giggle-qa-coverage.md`

（相对本 skill 目录。Claude Code 读 `~/.claude/skills/...` 副本，Codex 读 `~/.codex/skills/...` 副本，各自正确，不硬编码绝对路径。）

## 清单包含的维度（执行时以文件实际内容为准）

- 产品链路：启动 / 账号 / 学习 / 内容 / 运营
- 技术端：Android / iOS / Unity / H5 / Flutter / 后端
- 通用场景：主流程 / 反向中断 / 状态矩阵 / 弱网 / 兼容 / 数据一致性 / 回归
- 风险提示：多端联动状态同步、Unity 资源/动画、后台配置/AB、热更恢复、纯视觉稿补问

## 使用方式

工作流「步 6 防漏」时，读取该清单，逐维过闸——每维只能是「已覆盖 / N/A / 待确认」。
若清单读取失败（路径变动），停止并提示用户，不要凭记忆编维度。
```

- [ ] **Step 3: 验证相对路径能解析到真实清单**

Run:
```bash
ls -la /Users/dong/.claude/skills/qa-testcase-design/references/../../writing-lark-test-mindmaps/references/giggle-qa-coverage.md
```
Expected: 列出该文件（存在，约 2420 字节）。若 No such file，说明兄弟 skill 缺失，停止排查。

---

### Task 2: 用例结构模板 case-schema.md

**Files:**
- Create: `/Users/dong/.claude/skills/qa-testcase-design/references/case-schema.md`

**Interfaces:**
- Consumes: 无。
- Produces: `case-schema.md`，供 SKILL.md 步 7/步 8 引用（用例骨架、叶子格式、优先级、自检表、判定规则）。

- [ ] **Step 1: 写 case-schema.md**

写入 `/Users/dong/.claude/skills/qa-testcase-design/references/case-schema.md`：

```markdown
# 测试用例中间产物结构

本 skill 产出「格式无关的结构化用例中间产物」。下游（`writing-lark-test-mindmaps` / 未来 formatter）据此出思维导图 / Excel / XMind。

## 输出骨架（顺序固定，9 块）

1. 需求理解（目标 / 入口 / 用户路径 / 状态 / 端 / 接口 / AB / 埋点 / 验收口径）
2. 风险判断（这次最该测什么 + 理由，非中性复述）
3. P0 主流程
4. P1 重要场景
5. P2 边界/兼容
6. 跨端联动
7. 后端 / 配置 / AB / 埋点
8. 风险与待确认
9. 覆盖自检表

## 用例叶子格式（与 writing-lark-test-mindmaps 对齐，一行一条）

​```text
[P0/P1/P2] 用例标题｜前置：...｜步骤：...｜期望：...｜来源：PRD-xx / 历史需求-xx / 覆盖维度-xx｜待确认：...
​```

- 步骤具体可执行；禁止「验证功能正常」「检查页面无问题」这类空泛叶子。
- 来源必标：PRD 出处 / qa-kb 历史需求 / 覆盖维度，便于追溯。
- 缺信息写「待确认」，不编造产品逻辑、接口字段、AB 策略、视觉标准。

## 优先级定义

| 优先级 | 含义 |
|---|---|
| P0 | 不通过不能发版：主链路、启动、登录、奖励、学习进度、热更、核心接口、核心配置 |
| P1 | 重要路径：常用分支、配置/AB、跨端状态、异常恢复、弱网恢复 |
| P2 | 边界、兼容、探索、低频状态、文案/视觉细节 |

## 覆盖自检表（每次必出）

​```text
| 维度 | 状态 | 对应用例 | 说明 |
|---|---|---|---|
| 主流程 | 已覆盖 | P0-1, P0-2 | 覆盖入口到结果 |
| Unity | N/A | — | 本需求不涉及 Unity 课程资源 |
| AB 配置 | 待确认 | P1-3 | PRD 未说明分组和灰度策略 |
​```

### 状态判定规则

| 状态 | 判定标准 |
|---|---|
| 已覆盖 | 该维度与本需求相关，且 ≥1 条可执行用例覆盖，用例可追溯到 PRD/历史/清单 |
| N/A | 与本需求明显无关，并写明理由 |
| 待确认 | PRD 没写清、无法判断是否需测；写原因 + 影响哪些用例 |

禁止只写「已检查」「正常验证」。自检表要能让 QA 一眼看出漏没漏。
```

> 注：上方代码块内的 `​```text` 是模板内嵌示例，写文件时保留为普通反引号围栏即可（示例用零宽字符占位仅为在本计划中转义，实际文件写标准 ```）。

- [ ] **Step 2: 验证内容完整**

Run:
```bash
grep -c -E "输出骨架|用例叶子格式|优先级定义|覆盖自检表|状态判定规则" /Users/dong/.claude/skills/qa-testcase-design/references/case-schema.md
```
Expected: `5`（五个必需小节都在）。

---

### Task 3: SKILL.md —— 8 步语义工作流

**Files:**
- Create: `/Users/dong/.claude/skills/qa-testcase-design/SKILL.md`

**Interfaces:**
- Consumes: `references/coverage-pointer.md`（Task 1）、`references/case-schema.md`（Task 2）、`qa-knowledge-base/scripts/search.py`（现成）。
- Produces: 可触发的 skill 入口。

- [ ] **Step 1: 写 SKILL.md**

写入 `/Users/dong/.claude/skills/qa-testcase-design/SKILL.md`：

````markdown
---
name: qa-testcase-design
description: Use when 把 Giggle Academy 产品需求(飞书链接或粘贴文本)设计成全面、按风险排序、可直接执行的结构化测试用例中间产物;会先判断本次高风险、按需只读检索 qa-kb 历史需求逻辑与回归线索、强制逐维过覆盖清单防漏。产出可交 writing-lark-test-mindmaps 出思维导图,或后续 formatter 出 Excel/XMind。不做需求录入(qa-knowledge-base 干)、不做用例管理/执行报告(opentest 干)、不自动写飞书、不生成自动化脚本。
---

# 测试用例设计引擎

把「本次需求 + 覆盖清单 + 按需检索的历史需求知识」**编译**成全面、按风险排序、可执行的结构化用例中间产物。质量来自三支柱：历史编译、逐维防漏、风险立场。

## 边界（先读）

- 只产出**格式无关的中间产物**；出飞书思维导图/Excel/XMind 交下游。
- qa-knowledge-base **只读**：`/Users/dong/.codex/skills/qa-knowledge-base/` 不改、不新增、不回写。
- 不编造产品逻辑/接口字段/AB 策略/视觉标准；缺信息一律写「待确认」。
- v1 不做往回织回流、用例管理、执行报告、自动写飞书、自动化脚本。

## 复用资源（不重造）

- 覆盖清单：`references/coverage-pointer.md` → 指向 `../writing-lark-test-mindmaps/references/giggle-qa-coverage.md`
- 用例结构 / 优先级 / 自检表：`references/case-schema.md`
- 历史检索：`python3 /Users/dong/.codex/skills/qa-knowledge-base/scripts/search.py <关键词|--module 模块|--version 版本>`
- 读飞书：`giggle:lark-docs`
- 出思维导图：`writing-lark-test-mindmaps`

## 8 步工作流

**1 进** — 接收需求。飞书链接 / 粘贴文本 + 可选：本次改动点、影响端范围、提测说明、配置/AB 范围。

**2 保真读取** — 飞书链接用 `giggle:lark-docs` 读，优先保留正文、表格、图片、UI 状态图、字段图。凡是没读到的原始结构（图/表），必须在产出里标「未保真读取，覆盖有风险」。粘贴文本同样标「未含图片/表格原始结构」的覆盖风险。

**3 对齐** — 用自己的话复述需求理解（目标/入口/路径/状态/端/接口/AB/配置/埋点/验收口径），并列出 PRD 没写清的**待确认项**。不编造。先跟用户对齐，再继续。

**4 编译历史** — 按需只读调用 search.py（按模块/版本/关键词），从命中笔记里**挑出与本次相关的历史需求逻辑、旧边界、相邻入口、回归线索**，排除无关噪声。注意：qa-knowledge-base 是需求知识库，不是 bug 库——这里是基于历史需求知识现算，不是查历史缺陷。检索命令示例：
```bash
python3 /Users/dong/.codex/skills/qa-knowledge-base/scripts/search.py 奖励 领取
python3 /Users/dong/.codex/skills/qa-knowledge-base/scripts/search.py --module 学习
```

**5 立场** — 先判断「**本次改动真正的高风险在哪、最该测什么**」，写一段风险判断 + 理由。这决定后面 P0 排序，不是一碗水端平。

**6 防漏** — 读取 `references/coverage-pointer.md` 指向的覆盖清单，**逐维过闸**。每维只能是「已覆盖 / N/A / 待确认」，禁止默默跳过；判定标准见 `case-schema.md`。

**7 出例** — 按 `case-schema.md` 的 9 块骨架 + 叶子格式输出用例，带优先级、来源标注、待确认。步骤具体可执行，禁空泛。

**8 自检与交付** — 按 `case-schema.md` 输出**覆盖自检表**（维度 | 状态 | 对应用例 | 说明），让用户一眼看漏没漏。末尾提示：①可交 `writing-lark-test-mindmaps` 出飞书思维导图；②执行后如发现新缺陷/新回归点，建议后续 ingest 回 qa-kb（v1 不自动做）。

## 质量门槛（交付前自检）

- [ ] 覆盖清单每一维都有明确状态，无默默跳过
- [ ] 每条用例可直接执行，无「验证功能正常」空泛叶子
- [ ] 每条用例标了来源（PRD/历史/维度）
- [ ] 缺信息写了「待确认」，无编造
- [ ] 有一段「本次最该测什么」的风险判断
- [ ] 图/表未保真读取时已标覆盖风险
````

- [ ] **Step 2: 验证 frontmatter 与工作流完整**

Run:
```bash
head -3 /Users/dong/.claude/skills/qa-testcase-design/SKILL.md
grep -c -E "^\*\*[1-8] " /Users/dong/.claude/skills/qa-testcase-design/SKILL.md
```
Expected: 第一行 `---`、第二行以 `name: qa-testcase-design` 开头；grep 计数 `8`（8 步齐全）。

- [ ] **Step 3: 用 writing-skills 校验 skill 结构与 description 触发质量**

Invoke skill: `writing-skills`（校验 frontmatter 合法、description 是否覆盖触发场景、与 `qa-knowledge-base`/`writing-lark-test-mindmaps` 描述无冲突/无抢触发）。按其反馈就地修正 description，直至清晰不重叠。

---

### Task 4: 镜像到 .codex 运行时

**Files:**
- Create: `/Users/dong/.codex/skills/qa-testcase-design/`（整目录镜像）

**Interfaces:**
- Consumes: Task 1-3 完成的 `.claude/skills/qa-testcase-design/`。
- Produces: Codex 运行时下可用的同一 skill。

- [ ] **Step 1: 镜像目录**

Run:
```bash
cp -R /Users/dong/.claude/skills/qa-testcase-design /Users/dong/.codex/skills/qa-testcase-design
```

- [ ] **Step 2: 验证两运行时下相对路径都解析到各自 coverage 副本**

Run:
```bash
ls /Users/dong/.claude/skills/qa-testcase-design/references/../../writing-lark-test-mindmaps/references/giggle-qa-coverage.md
ls /Users/dong/.codex/skills/qa-testcase-design/references/../../writing-lark-test-mindmaps/references/giggle-qa-coverage.md
```
Expected: 两行都列出文件（两运行时镜像各自自洽）。

---

### Task 5: 真实需求 dry-run（skill 的真验证）

**Files:**
- 无（运行验证，不产生 skill 文件）。

**Interfaces:**
- Consumes: 完整 skill（Task 1-4）+ qa-knowledge-base（现成，只读）。

- [ ] **Step 1: 准备一个真实输入**

选一个近期真实需求：飞书 PRD 链接，或一段粘贴的需求文本（含至少一个跨端 + 一个配置/AB 点，便于检验防漏）。

- [ ] **Step 2: 触发 skill，走完 8 步**

在会话里调用 `qa-testcase-design`，喂入 Step 1 的需求。观察：
- 步 2 是否标了图/表保真风险；
- 步 3 是否列了待确认、无编造；
- 步 4 是否真的跑了 search.py 并挑出相关历史（而非空谈）；
- 步 5 是否给了「这次最该测什么」的风险判断；
- 步 6 是否逐维给了状态（已覆盖/N/A/待确认）。

- [ ] **Step 3: 核对产出契约**

对照 `case-schema.md`：产出含 9 块骨架 + 叶子格式合规 + 覆盖自检表。抽查 3 条用例：步骤可执行、有来源标注、无空泛。

- [ ] **Step 4: 验证可交下游**

把产出交给 `writing-lark-test-mindmaps`，确认叶子格式能被它直接消费出思维导图节点（格式对齐无需人工改写）。

- [ ] **Step 5: 对照成功标准记录结论**

对照 spec 第 10 节正向/失败信号，记录：是否比手写/旧方式少遗漏、自检表是否有真实防漏价值、历史检索噪声是否可控。发现问题回退到对应 Task 修正 reference / 工作流措辞。

---

## Self-Review

**Spec coverage：**
- spec §4 进存取 → Task 1（存·清单指针）、Task 3（进/取工作流）✅
- spec §5 8 步工作流 → Task 3 SKILL.md 8 步 ✅
- spec §6 质量三支柱（历史编译/逐维闸门/风险立场）→ Task 3 步 4/6/5 + 质量门槛 ✅
- spec §7 覆盖判定规则 → Task 2 case-schema.md 状态判定规则 ✅
- spec §8 文件结构 → Task 1-3 ✅
- spec §9 中间产物结构/优先级/自检表 → Task 2 ✅
- spec §0/§11 只读边界、不回写、opentest 非必达 → Global Constraints + Task 3 边界 ✅
- spec §10 14 天验证 → Task 5 dry-run + 成功标准核对 ✅
- 跨运行时可用（相对路径）→ Task 4 镜像 + 双路径验证 ✅

**Placeholder scan：** 无 TBD/TODO；每个文件的完整内容已内嵌在步骤中。case-schema 内嵌代码围栏的转义已在 Task 2 注明。

**Type consistency：** 叶子格式 `[P0/P1/P2] 标题｜前置｜步骤｜期望｜来源｜待确认` 在 Global Constraints、case-schema.md（Task 2）、SKILL.md 步 7（Task 3）三处一致；覆盖清单相对路径 `../writing-lark-test-mindmaps/references/giggle-qa-coverage.md` 在 Task 1/3/4 一致；search.py 绝对路径三处一致。
