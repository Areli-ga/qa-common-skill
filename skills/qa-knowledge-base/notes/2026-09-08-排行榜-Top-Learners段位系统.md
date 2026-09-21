---
标题: Top learners排行榜优化：支持段位
模块: 排行榜 / Top Learners学习之星
版本: V1.38.0
related: [2026-06-30-排行榜-Top Learners排行榜玩法.md, 2026-06-30-排行榜-排行榜规则说明.md, 2026-08-11-排行榜-排行榜细节优化.md, 2026-09-08-IP打电话-IP打电话增加孩子亲密度.md, 2026-09-08-任务体系-任务2.0.md, 2026-09-08-功能广场-鹦鹉学舌变声机.md, 2026-09-08-单词回顾-每日复习任务.md, 2026-09-08-同桌-邀请同桌1.3随机匹配.md]
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/SkC0wADU0i8txYkCisRly4E2gth
日期: 2026-09-08
---

## 摘要

V1.38.0 给 Top Learners 周榜加一层**跨周不可失去的段位（7 级）**：每周结算时前 10 名升一级、11–30 名不变、只升不降、每周最多升一级、最快 6 周封顶，把「这周冲一冲」延伸为「我要一直冲」。

## 功能信息（逻辑/状态/边界/字段）

### 背景与目标

- 背景：Top Learners 周榜只覆盖单周维度，**每周排名清零重来，缺乏跨周的长期成长标识**。加入段位晋升层，为持续活跃用户提供**可积累、不可失去**的身份标识。
- 目标：**提升周留存率**。
- UI：`https://www.figma.com/design/ILqThciQTufJKCFPmIuDVH/1.38.0?node-id=52139-94617`

### 1. 核心玩法（修改版）

- 每周结算时，**本周排名第 1–10 名 → 升一级**。
- **本周排名第 11–30 名 → 段位不变。**
- **已达到最高段位的用户，排名前 10 也不再变化。**
- **每周最多升一级，不可跳级。**
- **段位只升不降**，最快 **6 周**达到最高级。
- **不发放额外奖励。**

### 2. 段位命名（⚠️ 文档内三套并存）

**img-01「修改版」对照表（最新一版，含三语与埋点枚举）**

| 序号 | 旧命名（中） | 旧命名（英） | **新命名（中）** | **新命名（英）** | **新命名（印尼）** | **埋点枚举值** | TTS 朗读稿（英） |
|---|---|---|---|---|---|---|---|
| 1 | 训练生 | Cadet | 学习之星 1 段 | TopStar Lv1 | TopStar Lv1 | 1 | `TopStar level one` |
| 2 | 宇航员 | Astronaut | 学习之星 2 段 | TopStar Lv2 | TopStar Lv2 | 2 | `TopStar level two` |
| 3 | 领航员 | Navigator | 学习之星 3 段 | TopStar Lv3 | TopStar Lv3 | 3 | `TopStar level three` |
| 4 | 舱长 | Captain | 学习之星 4 段 | TopStar Lv4 | TopStar Lv4 | 4 | `TopStar level four` |
| 5 | 指挥官 | Commander | 学习之星 5 段 | TopStar Lv5 | TopStar Lv5 | 5 | `TopStar level five` |
| 6 | 将军 | Admiral | 学习之星 6 段 | TopStar Lv6 | TopStar Lv6 | 6 | `TopStar level six` |
| 7 | 星际传奇 | Star Legend | 学习之星 7 段 | TopStar Lv7 | TopStar Lv7 | 7 | `TopStar level seven` |

- **正文**（页面改动段）仍写旧命名：「训练生 — 宇航员 — 领航员 — 舱长 — 指挥官 — 将军 — 星际传奇」。
- **内嵌 Sheet1** 也只有旧命名（中/英）。
- **内嵌埋点表**的 `user_tier` / `viewed_user_tier` / `current_tier` / `new_tier` 枚举全部是 `Cadet / Astronaut / Navigator / Captain / Commander / Admiral / Star Legend`（旧英文名），**与 img-01 定的数字枚举 1–7 冲突**。
- **所有设计稿（img-02 / img-05）里的段位标签也仍是旧中文名**。

### 3. 页面改动

**① 排行榜页顶部段位进度条（img-02）**

- 进入 Top Learners 排行榜页面时展示当前段位；**需 UI 设计，目前参考了多邻国**。
- 七段横向排列，段位状态三态：**已达到（绿圈）/ 当前（紫圈高亮 + 名称加粗着色）/ 未达到（灰）**。
- 页面结构：顶部 tab `Top learners` / `Streak`，其下为段位条，再下为「还剩 X 天，周一结算奖励」提示。

**② 晋级分割线（img-02 / img-03）**

- **第 10 名和第 11 名之间插入一条晋级分割线**：`⬆️ 前 10 名下周晋级下一段位`。
- **主路径页面和排行榜入口页面都要增加分割线。**
- ⚠️ 两版设计稿文案不同：排行榜页（img-02）为 **「↑ 以上可晋升下一段位」**；主路径弹窗版（img-03）为 **「⬆ 前 10 名下周晋升下一段位」**；正文写的是「前 10 名下周晋级下一段位」（晋级 vs 晋升）。

