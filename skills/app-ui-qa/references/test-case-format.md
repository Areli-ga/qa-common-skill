# Test Case Format

Use the case as the source of truth. The automation route should not invent scope from the visible app.

## Contents

- Source conversion and three bundled Giggle Academy execution types
- New-feature Markdown conversion and traceability
- Top-level JSON and step shapes
- Conversion guidance and secrets
- Example requests

Read the selected Markdown case in full before using its JSON companion. Scope boundaries, general prerequisites, recovery rules, exclusions, and per-step notes are mandatory operating context; do not rely on `SKILL.md` or step JSON alone.

When the source is Excel, Markdown, TestRail, TAPD, Jira, a mind map, or a Chinese manual test document, first convert it into a readable checklist, then optionally into JSON.

For image-only mind maps, record:

- Included modules.
- Excluded modules.
- Unclear nodes.
- Manual/owner-input steps.
- Known route risks.

For Giggle Academy, the current main smoke draft is:

- Checklist: `assets/cases/giggleacademy-main-smoke-v0.1.md`
- JSON: `assets/cases/giggleacademy-main-smoke-v0.1.json`

For Giggle Academy Android channel package smoke:

- Checklist: `assets/cases/giggleacademy-android-channel-smoke-v0.1.md`

For Giggle Academy new-feature exploratory testing:

- Fixed execution rules: `assets/cases/giggleacademy-feature-exploratory-v0.1.md`
- Converted feature documents: `assets/feature-executions/`
- Conversion template: `assets/feature-executions/feature-execution-template.md`
- Asset registry: `assets/feature-executions/INDEX.md`

Feature test cases are mandatory; requirements are optional. Read the supplied XMind, Excel, Markdown, image, test-management page, or authenticated URL completely before conversion. Use the user's signed-in Chrome session for authenticated URLs and Computer Use for desktop-only UI when needed. Keep source access read-only.

## New-Feature Markdown Shape

Create the converted document before operating the App. Save it as:

```text
assets/feature-executions/<YYYY-MM-DD>-<feature-slug>-v<major>.<minor>.md
```

Use the same executable table shape as main smoke:

```markdown
| ID | 用例点 | 操作 | 预期 | 备注 |
| --- | --- | --- | --- | --- |
| F01-01 | ... | ... | ... | 原始编号 / 节点路径：... |
```

Required source cases use module-continuous `F` ids such as `F01-01`, `F01-02`, and `F02-01`. Agent-added exploratory checks use separate `E` ids such as `E01-01`. Do not include `E` rows in required-case pass-rate calculations.

The document must include:

- Source and optional requirement links/files.
- Build, platform, server environment, scope, and exclusions.
- User-prepared first-case scene, account/data/flags, special entry, and post-restart re-entry path.
- Formal `F` cases, bounded exploratory `E` checks, and global checkpoints.
- A traceability table from every original id/node path to one or more converted ids.
- Ambiguities, manual steps, destructive-action boundaries, and report focus.

Preserve original intent and expected results. Do not silently omit or merge source cases. Mark unknown expected values `待使用者确认` instead of inventing them.

## Top-Level JSON Shape

```json
{
  "version": "1.0",
  "name": "release-smoke",
  "description": "Optional human description",
  "platform": "android",
  "app": {
    "android": {
      "packageName": "com.company.app",
      "activityName": "",
      "launcher": "adb"
    },
    "ios": {
      "bundleId": "com.company.app",
      "launcher": "iphone-mirroring-pyautogui"
    }
  },
  "runtime": {
    "defaultTimeoutMs": 90000,
    "language": "zh-CN",
    "skipVoiceByDefault": true
  },
  "testData": {},
  "globalChecks": [],
  "steps": []
}
```

Keep Android and iOS identifiers in one case file when the business flow is shared.

## Step Shape

```json
{
  "id": "stable-kebab-case-id",
  "type": "action",
  "title": "Short human-readable title",
  "objective": "Why this step exists",
  "action": "What Codex should do through visible UI",
  "expected": "What must be visible or true afterwards",
  "riskSignals": ["Things to actively watch for"],
  "severity": "blocker",
  "platforms": ["android", "ios"],
  "timeoutMs": 90000,
  "continueOnFailure": false,
  "data": {}
}
```

Supported `type` values:

- `setup`: entry blockers, permissions, onboarding, login preparation.
- `action`: perform a user workflow.
- `checkpoint`: inspect a state and report risks.
- `assert`: verify a visible expectation with minimal interaction.
- `voice`: speech-recognition coverage, skipped unless an audio strategy is approved.
- `manual`: documented but not automated.
- `teardown`: return to a stable state.

## Conversion Guidance

- Preserve business intent and expected result.
- Split report-critical clicks, swipes, drags, inputs, page entries, completions, and returns into separate rows.
- Split steps at risk boundaries: login, entering Unity, opening H5/WebView, permissions, payment/destructive actions, and completion recovery.
- Use visual language: labels, colors, icons, position, screen region, and expected copy.
- Use `riskSignals` for known historical issues and UX concerns.
- Use environment variable names for secrets instead of raw passwords.
- Mark voice, payment, destructive account changes, and production-side effects as `manual` or guarded steps unless the test environment is safe.
- For lesson flows, prefer one step per visible interaction such as entering a lesson, tapping a target object, dragging/swiping, confirming completion, and returning home.

## Runtime Data and Secrets

Any key ending in `Env` names a local environment variable. The value can be used during the live test only after the user has authorized that account/data entry for the app.

Example:

```json
{
  "testData": {
    "account": {
      "usernameEnv": "APP_QA_USERNAME",
      "passwordEnv": "APP_QA_PASSWORD"
    }
  }
}
```

Do not write raw secrets into reports, prompts, screenshots, or shared case files.

## Example Requests

- "Convert this smoke checklist into app-ui-qa JSON for Android and iOS."
- "整理这个思维导图，只保留故事书模块及以上的冒烟范围。"
- "Run S12-S17 through Android adb-only and produce an HTML report."
- "Run the iOS iPhone Mirroring PyAutoGUI route for this case and flag route-specific risks."
- "读取我已登录 Chrome 中的新功能用例页面，转成 F/E 编号执行文档；我准备好 QA 环境入口后再开始验证。"
