---
标题: Mai - 加入主对话界面，提供点击互动
模块: AI Tutor / Mai主对话
版本: V1.32.0
related: [2026-06-30-AI Tutor-I spy游戏模型升级.md, 2026-06-30-AI Tutor-单图对话多玩法与单词记忆系统.md, 2026-07-13-AI Tutor-Mai场景内口语对话课.md, 2026-07-13-AI Tutor-Mai引导交互优化.md, 2026-07-13-AI Tutor-学习场景屏幕常亮.md, 2026-07-13-语音识别-自适应跟读计时与会话统计.md]
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/HvVTwuYwaiexYIkUMbolXFqSgC8
日期: 2026-06-30
---

## 摘要

V1.32.0 新增 **AI Tutor 主对话界面**:App 右下角 Mai 入口进入独立对话页,承载语音对话、Mai v2 极简兔子形象反馈、白天/黑夜主题、I Spy 游戏入口与主/子 Prompt 切换。本期把 Mai 从 I Spy 游戏内陪伴角色升级为独立英语启蒙智能体,支持 reaction / interaction / 变形 / 变色 / SVG Morph、点击彩蛋、Memory 学习进度存储,并将 I Spy 游戏内原 Max 形象替换为 Mai。产品 Owner:Libin;优先级:高。

## 功能信息(逻辑 / 状态 / 边界 / 字段)

### 1. 入口与主流程
- App 右下角通过 **banner 配置静态图**展示 Mai 入口,点击后进入「AI Tutor 对话页面」。
- 进入后先展示加载页:Mai 处于 **sleep** 状态,资源加载中也可点击 Mai 触发 interaction。
- 若加载完成时抖动/眩晕动画仍在播放,需等待动画播完再进入对话页。
- Greeting 按 Admin 配置展示,需区分新用户 / 老用户欢迎策略。
- 进入对话后:
  - 麦克风自动激活,也支持点击手动启用。
  - 用户语音可自动结束或点击提交。
  - 用户提交新语音可打断 / 中止当前 AI speech。
  - Mai 流式输出语音,气泡展示最新一句话。
  - Memory 记录学习进度。
- 退出主对话时,主 Prompt 对今日学习成果做动态总结,给出简短离别感言后关闭。

### 2. 页面结构与交互规则
- 左侧为 Mai 展示区:遵循 v2 极简兔子行为,支持 reaction / interaction / 高阶变形 / SVG Morph / play word game。
- 右侧为用户区:展示 user 子账号头像;用户语音不显示为文本,文本框内为麦克风启用按钮。
- 气泡规则:
  - 只显示需要被读出的内容,系统指令必须过滤。
  - 流式加载。
  - 最多显示 4 行,超过后支持手指滑动查看。
- 全局彩蛋:
  - 单击 Mai → 抖动。
  - 快速连续点击 → 眩晕彩蛋。
  - 眼球跟随。
- 主题支持白天 / 黑夜。原文未展开切换方式,测试时按实现覆盖自动 / 手动表现。

### 3. I Spy 游戏入口与 Prompt 切换
- 底部仅开放一个游戏入口:**I Spy with My Little Eye - at home**;其他未来内容入口置灰。
- 点击 I Spy 入口后切换 Prompt,加载并运行 I Spy at home 关卡。
- I Spy 游戏内 Mai 形象替换原 Max,并同样支持单击抖动、连续点击眩晕、眼球跟随。
- 游戏 greeting 需自然承接主对话上一句。
- 退出 I Spy 后返回主对话界面,切换回主 Prompt,由主 Prompt 对游戏结果进行评价。

### 4. AI / Prompt / Memory
- Mai 由 AI 驱动,提供主 Prompt 与子 Prompt,并定义主/子 Prompt 的切换方式。
- Admin 后台升级:
  - 拆分 I Spy 游戏 prompt 为 main prompt 和游戏内 prompt。
  - 拆分 Memory 为用户基本信息、游戏进度、单轮次对话报告总结。
  - 支持主 Prompt 配置、加载动画配置、欢迎策略配置。
  - 单词卡支持单词矢量图形配置(非必填)。
- 对话输出执行 Admin Prompt 配置,并按 Prompt 配置写入 Memory。
- 需支持唤起 Sidecar 的朗读功能与 Mai 变形能力。

### 5. 验收重点
- 点击右下角 Mai 入口能进入 AI Tutor 对话页。
- 加载态、抖动、眩晕彩蛋、眼球跟随符合 v2 极简兔子设计。
- 语音输入可启用 / 提交 / 打断,AI 流式语音输出与气泡同步。
- 气泡过滤、4 行溢出、滑动查看规则生效。
- 新 / 老用户 Greeting 按 Admin 配置正确区分。
- I Spy 入口能切换 Prompt 并进入 at home 关卡,游戏内 Mai 已替换 Max。
- 学习进度能正确写入并从 Memory 读取。
- 白天 / 黑夜主题、Admin 端 Prompt / 动画 / 欢迎策略配置均生效。

### 6. 数据埋点
- 背景:此前只有 I Spy 游戏一种对话类型,本期新增 Mai 主对话类型,需统计主对话 PV/UV、留存、进入率、I Spy 学习深度、互动彩蛋触发 PV/UV。
- 新增事件 **`mai_interaction`**:
  - 触发:用户触摸 Mai 触发互动彩蛋,且客户端成功执行单击抖动 / 连续点击眩晕时,每次触发上报一次。
  - 字段:
    - `session_id`(必填):本次会话 ID,与 `StartTalkScene` 一致。
    - `conversation_type`(必填):`main_chat` / `game`。
    - `interaction_type`(必填):`single_tap_shake` / `multi_tap_dizzy`。
    - `page_state`(必填):`loading` / `running`。
- 历史事件扩展字段 **`conversation_type`**:
  - `StartTalkScene`:进入 Talk Scene 页面时上报,用于区分 Mai 主对话与游戏两类对话的 PV/UV、进入率、留存。
  - `EndTalkScene`:退出 Talk Scene 页面时上报,用于分析有效时长、对话轮次、退出方式;学习深度明细在 memory 字段。
  - `TalkSceneAction`:AI 产生一次 action 且客户端成功执行时上报,用于分析两类对话下 AI 多模态动作触发与执行。
- 原文备注:可评估是否新增独立游戏 `scene_id`,以便未来拓展更多游戏入口;本期按实际埋点方案验收。

### 7. 兼容与多语言
- 多语言:界面文案 / Greeting 需支持多语言。
- 数据兼容:新老数据兼容;I Spy 游戏内 Max → Mai 替换不能影响存量已学习数据与进度。

### 关联依赖(回归注意)
- 与「I spy - at home 游戏模型升级」强相关:上一期 I Spy 迁移到 AI Tutor 技术方案,本期把 Mai 主对话界面上线并替换游戏内 Max。
- 与「数据埋点 - App 神策全埋点」相关:本期在既有 Talk Scene 埋点上扩展 `conversation_type`,并新增 `mai_interaction` 自定义事件。
- 与「语音识别 / 录音组件」相关:主对话依赖自动激活麦克风、手动启用、提交与打断当前 AI speech。
- 与「素材库 / 音频库」相关:Admin 侧涉及动画、欢迎策略、Prompt、单词矢量图形、朗读与多语言资源配置。

## 图说明

无图(0 张)。文档含 6 个表格:**基本信息**、**资源列表**、**需求范围**、**流程说明**、**规则/逻辑详述**、**其他功能需求**;关键信息已并入上文。Figma / Demo / Prompt / 动画参数等资源链接见原文档。
