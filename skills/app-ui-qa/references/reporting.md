# Reporting Guide

Visual automation runs are manual-evidence runs. The report must be based on the visible app state, saved screenshots, ADB/Logcat evidence when available, iPhone Mirroring/PyAutoGUI evidence when available, and the active case.

## Contents

- Required artifacts and standalone rendering
- QA Web upload contract
- Crash evidence and embedded logs
- Evidence policy and final report structure
- Status meaning and risk taxonomy
- Review checklist

## Required Artifacts

Keep these files together in a run directory for source evidence and audit:

- `report.md`: editable/source report.
- `report.html`: self-contained browser-readable report. It must remain complete when copied or uploaded without `screenshots/`.
- `screenshots/`: original evidence screenshots.
- `logs/`: ADB/Logcat or other local diagnostic files. Optional for runs without diagnostics; required when a crash occurs.

Render HTML from Markdown:

```bash
node scripts/render-manual-report.mjs runs/smoke/report.md runs/smoke/report.html
```

The renderer must inline every local screenshot as a `data:` URI. It prefers WebP at quality 76 and a maximum width of 1280 pixels, then falls back to the original PNG/JPEG/GIF/SVG bytes when no WebP converter is available. Both paths produce one portable HTML file.

To embed a reviewed plain-text log, put this directive on its own line in `report.md`:

```html
<qa-log src="logs/android-crash-report.log" title="Android 崩溃日志"></qa-log>
```

The renderer reads the complete local text file and writes it into a collapsed, scrollable log block in `report.html`. The uploaded HTML remains self-contained and requires no JavaScript or external `.log` file. Keep the original raw log separately under `logs/`; the referenced report copy must be reviewed and redacted before rendering.

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

The default renderer must fail when a referenced local image or `<qa-log>` file is missing, when an external image remains, or when a log directive points to an external URL or binary file. Treat this as a report build failure rather than publishing a partially broken report.

## QA Web Upload Contract

- Upload only `report.html` for viewing. Keep `report.md`, `screenshots/`, and logs in the run archive for traceability.
- Allow `data:` in the viewer's image content-security policy, for example `img-src data:`. If the report document receives a CSP, also permit its bundled inline stylesheet with `style-src 'unsafe-inline'`; no script permission is required.
- Render uploaded reports in a sandboxed iframe or on an isolated origin. The bundled renderer emits no JavaScript, but uploaded HTML should still be treated as untrusted content.
- Do not rewrite, sanitize away, or proxy `data:image/...;base64,...` values.
- Preserve UTF-8 and serve with `Content-Type: text/html; charset=utf-8`.
- Enable gzip or Brotli for HTML responses. Base64 increases the stored HTML size, while transport compression recovers much of that overhead.
- Set an upload-size limit based on real reports. The renderer prints source image bytes, embedded image bytes, and final standalone HTML size after every build.

## Authenticated QA Web Upload

QA Web is protected by Cloudflare Access. Every app-ui-qa run must finish by uploading its verified report, even when the user did not mention report generation or upload. Each QA member must upload through their own identity so the report list records the correct uploader. The preferred route is the site's upload form in the user's signed-in Chrome session; do not export browser cookies, copy access JWTs, reuse another member's session, or place credentials in local environment files.

1. Finish the run and render the final standalone `report.html`.
2. Confirm the renderer completed without missing images or external image dependencies. Keep `report.md`, screenshots, and logs local.
3. Open `https://qa-platform.giggletools.com/ui/reports` in the QA member's signed-in Chrome session.
4. If Cloudflare Access redirects to login, pause and ask the QA member to sign in with their own account in that Chrome window. Continue only after the report page shows that member's identity.
5. Click `上传报告`, enter a clear build/run title, select `Android` or `iOS`, and choose only the final `report.html`. This upload is a mandatory part of the skill's requested workflow and must not be omitted because the original prompt was silent about reports.
6. Before clicking the final `上传` button, verify the title, platform, selected filename, and that the file is the standalone renderer output. Do not upload `report.md`, screenshot folders, logs, credentials, or intermediate HTML.
7. After upload, verify a new list row shows the matching title, platform, current QA member under `上传人`, and the current upload time. Open the report and confirm the first page plus at least one embedded screenshot renders; record the report URL when available.
8. If authentication expires or upload fails, keep the local artifacts, report upload finalization as blocked separately from the App smoke result, and do not rerun the device test. Resume upload after the QA member restores access; do not declare the run fully finalized until the uploaded row and report rendering are verified.

