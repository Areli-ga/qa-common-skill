# QA Common Skills

QA 内部 Codex skills 仓库。

## Skills

| Skill | 用途 |
| --- | --- |
| `app-ui-qa` | 复合技术栈移动 App 的双端 UI 冒烟自动化。Android 使用 adb-only；iOS 使用 iPhone Mirroring + PyAutoGUI；输出截图证据和 HTML 报告。 |
| `qa-testcase-design` | 根据 PRD/提测范围设计中文测试用例、覆盖方案与 PlantUML 思维导图 ，一键发布到飞书文档 |
| `qa-knowledge-base` | 飞书 PRD 录入 QA 知识库；写用例前检索历史需求、回归点、埋点，支持录入与检索 |

## Install

在 QA 成员自己的机器上安装：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Areli-ga/qa-common-skill \
  --path skills/app-ui-qa
```


如果本机 `$CODEX_HOME` 不是默认路径，按实际 Codex skill-installer 路径执行。安装后重启 Codex。

## Update

更新本仓库中的 skill 后，使用方可以删除本地旧 skill 再重新安装：

```bash
rm -rf ~/.codex/skills/app-ui-qa
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Areli-ga/qa-common-skill \
  --path skills/app-ui-qa
```

## Notes

- 不提交真实账号密码、API key、测试报告截图、设备日志或运行产物。
- 冒烟 case 已随 `app-ui-qa` 放在 `skills/app-ui-qa/assets/cases/`。
- 如需新增 QA skill，放在 `skills/<skill-name>/`，每个 skill 目录必须包含自己的 `SKILL.md`。