**③ 榜单行与个人形象卡（img-02 / img-04）**

- 排行榜列表每行在昵称后展示**段位标签**（带底色的小胶囊，如 指挥官 / 舱长 / 领航员 / 宇航员 / 训练生）。
- **个人形象卡增加用户段位**：形象卡内容为 Avatar + 昵称 + 国旗 + `🏆 Lv X` + **段位标签** + 点赞数；下方两块数据「本周课程数」「连胜天数」。
- **机器人也需要增加段位** —— ⚠️ 正文写「规则如下：」后接的是个人形象卡截图（img-04），**机器人段位的分配规则实际缺失**。
- ⚠️ 主路径弹窗版榜单（img-03）**行内没有段位标签**，与排行榜页（img-02）不一致，需确认是否两处都要加。

**④ 战报与晋升庆祝（img-05）**

- 正文：**战报 —— 晋升后展示段位晋升，点击后进入数据战报；如果段位没有上升，不展示段位变化。**
- 设计稿两联：左为**段位晋升庆祝页**（七段卡片横排，当前晋升到的段位彩色高亮 + 撒花，其余灰化，底部绿色 ➡️）；右为 `Last Week's Recap` 战报（`Last Week's Ranking` / `Completed Lessons` / `Cheers Received` / `Rewards +100` 四格 + `Claim Rewards` 按钮）。
- ⚠️ **顺序与正文相反**：埋点表定义 `app_tier_celebration_show` = 「**点击 Claim Rewards 后**弹出的晋升庆祝全屏页」，即 战报 → Claim Rewards → 晋升庆祝；正文写的是 晋升展示 → 点击 → 数据战报。

### 数据埋点（内嵌 Sheet，18 行 × 20 列；本期新增部分标注 2026/8/25–8/26）

**本期新增 / 改动**

| 事件 | 变更 | 属性 |
|---|---|---|
| `app_leaderboard_show`（排行榜页展示） | **新增参数** | `user_tier`：Cadet / Astronaut / Navigator / Captain / Commander / Admiral / Star Legend（用户当前段位） |
| `app_leaderboarduser_click`（点击他人头像看卡片） | **新增参数** | `viewed_user_tier`：同上枚举（被查看用户的段位） |
| `app_leaderboard_settlement_show`（上周战报展示） | **新增参数** | `tier_changed`：true/false（本周是否晋升）；`current_tier`：同上枚举（**无论是否晋升都上报**） |
| `app_tier_celebration_show`（**新增事件**） | 晋升庆祝页曝光 —— 点击 `Claim Rewards` 后弹出的晋升庆祝全屏页 | `new_tier`（晋升后段位）；`promotion_count`：int 1–6（**该用户第几次晋升**） |
| `app_tier_celebration_click`（**新增事件**） | 用户点击晋升庆祝页 `Continue` | `new_tier` |

**表内既有事件（V1.33 / V1.35 遗留，本期不变）**：`app_leaderboard_entrance_click`（`lastweekstatus` 上周是否参赛）、`app_overtake_animation_show`（`show_time` 今日第几次 + 2026/6/30 新增 `rank_status`：第1名 / 2~10名 / 11~20名 / 21~30名）、`app_overtake_animation_continue_click`、`app_leaderboard_like_click`、`app_leaderboard_settlement_click`（`buttom_name`：next/返回首页）、`leaderboard_group_locked`（**服务端**，满 20 真人或 24h 超时封组，记录封组原因 `real_users_full`/`timeout_24h` 与首位真人到封组耗时 ms）、`leaderboard_push_optin_show` / `leaderboard_push_optin_click`（`button_name`：allow/later）。

### ⚠️ 待确认（写用例前需拉齐）

