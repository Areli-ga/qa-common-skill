---
标题: Onboarding 流程引入中文
模块: 新用户引导 / Onboarding语言选择
版本: V1.36.0
related: [2026-08-11-奖励中心-家园好友串门社交测试.md, 2026-08-11-学习路径-解锁规则和学习顺序测试.md, 2026-08-11-竞技场-竞技场Arena1.0随机PK.md, 2026-08-24-学习路径-单元内连续学习与单元结算.md, 2026-08-24-新用户引导-Onboarding去掉选择语言.md, 2026-08-24-竞技场-游戏大厅2.0小游戏.md]
原链接: https://wsgh3q8mwfpp.sg.larksuite.com/wiki/RxQVwWjiXikoVrkVRdwl1Zs0gZc
日期: 2026-08-11
---

## 摘要

V1.36.0 新增**中文课**并在首页逐步放量:Onboarding 里插入一页**语言选择(English / Chinese)**,选英文走原有 L1–L10 体系与 Hello 课,**选中文则无论孩子多大都锁 Level 1**、加载后**直接进小Mai 中文首页**;家长中心新增**切换语言**按钮,**每个孩子的语言学习进度单独记录**。走 AB:对照组只有英语。

## 功能信息(逻辑 / 状态 / 边界 / 字段)

### 0. 背景与 AB

- 本次新增中文课,**在首页逐步放量,测试用户学习情况**。
- **AB 测**:
  - **对照组**:只有英语学习;
  - **实验组**:支持选择英文与中文。
- 对照组用于参考增加中文课程的数据影响;同时**用来控制放量的开关**,如果数据不好,可以**先只用少量数据测试**。
- UI:Figma **`1.36.0`** node `47001-33746`(与同版本注册登录优化同一 node)。

### 1. Onboarding 流程(逐页)

> 注:**启动页文案先不修改,后续全量再修改**。

**① 头像/年龄设置页**
- **整个启动流程的语言,基于用户系统设置语言展示**。
- 点击欢迎页的【**免费开始学习**】后进入此界面,**替换掉原本旧的选年龄页面**。
- **直接复用现在线上已有界面**;同时**要把头像的设置带去家园和主页**。

**② 语言选择页(新增,img-02)**
- 标题 `Which language would you like to learn?`;两张卡:
  - **English — `Learn as you play`**(默认选中,右上绿色 ✓);
  - **Chinese — `Learn as you chat`**。
- 选择后点击**下一步**;**点击返回:回到上一页**。
- 📌 两句副文案点出了两条产品线的差异:英文是**玩中学(主路径游戏)**,中文是**聊中学(小Mai 对话)**。

**③ 级别页**
- **英文(img-03)**:进入英文体系页面,**级别规则不变,仅 UI 调整**。展示 **L1–L10**(L1–L5 黄色:Letters / Listening / Speaking;L6–L10 绿色:Phonics / Early Writing / Early Reading),右侧「完成本级后孩子将掌握」**11 Letters / 8 Themes / 80 Vocabulary words / 16 Storybooks**。
- **中文(img-04)**:**中文的体系需要重新开发**,**无论用户设置多少岁,孩子都是在 Level 1**。展示 **L1–L7**(Listening / Speaking / **Characters**),右侧 **7 Levels / 57 Units / 150 Words & Phrases**,说明「Understands and responds in everyday scenes — greetings, introductions, and simple chats.」
- ⚠️ **设计稿与规则冲突(已入待确认)**:中文级别页(img-04)的「Your Child's Level」**箭头指向 L2**,与正文「中文无论多少岁都在 Level 1」矛盾;英文页(img-03)箭头同样指 L2,疑为**两张稿共用同一套占位素材**。
- 点击下一步 → 进入**资源加载页**。

