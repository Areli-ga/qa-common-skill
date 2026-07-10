---
标题: Miniplan改Phonics-AB测试
模块: Phonics / 主菜单入口与推荐路径
版本: V1.31.0
related: []
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/BTDzwj5yricAV6k0P09lLe3wgaf
日期: 2026-06-30
---

## 摘要

V1.31.0 做 Phonics 一级模块 AB 测试:实验组把主菜单原 Miniplan 入口替换为 **Phonics** 入口,将 Lv5-Lv10 既有自然拼读课程抽出为独立模块,支持 Alphabet / Sound Groups / Syllable Practice 三块内容、全开放无锁定、单推荐卡引导、状态同步与埋点扩展。产品 Owner: Cloud;优先级:高。✅ **版本已确认 V1.31.0**(主人确认,2026-07-01):文档「版本号」字段与 Figma 均为 **1.32.0**,但本库按 **V1.31.0** 入库。

## 功能信息(逻辑 / 状态 / 边界 / 字段)

### 1. 目标与 AB 范围
- 背景:家长希望有独立自然拼读模块;现有 Phonics 课程散落在 Lv6-Lv9/Lv10,低等级孩子难以直接接触核心拼读训练。
- 目标:主菜单一级展示 Phonics,让家长看懂学习结构与进度,孩子可按推荐路径继续学习,同时允许自由探索跳学;从主菜单到具体课程不超过 2 次点击。
- 内容复用:复用 Lv5-Lv10 现有 lesson / storybook / game 资产,不重复生产内容。
- **AB 规则**:
  - 对照组:展示原版 Miniplan 图标,点击进入 Miniplan 模块。
  - 实验组:展示新版 Phonics 图标,点击进入 Phonics 模块。
  - AB ID:`course_ab_phonics_entry`,走 admin 的 abtest 管理控制灰度。

### 2. 内容结构与上线范围
- 数据无需 admin 配置,按教研内容文档直接分类放置;标题和课程名称支持多语言。
- 结构:Stage - theme - step。
- **Stage 1 Alphabet**:A-Z 共 26 个字母主题,每字母 3 个活动;来源 Lv5-Lv9;本期上线。
- **Stage 2 Sound Groups**:5 个字母组主题,每组 7 个学习步骤;来源 Lv5-Lv9;本期上线。
- **Syllable Practice**:5 个主题 x 6 个活动 + 1-2 个主题绘本;来源 Lv5-Lv9;本期上线。
- **Stage 3/4/5 本期不显示**:
  - Stage 3 Short Vowels & CVC Words 不在进度链显示节点,不在屏内出现入口,推荐计算不涉及。
  - Stage 4 Digraphs & Common Long Vowels 不显示。
  - Stage 5 Advanced Long Vowels 不显示。

### 3. 导航与屏幕模式
- 顶部进度链是全屏共用一级导航,横向贯穿并常驻每个 Phonics 屏顶部。
- 节点点击直接切到目标屏,无中间页;当前节点高亮,下方展示当前 Stage 名。
- 滚动:用户向上滑主体内容时,顶部进度链上移渐隐;下拉到顶恢复。
- 节点与跳转:
  - `a-z Alphabet` → Stage 1 主屏。
  - `satph` / `crinm` / `delkf` / `goyjq` / `ubvwxz` → Stage 2 对应 Sound Group 主屏。
  - `Syllable Practice` → Syllable Practice 主屏。
- **Alphabet 屏**:A-Z 字母网格,每屏 4 个字母可见;每个字母单元展示字母标识(Aa/Bb/...) + 3 张课程卡,顺序为 Lesson → Letter Dot-to-dot → Storybook。
- **Sound Group 屏**:共 7 行,每行对应一个学习步骤;行内水平滚动展示该步全部活动 + storybook;行标题如 Learn the Letters / Trace the Letters / Hear the Sounds 等。
- **Syllable Practice 屏**:共 5 行,每行对应一个主题;主题为 Animals / Food / Transport / Musical Instruments / Toys,行内水平滚动展示该主题活动 + storybook。

### 4. 课程卡状态与推荐学习
- 状态仅 3 个:
  - `not_started`:默认未学习。
  - `recommended`:系统标记推荐学习。
  - `completed`:用户完成该 lesson 后。
- 全模块**无锁定状态**,所有 lesson 默认可点击。
- Phonics 模块内完成课程**不会获得星级**,也**不会同步到路径中**。
- Phonics 模块内首次完成课程可获得完课通用奖励 **20 Giggles**,也能激活终身学员打卡。
- 任意时刻模块内**有且仅有 1 张课程卡**被标记为 `recommended`。
- 推荐计算:
  - 同 Stage 续推:按用户上次在本模块完课所属 Stage 内的 Step 顺序 + 行内顺序,推荐下一张未完成 lesson。
  - Stage 1 全部完成 → 推荐 Stage 2 `satph` 第 1 步第 1 课。
  - Stage 2 全部完成 → 推荐 Syllable Practice `Animals` 第 1 课。
  - Syllable Practice 全部完成 → 推荐保持在最后一张已完成 lesson,不再推进。
  - 边界:若上次完课在 Sound Groups,但 Alphabet 未全部完成,仍按"上次完课所在 Stage"推进,不回退到 Alphabet。
