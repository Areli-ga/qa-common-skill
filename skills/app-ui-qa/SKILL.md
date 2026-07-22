---
name: app-ui-qa
description: Case-first mobile UI smoke testing for hybrid Android/iOS apps. Use when Codex needs to prepare, execute, recover, or report Android adb-only or iOS iPhone Mirroring plus PyAutoGUI validation with mandatory active-case reading, screenshots, logs, environment checks, and HTML QA reports.
---

# App UI QA

Use this skill for the formal Giggle Academy style smoke workflow:

- Android route: operate one connected Android device or emulator through adb-only commands for input, screenshots, lifecycle operations, foreground checks, and Logcat.
- iOS route: operate the real iPhone through macOS iPhone Mirroring and the local PyAutoGUI HTTP service. Use TestFlight on the phone only to install or update a build with user confirmation.
- Report route: save screenshots for every key action/checkpoint, then produce `report.md` and `report.html`.

Keep separate comparison experiments outside this skill.

## Read the Active Case First

Do not operate the App from `SKILL.md` alone.

1. Select the active case before touching the device.
2. Read the active Markdown case in full, including its scope boundaries, general prerequisites, global checkpoints, module steps, notes, recovery rules, and exclusions.
3. For Giggle Academy main smoke, read both `assets/cases/giggleacademy-main-smoke-v0.1.md` and `assets/cases/giggleacademy-main-smoke-v0.1.json`. Treat the Markdown rules as mandatory operating context and the JSON as the structured step companion. Reconcile any difference before execution.
4. For Android channel package smoke, read `assets/cases/giggleacademy-android-channel-smoke-v0.1.md` in full. Its explicit new-user skip/exit steps belong to the independent channel scope and take precedence over main-smoke S02 behavior.
5. If the selected case is incomplete or unclear, organize it first and ask the test manager to confirm the affected scope.

## Workflow

1. Confirm the active case and all of its rules have been read in full.
2. Pick exactly one execution route:
   - Android: adb-only against the selected `ANDROID_SERIAL`.
   - iOS: iPhone Mirroring plus the local PyAutoGUI service on the mirrored real phone.
3. Run route-specific environment checks before the first operation; install or ask the QA owner to install missing prerequisites. For an iOS run that includes S02, confirm the user has manually prepared a fresh TestFlight installation before automation starts.
4. State the next case id before operating. Never follow visible App content outside the active case.
5. Capture evidence before and after every key click, swipe, drag, input, page entry, completion state, recovery action, and final state.
6. Record pass, block, and risk results immediately while the screen evidence is fresh.
7. Generate or update an HTML report with screenshots rendered inline.

## Read References As Needed

- Setup and route selection: `references/environment.md`
- Case cleanup and JSON/checklist shape: `references/test-case-format.md`
- Android adb-only and iOS iPhone Mirroring operating rules: `references/execution-routes.md`
- Report structure and status taxonomy: `references/reporting.md`

## Critical Execution Rules

