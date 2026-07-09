# Reporting Guide

Visual automation runs are manual-evidence runs. The report must be based on the visible app state, saved screenshots, ADB/Logcat evidence when available, iPhone Mirroring/PyAutoGUI evidence when available, and the active case.

## Required Artifacts

Keep these files together in a run directory:

- `report.md`: editable/source report.
- `report.html`: browser-readable report with screenshots rendered inline.
- `screenshots/`: original evidence screenshots.
- Optional `logs/`: ADB/Logcat or other local diagnostic snippets.

Render HTML from Markdown:

```bash
node scripts/render-manual-report.mjs runs/smoke/report.md runs/smoke/report.html
```

## Evidence Policy

- The report must show the full operation path, not only failed or risky steps.
- Save screenshots before and after every key click, swipe, drag, input, page entry, completion state, recovery action, and final state.
- Always attach screenshots for blocked, failed, needs-review, and UX-risk steps.
- Attach screenshots for key pass checkpoints such as login success, home, lesson entry, WebView load, story playback, completion, and returned home.
- For log-only risks, quote a short log fragment and point to the saved log file.
- For skipped voice/manual coverage, state why it was skipped and who should verify it.
- If password entry causes a black/hidden projection screen only while the password field or input bar is active, classify it as secure-input/projection protection. Report the handling path: enter password, hide keyboard/input bar, capture the masked-password state, and continue.
- If a precision control such as handwriting/tracing blocks automation, report it as `自动化阻塞 / 需人工复核` unless there is independent evidence that the app itself is broken.
- If the app auto-enters the next course/content after completing a listed course, include the auto-entered screenshot and the recovery path. Classify it as normal auto-advance/recovery unless the app cannot exit, loops, crashes, or blocks later cases.

## Final Report Structure

1. Scope: build, platform route, device/window, account handling, case file, run time.
2. Overall conclusion: pass, blocked, pass with risks, or inconclusive.
3. Case status table: one row per case id or module.
4. Operation path screenshots: ordered evidence with short captions.
5. Confirmed failures: severity, evidence, expected vs actual, reproducibility.
6. Possible risks: suspicious but unconfirmed anomalies, UX concerns, flaky timing, route limitations.
7. Skipped coverage: voice, real-device-only items, destructive flows, unavailable account states.
8. Follow-up recommendations: retest data, logs needed, owner suggestions, release impact.

## Status Meaning

- `通过`: observed expected state and no release-relevant gaps for that case.
- `带风险通过`: main path works, but route limits, timing instability, logs, or UX signals need review.
- `阻塞`: required path cannot continue, app crashes, login blocks, or data/account state prevents execution.
- `自动化阻塞 / 需人工复核`: app may be usable, but the selected automation route cannot reliably complete the control.
- `未执行`: the step was not operated.
- `不适用`: out of current case scope or intentionally removed.

## Risk Taxonomy

- `blocker`: cannot enter app, cannot login, crash, core flow unusable, data loss.
- `major`: important feature broken, repeated loading failure, layout prevents use, WebView/Unity/Flutter rendering defect.
- `normal`: recoverable issue, confusing copy, intermittent delay, non-critical visual defect.
- `minor`: polish issue, low-risk copy/layout problem.

## Review Checklist

- Confirm the report's screenshots match the platform route and device/window claimed in the scope.
- Confirm every failed or blocked row has a screenshot.
- Confirm the operation path is reproducible without reading chat history.
- Confirm Android screenshots/logs are bound to the same serial.
- Confirm iPhone Mirroring limitations are called out separately from product defects.
- Confirm skipped voice/manual steps are acceptable for the current release gate.
