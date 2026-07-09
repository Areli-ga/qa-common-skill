---
name: app-ui-qa
description: Mobile app smoke testing for hybrid Android/iOS apps. Use when Codex needs to run or prepare case-first UI smoke validation through Android adb-only on connected devices/emulators, PyAutoGUI-driven iPhone Mirroring on iOS, screenshots, logs, environment checks, and HTML QA reports.
---

# App UI QA

Use this skill for the formal Giggle Academy style smoke workflow:

- Android route: adb-only operates a connected Android device or emulator through `adb shell input`, `screencap`, app lifecycle commands, and Logcat. No desktop mirroring layer is used for Android.
- iOS route: a local PyAutoGUI HTTP service operates the real iPhone through macOS iPhone Mirroring; TestFlight on the phone is used only for installation/build update with user confirmation.
- Report route: save screenshots for every key action/checkpoint, then produce `report.md` and `report.html`.

Separate comparison experiments must live outside this skill. The formal workflow here is Android adb-only on Android, and iPhone Mirroring plus PyAutoGUI on iOS.

## Workflow

1. Identify the active smoke/feature case before touching the app.
   - For Giggle Academy main smoke, use bundled case files `assets/cases/giggleacademy-main-smoke-v0.1.md` and `assets/cases/giggleacademy-main-smoke-v0.1.json`.
   - For Android channel package smoke, use bundled case file `assets/cases/giggleacademy-android-channel-smoke-v0.1.md`.
   - If the case is incomplete, organize it first and ask the test manager to confirm unclear scope.
2. Pick exactly one execution route:
   - Android: adb-only against the selected `ANDROID_SERIAL`.
   - iOS: `iPhone Mirroring` + local PyAutoGUI service on the mirrored real phone.
3. Run route-specific environment checks before the first operation; install or ask the QA owner to install missing prerequisites.
4. State the next case id before operating. Never follow visible app content that is outside the active case.
5. Capture evidence before and after every key click, swipe, drag, input, page entry, completion state, recovery action, and final state.
6. Record pass/block/risk immediately while the screen evidence is fresh.
7. Generate or update an HTML report with screenshots rendered inline.

## Read References As Needed

- Setup and route selection: `references/environment.md`
- Case cleanup and JSON/checklist shape: `references/test-case-format.md`
- Android adb-only and iOS iPhone Mirroring operating rules: `references/execution-routes.md`
- Report structure and status taxonomy: `references/reporting.md`

## Execution Rules

- Case first, device second. Do not infer smoke scope from the app's current state.
- If a visible page is tempting but not listed in the active case, do not explore it.
- If a course finishes and auto-enters the next course/content, screenshot that off-path state, then use the top-left back/exit/pause control to return to the main path. This recovery applies only after confirmed completion; never use top-left exit to force progress while a course is still running, especially during beginner courses.
- After beginner-course completion, loading-like course-opening screens or content such as `颜色飞溅`, `颜色配对`, or `颜色 1` are auto-entered next-course content, not part of the beginner course. Capture evidence and return to the main path immediately; do not keep operating the new course.
- If an in-app guide/coachmark overlay appears and it is not the active case target, capture it first, then try tapping a safe blank area outside highlighted/card content to dismiss it before using close/back controls.
- If a course completion lands on `学习之星` or another leaderboard/ranking page, capture it and tap the continue/next button to return to the main learning path before starting the next case.
- Before tapping any post-completion `继续` / `下一步` / right-arrow style control, take a fresh screenshot and confirm the control is still visible on the intended page. If the app has already auto-returned to the main path, skip the stale coordinate click.
- Before S03/login or any next module after beginner-course completion, verify main-path signals: top-left avatar plus learning center or visible path nodes.
- Android must be operated with adb-only unless the user explicitly asks for a separate exploration. Use `adb -s <serial>` for every Android command once a serial is selected.
- Keep Android screenshots, foreground app checks, and Logcat tied to the same explicit ADB serial.
- Prefer a real Android device for release smoke when emulator performance is slow or flaky.
- iOS release smoke should use iPhone Mirroring against the real phone whenever available. Use TestFlight only to install or update the phone build.
- For iPhone Mirroring, use the PyAutoGUI service for screenshots and actions. The service must raise iPhone Mirroring before every action/screenshot.
- Keep iPhone Mirroring frontmost and uncovered during iOS runs. PyAutoGUI screenshots are fast region screenshots and will include any window covering the mirror.
- For horizontal cards or level lists, drag blank/non-card areas between cards or above/below cards. Do not drag the card body unless selecting the card is intended.
- Treat password-entry black/hidden projection as expected secure-input behavior when it occurs only while the password field or keyboard/input bar is active. Enter the password, hide the keyboard/input bar, capture the masked state, and continue.
- Voice recognition is skipped by default unless an approved audio fixture, injection strategy, or test stub is provided. When a voice/repeat step is expected to auto-skip, wait 5 seconds before checking the next screen.
- For non-voice auto-advance, auto-completion, post-completion return, or showcase transitions, wait 2 seconds, then capture a fresh screenshot before deciding or tapping.
- Do not store raw passwords, tokens, complete child ids, IPs, or audio URLs in reports or prompts.
- If a precision drag or tracing control cannot be completed after reasonable attempts, mark that step `自动化阻塞 / 需人工复核`, capture evidence, then use the case-defined recovery path if later cases do not depend on that completion.

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