**④ 资源加载页 → 进入首页**
- **英文路径**:展示 loading 和文案并**进入 hello 课,流程不变**。
- **中文课**:展示 loading 和文案并**进入中文首页**;**中文首页是直接启动小Mai**。
- ⚠️ 原文注明「**具体流程以 Libin 需求为准**」并 @Libin Liu 确认 —— 中文首页的具体行为**以 Mai 侧需求为准,本篇不是最终口径**。

### 2. 中英文首页

| | 说明 |
|---|---|
| **英文首页**(img-08) | **无变化**,仍保留**底部小Mai 入口**,进入后进**英文版的小Mai**,**小Mai 对话说英文**(@Libin Liu) |
| **中文首页**(img-09) | **中文首页就是小Mai**(对话界面);**左上角新增一个家长中心** |

### 3. 家长中心切换语言

- **家长中心增加一个按钮,可以切换语言**;
- **切换语言后,直接进入到对应首页**;
- **每个孩子学习某种语言的进度单独记录** —— **A 孩子在学中文,切换到 B 孩子后,B 孩子默认选英文**;
- **增加孩子的流程**:1. 设置孩子信息;2. **选择学习语言**。

### 4. 数据埋点(内嵌 Sheet,6 个事件)

| 模块 | 事件名 | 触发位置 | 属性 | 值 |
|---|---|---|---|---|
| Onboarding-设置孩子 | `onboarding_child_setup` | 头像/年龄设置页完成设置后**点击下一步进入语言选择页**时 | (无) | — |
| Onboarding-语言选择 | `onboarding_language_click` | 语言选择页**选择语言后点击下一步** | `onboarding_language` | **`en` / `zh`** |
| Onboarding-级别确认 | `onboarding_level_confirm` | 级别页(英文级别页 / **中文 Level1 锁定页**)点击下一步**进入资源 loading 时** | `onboarding_language` | `en` / `zh` |
| 新增孩子-设置孩子信息 | `add_child_info_submit` | 新增孩子流程设置孩子信息(头像/昵称/年龄等)后点击下一步 | (无) | — |
| 新增孩子-语言选择 | `add_child_language_click` | 设置孩子信息完成后,语言选择页点击下一步 | `onboarding_language` | `en` / `zh` |
| 家长中心-语言切换 | `parent_center_lang_switch` | 家长中心**点击切换语言按钮** | `onboarding_language` | **切换后的目标语言** |

- 埋点新增日期列为序列值 `46230`。
- 备注两条:`onboarding_child_setup` **复用现有选年龄页逻辑**,若线上已有对应埋点建议 RD 直接复用,**此处先占位保证页面顺序完整**;`add_child_info_submit` 因 **PRD 未列具体信息字段**,待补充后再扩展属性。
- 📌 埋点表把中文级别页明确称作「**中文 Level1 锁定页**」,可作为「中文锁 Level 1」这一规则的旁证(与设计稿箭头指 L2 相悖)。

### 关联依赖(回归注意)

