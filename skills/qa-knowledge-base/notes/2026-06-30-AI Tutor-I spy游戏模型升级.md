---
标题: I spy - at home 游戏模型升级
模块: AI Tutor / I spy游戏
版本: V1.31.0
related: [2026-06-30-AI Tutor-Mai主对话界面.md, 2026-06-30-AI Tutor-单图对话多玩法与单词记忆系统.md, 2026-07-13-AI Tutor-Mai场景内口语对话课.md, 2026-07-13-AI Tutor-Mai引导交互优化.md, 2026-07-13-AI Tutor-学习场景屏幕常亮.md]
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/UFbtwfVfgiGBmwkNaUvliKqagBh
日期: 2026-06-30
---

## 摘要

V1.31.0 把「I spy - at home」AI 找物游戏迁移到新 AI tutor 技术方案:**Live 对话 → 流式输出**、**全开麦 → 点击发送**、**Memory 升级**(记累计学过单词/用户喜好/学习报告)、等级词汇表(L1–L3)与升降级策略、仪式感离别感言。本期做 I spy 游戏迁移;**Mai 主对话界面为二期需求**。AI 助手角色为 **Mai**,保留 Max 形象。

## 功能信息(逻辑 / 状态 / 边界 / 字段)

### 技术方案升级
- 从 Live 对话 → **流式输出**;Sidecar 朗读/高亮/缩放保持一致;Admin 后台配置支持**图片直接作为 LLM 输入**(降运营成本)。
- DoD:按既定规则玩、**过程无 AI 幻觉 bug**;离别感言;多次进入记忆完备、按线性学习顺序续学、**学过词汇不重复**。

### 玩法升级(Prompt 层已调试)
- 告诉 AI 故事情节,AI 理解并作为 **rounds 转场**;按等级词汇表(L1/L2/L3)约束,猜词顺序遵从当前等级单词表顺序。
- **等级升降级策略**(用户等级是系统内标记,**界面无等级概念**):
  - **升级**(任一触发,最高 L3):用户主动反馈太简单;或**连续 3 轮在首次就猜对**。
  - **降级**(任一触发,最低 L1):用户主动反馈太难;或**连续 2 轮均在 3 次提示内无法猜对**。
- **3 次猜测机会(线索递增强化)**:①所在空间 + 首字母 → ②颜色描述 → ③详细物品参数。第二/三层提示需**带上之前线索**(一句话里线索逐渐变多)。
- **聚焦和高亮**:揭晓第 3 层线索时聚焦;揭晓答案后聚焦 + 高亮。
- 用户朗读完 → 俏皮故事情节收尾并开下一轮;不同等级朗读句不同(低:`I can see a bird`;中:`I spied a red bird on the roof`;高:加故事情节)。

### 交互优化(测试重点)
- **退出**:遵从"用户口述:我要离开"。仪式感离别(大模型驱动):向 GPT 发"我想离开"→ 播 Max 离别动画 + GPT 文案 → 播完关游戏回入口。**提供跳过按钮**(感言播完前立即终止 Mai 音频直接退出)。
- **切后台**:暂停音频;**回前台**:点 Mai 重新生成最近一轮对话,智能体给点击反馈(不过激),经 LLM 回主对话;点麦克风也可主动发起对话。

### Memory 总结流程(关键)
- 因技术方案改为点击发送:离开对话/游戏时**静默总结 memory**。
- ⚠️ **严谨总结流程**:总结过程中用户再次点入口 → **必须先执行完上次 memory 总结,再加载 memory 应用到下次对话,不可跳过 Mai 总结直接进游戏**(先总结上次 → 再初始化下次)。忽略用户异常关闭导致的 Memory 丢失。
- **Memory 结构**:`user_profile`(name/addressing_preference)、`learning_memory`(heard_words / successfully_repeated_words / attempted_words / not_repeated_words)、`play_preference`(likes/dislikes/preferred_gameplay/interaction_style/speaking_confidence/next_strategy)、`freeform_facts`、`word_state`(每词:word / source=curriculum\|ad_hoc / introduced_at / last_seen_at / mastery / due_at / success_count / attempt_count / today_seen_count / today_success_count / last_seen_day / recent_session_days / promotion_candidate)。

### Admin
- Prompt 配置:Mai prompt、I spy 游戏 prompt。

## 图说明(1 张,全读)

> 存于 `../raw/I-spy---at-home-游戏模型升级/images/`。Figma + 多个 Demo(Mai/svg-morph/voice-tutor)见原文档。

- **img-01**(`images/img-01.png`):**I spy at home 游戏场景**。房子剖面(多房间:卧室/厨房/客厅/浴室等,藏有可找物品),底部 Max 角色,左上返回、右上退出 X、右下绿色麦克风/发送按钮。
