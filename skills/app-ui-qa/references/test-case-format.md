# Test Case Format

Use the case as the source of truth. The automation route should not invent scope from the visible app.

## Contents

- Source conversion and bundled Giggle Academy cases
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