- **替换了旧选年龄页**,直接影响 [修改孩子年龄](2026-06-30-账号与设置-修改孩子年龄.md) 与 [Onboarding价值传递](2026-06-30-新用户引导-Onboarding价值传递.md) 的首启链路;**头像设置要带去家园和主页**,涉及 [奖励中心2.0虚拟形象装扮](2026-06-30-奖励中心-奖励中心2.0虚拟形象装扮.md) 与家园。
- **同版本 [注册登录优化](2026-08-11-账号与设置-注册登录优化V136.md)** 用的是同一个 Figma node,且同样改家长中心区域(未登录 Sign in 角标 vs 中文首页左上新增家长中心)—— **两篇的入口位置要对齐**。
- **中文首页 = 小Mai** 意味着中文用户的主路径就是 [Mai主对话界面](2026-06-30-AI%20Tutor-Mai主对话界面.md);V1.35 的 [破冰仪式](2026-08-11-AI%20Tutor-小Mai新用户入场破冰仪式.md)(img-09 气泡正是破冰后的中文首句)、[新内容更新引导](2026-08-11-AI%20Tutor-小Mai新内容更新引导.md)、[全局单词本 Quiz](2026-08-11-AI%20Tutor-Mai基于全局单词本生成Quiz.md) **在中文语境下是否全部适用,需要逐条确认**。
- **英文首页的小Mai 说英文、中文首页的小Mai 说中文** —— 与 [模型切换配置](2026-08-11-AI%20Tutor-小Mai模型切换配置.md) 的 TTS 供应商/音色、[音频库多语言](2026-06-30-音频库-单词短句多语言音频库.md) 的语种覆盖直接相关。
- **每个孩子语言进度独立**,与 [解锁规则和学习顺序测试](2026-08-11-学习路径-解锁规则和学习顺序测试.md)、[老用户路径迁移](2026-08-11-学习路径-老用户路径迁移.md) 的进度存储结构耦合:**切孩子/切语言后进度不能串**。
- 本期是**第三个并行的首页级 AB**(继 `homepage_learning_order`、`homepage_toplearners` 之后),分层见 [AB实验平台](2026-06-30-AB实验平台-AB%20Test优化.md);⚠️ **本篇未给出 AB key**,需补。
- 中文课属于新内容体系,与 [课程本地化 / 翻译开关引导](2026-06-30-课程本地化-翻译开关引导.md) 的多语言展示不是一回事(那是 UI 翻译,这是学习语种),**勿混淆**。

## 图说明(10 张,按规则只读关键图)

> 存于 `../raw/Onboarding-流程引入中文/images/`(超大图已转 `.read`)。

- **img-02**(`images/img-02.read.png`):**语言选择页(本期新增)**。浅蓝圆角卡,左上返回箭头、右上蓝色箭头「下一步」;标题 `Which language would you like to learn?`;两张选择卡——左 **English `Learn as you play`**(浅绿底、右上绿色 ✓ 选中态),右 **Chinese `Learn as you chat`**(白底未选中);右下角蓝兔吹泡泡插画。
- **img-03**(`images/img-03.read.png`):**英文级别页**。左侧「Your Child's Level」柱状阶梯 **L1–L10**:L1–L5 黄色系(标签条 `Letters / Listening / Speaking`)、L6–L10 绿色系(标签条 `Phonics / Early Writing / Early Reading`),**黄色箭头指向 L2**;右侧「After completing this level, the child will know」卡片:**11 Letters / 8 Themes / 80 Vocabulary words / 16 Storybooks**(各带绿色 ✓)。
- **img-04**(`images/img-04.read.png`):**中文级别页**。同版式,阶梯为 **L1–L7 全黄色系**(标签条 `Listening / Speaking / Characters`),**箭头同样指向 L2**(⚠️ 与"锁 Level 1"冲突);右侧卡片:**7 Levels / 57 Units / 150 Words & Phrases**,并附说明「Understands and responds in everyday scenes — greetings, introductions, and simple chats.」
- **img-08**(`images/img-08.webp`):**英文首页(无变化)**。绿色主路径地图,左上家长中心头像 + `学习中心` 胶囊,右上素材/排行榜/商店(Giggles 999);路径依次 Hello → 路牌 `Lv 1 Unit 1 Colors introduce` → Introducing Colors / Color Match / Color Speaking / Unit Rev…,每个课程圆圈带黄星;右下角小Mai 头像(**底部小Mai 入口**)。
- **img-09**(`images/img-09.read.png`):**中文首页 = 小Mai 对话界面**。深紫场景,**左上角新增家长中心图标**(本期新增);小Mai 睁眼 + 气泡「是谁把我吵醒了呀?我是小Mai,你可以告诉我你的名字吗?我们可以做好朋友。」;右上用户头像 + 麦克风;中央 ABC 主题岛屿,左右两侧为上锁的其他岛屿。
- 其余存档不逐张读:img-01(头像/年龄设置页)、img-05/06/07(英文与中文的资源加载页、英文首页局部)、img-10(家长中心切换语言按钮)。