The backend contract is:

```http
POST https://qa-platform.giggletools.com/api/ui_reports
Content-Type: application/json
```

```json
{
  "title": "报告标题",
  "platform": "android",
  "run_ref": "可选，≤128 字符",
  "html": "报告 HTML 的完整文本"
}
```

`platform` is `android` or `ios`. `run_ref` is optional and must not exceed 128 characters. The current web form exposes title, platform, and HTML file selection; it may omit `run_ref`. Direct unauthenticated requests are redirected to Cloudflare Access. Prefer the browser form because it uses the QA member's authenticated session and preserves uploader attribution. Use the raw API only when the platform owner provides a documented per-user authentication method; never work around Cloudflare Access by extracting cookies or tokens from Chrome.

## Crash Evidence and Embedded Logs

When an App crash is observed, record the case id, build, platform/device, local timestamp with timezone, last visible page, action immediately before the crash, crash UI/system prompt, restart result, and whether the failure reproduced. A crash is direct diagnostic evidence; do not downgrade it to an ordinary transient page block.

For iOS:

- Capture the crash state and any system prompt asking whether to share crash information with the developer.
- Always select the share option so the developer-side crash log can be correlated later, then capture the selected or post-share state.
- Record the exact local time, build, device, active case, and pre-crash action in the report because iPhone Mirroring does not directly retrieve the submitted crash payload.

For Android:

- Use the same `ANDROID_SERIAL` as the screenshots and actions.
- Collect the crash Logcat buffer, a bounded main/system/crash context window, and `dumpsys activity exit-info` when supported immediately after the crash.
- Keep complete raw output under `logs/`. Create a separate report-safe text file that preserves the crash stack and relevant context while redacting passwords, authorization headers, tokens, cookies, complete child ids, IP addresses, audio URLs, and unrelated personal data.
- Reference the sanitized copy with `<qa-log>` so its complete text is embedded in the standalone HTML. The collapsed block keeps a large log readable, but it still increases HTML size; check the renderer's final byte count before upload.
- Never clear Logcat after a crash before the evidence has been saved.

## Evidence Policy

- The report must show the full operation path, not only failed or risky steps.
- Save screenshots before and after every key click, swipe, drag, input, page entry, completion state, recovery action, and final state.
- Always attach screenshots for blocked, failed, needs-review, and UX-risk steps.
- For every crash, attach the pre-crash checkpoint when available, crash/system-prompt state, post-share state on iOS, relaunch result, and Android diagnostic log block when applicable.
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
5. Confirmed failures and crash diagnostics: severity, evidence, expected vs actual, reproducibility, timestamps, iOS share handling, and embedded Android logs.
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
- `跳过 / 自动化能力限制`: the active case explicitly excludes a behavior the selected route cannot perform, such as real recording. It is neither a product failure nor a reason to skip independent later cases.
- `跳过 / 人工已覆盖`: the active case explicitly delegates this coverage to a recorded manual result. Do not run an obsolete automated path in its place.
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
- Confirm every iOS crash-information prompt was shared with the developer and the action was recorded.
- Confirm every Android crash has saved diagnostics and that only the reviewed/redacted log copy is embedded through `<qa-log>`.
- Confirm iPhone Mirroring limitations are called out separately from product defects.
- Confirm skipped voice/manual steps are acceptable for the current release gate.
- Confirm `report.html` contains no local file paths, HTTP image dependencies, or external log dependencies and still shows all screenshots and embedded log blocks after the file is copied away from the run directory.