- Case first, device second. Do not infer smoke scope from the App's current state.
- If a visible page is not listed in the active case, do not explore it.
- If a course finishes and auto-enters the next course/content, screenshot that off-path state, then use the top-left back/exit/pause control to return to the main path. Apply this recovery only after confirmed completion; never use top-left exit to force progress while a course is still running.
- After beginner-course completion, loading-like course-opening screens or content such as `颜色飞溅`, `颜色配对`, or `颜色 1` are auto-entered next-course content. Capture evidence and return to the main path immediately.
- If an unrelated guide/coachmark appears, capture it, then try a safe blank area outside highlighted/card content before using close/back controls.
- If course completion lands on `学习之星` or another leaderboard page, capture it and use the visible continue/next control to return to the main path.
- Before tapping any post-completion `继续`, `下一步`, or right-arrow control, take a fresh screenshot and confirm the control remains on the intended page. Skip stale coordinates after an automatic return.
- Before S03/login or any later module after beginner-course completion, verify main-path signals such as the top-left avatar, learning center, or visible path nodes.
- In main smoke, treat S02 as a one-time entry path that normally appears only after install, reinstall, or cleared data. Do not restart merely to bypass the beginner course. If a genuine blocking state occurs, capture the screen and attempted actions, record expected/actual state, then restart once as recovery. If restart removes the one-time entry, do not infer S02 completion; record S02 as incomplete/blocked for that run and continue every later case that remains reachable. Reinstall or clear data again only when specifically retesting S02.
- In Android channel package smoke, follow the channel case's explicit skip/exit/restart steps. Do not import the main-smoke S02 completion requirement into that independent scope.
- Android must use adb-only unless the user explicitly requests a separate exploration. Use `adb -s <serial>` for every command and bind screenshots, foreground checks, input, and Logcat to that serial.
- Prefer a real Android device for release smoke when emulator timing is slow or flaky.
- Use iPhone Mirroring against the real phone for iOS release smoke whenever available. Use TestFlight only for phone build installation or updates.
- Before starting an iOS main-smoke run that includes S02, require the user to manually prepare the target build as a fresh TestFlight installation. If it is not ready at initial intake, do not start S01, S03, or any other automated part of that requested run; explain that iOS fresh-state preparation requires uninstalling the current App and reinstalling through TestFlight, and the download may take significant time. Ask for action-time confirmation before any uninstall/install action.
- If iOS S02 needs a fresh-install retest after the current run has started, first finish S03 and every later reachable case on the current installation. After downstream coverage is preserved, uninstall and reinstall through TestFlight with user confirmation, then run S02 as supplemental coverage with separate evidence.
- Use the PyAutoGUI service for iPhone Mirroring screenshots and actions. Keep the mirror frontmost and uncovered; the service must raise it before every action or screenshot.
- Before every iPhone Mirroring text-input step, switch the Mac input source to English/ABC. A Chinese input source can transform or duplicate PyAutoGUI keystrokes. Do not submit until a fresh screenshot confirms the complete visible value.
- For horizontal cards or level lists, drag blank/non-card areas between, above, or below cards. Do not drag a card body unless selecting it is intended.
- Treat password-entry black/hidden projection as expected secure-input behavior only when it occurs while the password field or keyboard/input bar is active. Enter the password, hide the keyboard/input bar, capture the masked state, and continue.
- Skip voice recognition unless an approved audio fixture, injection strategy, or test stub is provided. Wait 5 seconds for expected voice/repeat auto-skip checks. Wait 2 seconds for non-voice transitions, then capture a fresh screenshot before deciding or tapping.
- Do not store raw passwords, tokens, complete child ids, IPs, or audio URLs in reports or prompts.
- If a precision drag or tracing control cannot be completed after reasonable attempts, mark it `自动化阻塞 / 需人工复核`, capture evidence, and use the case-defined recovery path when later cases do not depend on completion.
- Treat permission enablement as part of the test path. Capture the App rationale, confirm it, allow the corresponding system permission, and check the post-permission state before classifying a block. On first iOS launch, allow every presented system permission prompt needed by the case, including advertising tracking and network/local-network access.
- If an unexpected state blocks a case, capture it, record the case id and expected/actual state, try case-defined recovery, then force-close and relaunch once when safe. Re-establish the nearest prerequisite and continue later reachable cases.
- Do not classify one transient block as a product defect. Require a persistent/reproducible failure, crash, or corroborating diagnostic evidence; otherwise report a recoverable state risk or automation-route limitation.
- If recovery cannot restore a shared prerequisite, mark only dependent cases as `阻塞`. Continue every later module with an independent or recovered entry path and update the HTML report with all evidence collected.
- On iPhone Mirroring, if editing shortcuts fail or text is duplicated, do not submit. Confirm the Mac input source is English/ABC, reset the page/form, and prefer clipboard paste into a confirmed empty field. Keep password input masked and clear sensitive clipboard content immediately after use.

## Resources

- `scripts/render-manual-report.mjs`: render screenshot-backed `report.md` into browser-friendly `report.html`.
- `scripts/check-environment.sh`: check Android adb-only and iOS iPhone Mirroring/PyAutoGUI prerequisites before a run.
- `scripts/ios-mirror-pyautogui-service.py`: local HTTP service for iPhone Mirroring screenshots, taps, drags, text input, and key presses.
- `assets/templates/smoke-intake.md`: handoff template for mind maps, Excel, Jira/TestRail/TAPD, or manual smoke cases.
- `assets/templates/project-intake.sample.json`: project/build/device/test-account intake template.
- `assets/templates/smoke.sample.json`: baseline smoke case JSON shape.
- `assets/templates/feature.sample.json`: targeted feature validation JSON shape.
- `assets/templates/env.example`: local test account/device variables only.
- `assets/cases/giggleacademy-main-smoke-v0.1.md`: bundled Giggle Academy main smoke checklist.
- `assets/cases/giggleacademy-main-smoke-v0.1.json`: bundled Giggle Academy main smoke machine-readable case.
- `assets/cases/giggleacademy-android-channel-smoke-v0.1.md`: bundled Android channel package smoke checklist.
