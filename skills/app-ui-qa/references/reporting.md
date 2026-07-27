# Reporting Guide

Visual automation runs are manual-evidence runs. The report must be based on the visible app state, saved screenshots, ADB/Logcat evidence when available, iPhone Mirroring/PyAutoGUI evidence when available, and the active case.

## Contents

- Required artifacts and standalone rendering
- QA Web upload contract
- Evidence policy and final report structure
- Status meaning and risk taxonomy
- Review checklist

## Required Artifacts

Keep these files together in a run directory for source evidence and audit:

- `report.md`: editable/source report.
- `report.html`: self-contained browser-readable report. It must remain complete when copied or uploaded without `screenshots/`.
- `screenshots/`: original evidence screenshots.
- Optional `logs/`: ADB/Logcat or other local diagnostic snippets.

Render HTML from Markdown:

```bash
node scripts/render-manual-report.mjs runs/smoke/report.md runs/smoke/report.html
```

The renderer must inline every local screenshot as a `data:` URI. It prefers WebP at quality 76 and a maximum width of 1280 pixels, then falls back to the original PNG/JPEG/GIF/SVG bytes when no WebP converter is available. Both paths produce one portable HTML file.

Install the optional `sharp` dependency once on a QA runner to guarantee the preferred WebP path:

```bash
npm install --prefix /path/to/app-ui-qa --omit=dev
```

Optional rendering controls:

```bash
node scripts/render-manual-report.mjs report.md report.html \
  --image-quality 72 \
  --max-image-width 1080

node scripts/render-manual-report.mjs report.md report.html \
  --image-format original
```

Use `--no-inline-images` only for local renderer debugging. Do not upload that output to QA Web.

The default renderer must fail when a referenced local image is missing or when an `http:` / `https:` image remains. Treat this as a report build failure rather than publishing a partially broken report.

## QA Web Upload Contract

- Upload only `report.html` for viewing. Keep `report.md`, `screenshots/`, and logs in the run archive for traceability.
- Allow `data:` in the viewer's image content-security policy, for example `img-src data:`. If the report document receives a CSP, also permit its bundled inline stylesheet with `style-src 'unsafe-inline'`; no script permission is required.
- Render uploaded reports in a sandboxed iframe or on an isolated origin. The bundled renderer emits no JavaScript, but uploaded HTML should still be treated as untrusted content.
- Do not rewrite, sanitize away, or proxy `data:image/...;base64,...` values.
- Preserve UTF-8 and serve with `Content-Type: text/html; charset=utf-8`.
- Enable gzip or Brotli for HTML responses. Base64 increases the stored HTML size, while transport compression recovers much of that overhead.
- Set an upload-size limit based on real reports. The renderer prints source image bytes, embedded image bytes, and final standalone HTML size after every build.

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
- If a case is blocked, include the original blocked state and every attempted recovery checkpoint. Update the HTML report while continuing the run so evidence is not lost.
- A blocked case does not automatically mean the package is defective. Separate confirmed product failures, recoverable App-state risks, account/data prerequisites, network issues, and automation-route limitations.
- After a safe App restart or other recovery, continue every later case that remains reachable. Mark only cases whose prerequisites remain unavailable as blocked.
- If main-smoke S02 requires restart, show why: the pre-restart screen, attempted in-page actions, elapsed wait, expected/actual state, restart evidence, and post-restart state. If the one-time onboarding entry disappears, mark S02 incomplete/blocked for that run but continue downstream coverage; reinstall or clear data again only for a dedicated S02 retest.
- For iOS scope that includes S02, record whether the user prepared a fresh, not-yet-launched TestFlight installation before automation. If it was not ready, record that automation was deferred rather than treating S02 as an App failure.
- When iOS S02 is supplemented after downstream coverage, show the ordering explicitly: S03 and later reachable cases on the original installation, user-confirmed uninstall/TestFlight reinstall, download/build verification, then the separate S02 retest and linked evidence.
- For iPhone Mirroring text input, record that the Mac input source was English/ABC when diagnosing transformed or duplicated characters. Never submit a value that has not been visually verified in a fresh screenshot.
- For new-feature testing, identify the original case source, optional requirement source, converted feature document, QA/server environment, user-prepared first-case scene, and restart re-entry path.
- Keep required `F` case results and exploratory `E` findings in separate tables and statistics. Do not use extra exploratory checks to dilute a blocked or failed required case.
- Separate confirmed product failures, possible risks, experience/testability suggestions, prerequisite gaps, and automation-route limitations. A screenshot-based suspicion without stable reproduction is a possible risk, not a confirmed defect.

## Final Report Structure

1. Scope: build, platform route, device/window, account handling, case file, run time.
2. Overall conclusion: pass, blocked, pass with risks, or inconclusive.
3. Case status table: one row per case id or module.
4. Operation path screenshots: ordered evidence with short captions.
5. Confirmed failures: severity, evidence, expected vs actual, reproducibility.
6. Possible risks: suspicious but unconfirmed anomalies, UX concerns, flaky timing, route limitations.
7. Skipped coverage: voice, real-device-only items, destructive flows, unavailable account states.
8. Follow-up recommendations: retest data, logs needed, owner suggestions, release impact.

For a new-feature exploratory report, also include:

9. Source traceability: source test-case link/file, optional requirement link/file, converted document path, and unresolved source gaps.
10. Preparation and recovery: server environment, account/data/flags, the first-case scene prepared by the user, and the documented restart re-entry route.
11. Exploratory results: `E` case coverage, possible risks, and suggestions, separate from the formal `F` case result.
12. Asset follow-up: remind the user to review and commit the converted feature execution document to `qa-common-skill`; do not claim it was merged into main smoke.

## Status Meaning

- `通过`: observed expected state and no release-relevant gaps for that case.
- `带风险通过`: main path works, but route limits, timing instability, logs, or UX signals need review.
- `阻塞`: required path cannot continue, app crashes, login blocks, or data/account state prevents execution.
- `自动化阻塞 / 需人工复核`: app may be usable, but the selected automation route cannot reliably complete the control.
- `未执行`: the step was not operated.
- `不适用`: out of current case scope or intentionally removed.
- `建议`: a product, UX, observability, or testability improvement; not a test failure.

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
- Confirm `report.html` contains no local file paths or HTTP image dependencies and still shows all screenshots after the file is copied away from the run directory.
