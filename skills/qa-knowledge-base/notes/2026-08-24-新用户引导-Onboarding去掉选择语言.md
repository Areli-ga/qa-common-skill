---
标题: onboarding 流程去掉选择语言
模块: 新用户引导 / Onboarding语言选择
版本: V1.37.0
related: [2026-08-11-AI Tutor-小麦中文课程.md, 2026-08-11-新用户引导-Onboarding流程引入中文.md]
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/WOZHwKZyKi80A4kVZRKlcn4kgbh
日期: 2026-08-24
---

## 摘要

V1.37.0 **下架 V1.36 的「Onboarding 引入中文」AB 实验（key `onboarding_chinesecourse`）**：选择年龄的页面**改回历史版本**、**新增孩子流程去掉选择语言**；但**菜单页仍保留切换语言进入中文小麦的入口**（覆盖印尼语 / 中文 / 英文，**语言基于设置中的语言**）。

> 本篇是 V1.36《Onboarding 流程引入中文》的**回退**，写用例前应连同那篇一起看（下架范围见待确认）。

## 功能信息（逻辑 / 状态 / 边界 / 字段）

### 1. 下架内容

- **下架：AB 实验 key `onboarding_chinesecourse`。**
- 数据参考：《Onboarding 增加中文流程数据》（外部文档，本库未存档）。

### 2. 调整点（原文仅三条）

**① 选择年龄的页面修改回历史版本**
- 原文给了「实验组」截图（图 1）；**「对照组」一行后面是空的，没有截图**。
- 实验组分镜（图 1，横向长条）：`Select the child's age`（0–13+ 数字网格）→ `Which way do you prefer?`（`With a parent` / `On their own`）→ `What do you want your child to gain here?`（多选：Speak English confidently / Learn English step by step / Get ready for primary school / Make screen time count / Boost school grades / Prepare for future work）→ `Your Child's Level`（柱状图 + 勾选清单）→ 进入主页。**该分镜中已无「选择语言」页**。

**② 菜单切换语言入口（保留）**
- **针对印尼语、中文和英文，菜单页面保持支持切换语言进入中文小麦。**
- **语言是基于设置中的语言。**

**③ 新增孩子去掉选择语言流程**
- 新增孩子流程（图 3）为**两步向导**，第 1 步「**填写孩子信息**」= 头像选择（8 个）+ **孩子的昵称** + **孩子的年龄**（步进器）；**没有语言选择步骤**。

### 3. 待确认项

1. **「对照组」截图缺失**：正文写「对照组：」后为空 —— 「选择年龄的页面**修改回历史版本**」到底回到什么形态，**无法从本文档取证**，需要产品补图或指明历史版本号。
2. **下架范围不清（最关键）**：V1.36《Onboarding 流程引入中文》包含五项 —— ① Onboarding 插语言选择页、② **中文锁 Level 1**、③ 中文首页直接是小 Mai、④ 家长中心可切语言、⑤ **每个孩子语言进度独立**。本篇只明确了「去掉选择语言」和「保留菜单切换语言」，**②③⑤ 是否一并下架完全没写**。
3. **存量实验组用户如何迁移**：已经选了中文、并已在中文路径上学习的孩子，实验下架后**走哪条路径、进度如何处理**（V1.36 新增了 `learn_language` 用户属性）—— 这是回退类需求最容易出事的地方，文档只字未提。
4. **`learn_language` 用户属性的去留**：下架后该属性是否保留、取值如何、历史埋点归属如何处理，未说明。
5. **「语言基于设置中的语言」与「每个孩子语言进度独立」可能冲突**：设置里的语言是**账号级**还是**孩子级**？多孩子账号切换孩子时语言如何取。
6. **「切换学习语言」弹窗正文完全没描述**（图 2 出现了两个形态）：一个带 **Lv1–Lv2 进度条**、一个带底部提示「**中文课程内测中，欢迎在「联系我们」中反馈问题**」。哪个是本期形态、进度条代表什么、内测提示是否保留，均未定义。
7. **全篇无数据埋点说明**：V1.36 相关的 `onboarding_language_click`、`add_child_language_click`（这两个事件在同批《路径双分支与搜索模块角标适配》的全量埋点清单里都还在）下架后**是否停报、是否删除、报表如何断档**，没有交代。
8. **文档极简（正文仅 223 字符）**：没有基本信息表、没有产品 Owner / 优先级 / 版本号字段、没有需求背景与目标、**没有验收标准** —— 本库按主人给定的 **V1.37.0** 入库。

## 图说明

原料目录：`raw/onboarding-流程去掉选择语言/`。共 3 张图，均为超大图，全部读 `.read` 缩放副本。

1. [img-01（16604×1210 超长横条，读 read 副本）](../raw/onboarding-流程去掉选择语言/images/img-01.read.png) —— **Onboarding 实验组完整分镜（7 帧）**：① `Select the child's age`（0–13+ 数字网格，含 13+）→ ② `Which way do you prefer?`（`With a parent` / `On their own` 两卡）→ ③ 同页选中态（`With a parent` 打勾）→ ④ `What do you want your child to gain here?`（六项多选：Speak English confidently / Learn English step by step / Get ready for primary school / Make screen time count / Boost school grades / Prepare for future work）→ ⑤ 同页选中态（3 项打勾）→ ⑥ `Your Child's Level` 柱状图 + 右侧勾选清单（「After completing this level, the child will know…」）→ ⑦ 进入主页（Max 与鹦鹉、`Go` 按钮）。**全程无「选择语言」页**。帧间夹有中文批注小卡（需求说明）。
2. [img-02（5272×1700，读 read 副本）](../raw/onboarding-流程去掉选择语言/images/img-02.read.png) —— **家长中心 + 切换学习语言**六宫格：上排为家长中心三态（中文版「家长中心」含 邀请好友 / 学习报告 / 联系我们 / 设置；英文版 `Parent Center` 含 `Free Learning Resources` banner；另一英文版含 `Magic Machine` banner），顶部均有 **孩子头像 `Lily` + 语言 `English`** 两个可切换胶囊，底部版本号 `V1.23.0 | 731507862769733`；下排为「**切换学习语言**」弹窗两态 —— 均为「选择你的学习语言」+ **英文 / 中文 两张国旗卡**，其一下方带 **Lv1–Lv2 进度条**，其二底部带提示条「**中文课程内测中，欢迎在「联系我们」中反馈问题**」。
3. [img-03（2664×1500，读 read 副本）](../raw/onboarding-流程去掉选择语言/images/img-03.read.png) —— **新增孩子流程第 1 步「填写孩子信息」**：顶部步骤条 **①→②**（两步）；左侧头像选择区（8 个头像，第 3 个选中带绿勾）；右侧 **「孩子的昵称」**输入框（示例「小可」）+ **「孩子的年龄」**步进器（− / 3 / +）；右下角 Max 插画。**该流程中已无语言选择步骤**。