1. **段位命名三套并存（最关键）**：img-01「修改版」已改成「学习之星 N 段 / TopStar LvN」且埋点枚举为数字 1–7，但正文、内嵌 Sheet1、埋点表枚举、所有设计稿仍是「训练生/宇航员/…/星际传奇」与 `Cadet…Star Legend`。**上线用哪套命名、埋点值是数字还是英文名，必须先定**，否则文案、TTS、埋点全对不上。
2. **机器人段位规则缺失**：正文写「机器人也需要增加段位，规则如下：」，后面接的却是个人形象卡截图，没有任何规则。机器人段位怎么分配（随机？跟随真人分布？固定档？）完全没写。
3. **战报与晋升庆祝的先后顺序冲突**：正文「晋升后展示段位晋升 → 点击 → 进入数据战报」vs 埋点「战报 → 点击 Claim Rewards → 晋升庆祝页」。
4. **分割线文案两版不一致**：排行榜页「以上可晋升下一段位」vs 主路径弹窗「前 10 名下周晋升下一段位」vs 正文「前 10 名下周晋级下一段位」。
5. **主路径弹窗榜单是否展示段位标签**：img-02 有、img-03 没有，而正文只说「主路径页面和排行榜入口页面都增加**分割线**」，没提标签。
6. **31 名及以后如何处理**：规则只写了 1–10 升级、11–30 不变，**未参赛或排名 31+ 的用户**段位如何处理（同样不变？还是不参与结算）没写。
7. **新用户初始段位未定义**：没写新用户默认是「训练生 / TopStar Lv1」还是无段位；未参赛过的用户在榜单里显示什么标签。
8. **「最快 6 周达到最高级」与七段位不自洽的边界**：从 1 段升到 7 段需要 6 次晋升，前提是初始为 1 段 —— 需确认初始段位定义（见上条）。
9. **段位与周榜结算的时序**：结算在「周一」，但没写晋升判定发生在结算瞬间还是用户下次打开 App 时；跨时区（用户本地时间 vs 服务端时间）如何处理。
10. **`promotion_count` 上限 1–6 的兜底**：若后续段位扩容或有重复晋升，超过 6 时如何上报。
11. **段位是否影响分组**：`leaderboard_group_locked` 显示排行榜是 20 真人一组，未写段位是否参与分组匹配（同段位分一组？），若不参与，高段位用户仍可能被分到弱组、继续无脑升段。
12. **无奖励是否会削弱动机**：明确写「不发放额外奖励」，Rewards 仍来自原战报（+100）—— 需确认段位只做身份标识、不接奖励中心。

## 图说明

共 5 张图，按 SKILL 规则（≤6 张）**全部读取**。

- [img-01](../raw/Top-learners排行榜优化：支持段位/images/img-01.webp)（1506×568）：**段位改名对照表（标题「修改版」）** —— 8 列：序号 / 旧命名(中文) / 旧命名(英文) / **新命名(中文)「学习之星 N 段」** / **新命名(英文)「TopStar LvN」** / 新命名(印尼语) / **埋点枚举值 1–7** / TTS 朗读稿(英文)「TopStar level one…seven」。内容见上文表格。
- [img-02](../raw/Top-learners排行榜优化：支持段位/images/img-02.webp)（1734×1054）：**排行榜页段位条 + 榜单** —— 顶部 tab `Top learners`（选中）/ `Streak`；段位条七段：训练生🎓 / 宇航员👨‍🚀 / 领航员🧭（三者绿圈=已达到）— 舱长🚀（紫圈=当前）— 指挥官 / 将军 / 星际传奇（灰=未达到）；「还剩 5 天，周一结算奖励」。榜单 1 Budi🇮🇩 指挥官 23 / 2 Sari 舱长 21 / 3 Minh🇻🇳 领航员 19 / 4 Adi 宇航员 17 / 5 Rina 领航员 16 / 6 Xiaoli🇨🇳 训练生 15 / **7 Me 舱长 14（紫色高亮行）** / 8 Dika 宇航员 13 / 9 Putri 训练生 12 / 10 Linh🇻🇳 训练生 11 —— **黄色虚线分割线「↑ 以上可晋升下一段位」** —— 11 Bayu 训练生 10 / 12 Dewi 训练生 8。
- [img-03](../raw/Top-learners排行榜优化：支持段位/images/img-03.webp)（1668×1006）：**主路径 / 入口页的排行榜弹窗版** —— 标题 `🏆 Top Learners`，左上 ×，右侧绿色 ➡️，左下兔子吹喇叭插画。行：8 Andi🇩🇪 3 Lessons / 9 Reza🇮🇩 3 / 10 Anna🇩🇪 2 —— **分割线「⬆ 前 10 名下周晋升下一段位」** —— 11 Tim 2 / **12 Lily(me)🇨🇱 2（蓝色高亮）** / 13 Andi🇨🇳 2。**行内没有段位标签**。
- [img-04](../raw/Top-learners排行榜优化：支持段位/images/img-04.webp)（1770×1058）：**个人形象卡** —— 弹窗内 Avatar 全身像 + `Dimas 🇨🇱` + `🏆 Lv 4` + **黑框标注的段位标签「宇航员」** + 点赞 `👍 252`；下方两格「本周课程数 🚩 13」「连胜天数 🔥 252」。背景为 Top Learners 排行榜页（`6 Days Left | Monday Rewards`、`Rules ⓘ`、领奖台 2/3 名、右侧榜单 27/18/17/15 Lessons、第 5 Dimas 9 Lessons、第 6 Tom 7 Lessons）。
- [img-05](../raw/Top-learners排行榜优化：支持段位/images/img-05.read.png)（原图 2258×568，副本 84%）：两联 —— 左「**段位晋升庆祝页**」：横排段位卡片（训练生 银色 / **宇航员 彩色高亮 + 撒花** / 领航员 灰 / 舱长 灰 / 指挥官 灰…），底部绿色 ➡️；右「**Last Week's Recap 战报**」：四格数据 `Last Week's Ranking 2`、`Completed Lessons 12`、`Cheers Received 7`、`Rewards +100`，主按钮 `Claim Rewards`，右上 ×。