- 起点:
  - 首次进入 Phonics:推荐 Stage 1 Alphabet 屏 Aa 的 Lesson 卡。
  - 已有学习记录:推荐上次记录的下一张未完成 lesson。
- 跳课不阻塞:孩子可不按推荐顺序、Step 顺序、Stage 顺序自由点击任意 lesson 进入学习;前序未做仍保持普通未学,不报错、不警告。

### 5. 后端与状态同步
- 后端本期需要支持 Phonics 课程状态记录/读取接口。
- 需记录并读取未完成/推荐/已完成状态,用于推荐路径计算与课程卡展示。

### 6. 数据埋点
- 新增 `scene=phonics`:所有从 Phonics 进入的 lesson / story / game 内容触发类事件都携带。
- Phonics 模块字段:
  - `phonics_stage`:scene=phonics 时必传;取值 `alphabet` / `sound_groups` / `syllable_practice`;预留 `short_vowels_cvc_words` / `digraphs_common_long_vowels` / `advanced_long_vowels`。
  - `phonics_theme`:scene=phonics 时必传;Alphabet 为 `a`-`z`,Sound Groups 为 `satph` / `crinm` / `delkf` / `goyjq` / `ubvwxz`,Syllable Practice 为 `animals` / `food` / `transport` / `instruments` / `toys`。
  - `phonics_step`:仅 `phonics_stage=sound_groups` 时必传,取值 1-7。
  - `phonics_lesson_status`:内容进入/完成/退出事件携带,取值 `not_started` / `completed`;完课埋点上报后才从 not_started 变为 completed,所以首次完课的进入埋点与完课埋点均上报 not_started。
  - `phonics_is_recommended`:内容进入/完成/退出事件必填,表示进入该内容时该 lesson 是否为 recommended。
- AB 分组字段:`course_ab_phonics_entry`,取值 `control` / `test`;对照组 Miniplan 与实验组 Phonics 的内容事件、`app_page_view` 都携带,用于按组拆分指标。
- 事件扩展:
  - `InteractiveLessonStart` / `LessonQuit` / `InteractiveLessonEnd`
  - `app_game_quit` / `app_game_complete`
  - `StoryBookStart` / `StoryBookExit` / `StoryBookComplete`
  - `app_page_view`:新增 `page_title=phonics`, `page_name=alphabet/sound_groups/syllable_practice`。

### 关联依赖(回归注意)
- 与首页主菜单入口相关:实验组替换 Miniplan,对照组仍保留原 Miniplan 入口。
- 与 AB 实验平台相关:`course_ab_phonics_entry` 走 admin abtest 灰度,需校验对照/实验组入口和埋点分组一致。
- 与数据埋点相关:同一批 lesson/story/game 原有内容事件只新增 Phonics 来源字段,不能影响非 Phonics 场景。
- 与奖励系统/终身学员计划相关:Phonics 内完课不发星级、不同步路径,但首次完课仍发通用 20 Giggles,且能激活终身学员打卡。

## 图说明

> 存于 `../raw/Miniplan改Phonics-AB测试/images/`(超大已转 `.read`)。5 张图按规则已全读。

- **img-01**(`images/img-01.read.png`):Alphabet 主屏示意。顶部进度链含返回按钮、`a-z Alphabet` 当前高亮、5 个 Sound Group 节点与 Syllable Practice 节点;正文为 Aa/Bb/Cc/Dd 字母网格,每字母下 3 张课程卡,卡片下方显示 Lesson name。
- **img-02**(`images/img-02.png`):顶部进度链局部。`satph` Sound Group 节点被黄色描边高亮,下方黄色标签显示 `Sound group`;左右分别连接 `a-z` 和后续字母组节点。
- **img-03**(`images/img-03.png`):Alphabet 屏另一版布局示意。顶部 `a-z Alphabet` 高亮,每行展示两个字母组(Aa/Bb、Cc/Dd),每个字母 3 张课程卡,用于确认每屏 4 字母可见。
- **img-04**(`images/img-04.read.png`):Sound Group 屏。顶部 Sound Group 节点高亮;正文按行展示 Learn the Letters / Trace the Letters 等步骤,每行内课程卡横向滚动,右侧可见下一张半露出的卡片。
- **img-05**(`images/img-05.read.png`):Syllable Practice 屏。顶部粉色拍手节点高亮并标注 `Syllable Practice`;正文按 Animals / Food 等主题分行,每行横向滚动展示活动卡。
