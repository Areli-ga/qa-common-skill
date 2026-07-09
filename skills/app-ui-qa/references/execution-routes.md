# Execution Routes

This is the formal execution mechanism for the skill. It must not decide smoke scope. Always load the active case first, state the next case id, and operate only that step.

## Android: adb-only

Operate Android through one explicit ADB serial. The visual loop is: take an ADB screenshot, inspect it, perform one ADB input action, then take the next screenshot.

1. Select a device:

```bash
adb devices
export ANDROID_SERIAL="<serial>"
```

2. Verify the app is installed:

```bash
adb -s "$ANDROID_SERIAL" shell pm path "${ANDROID_PACKAGE:-com.giggleacademy.app}"
```

3. Launch the app:

```bash
adb -s "$ANDROID_SERIAL" shell monkey -p "${ANDROID_PACKAGE:-com.giggleacademy.app}" -c android.intent.category.LAUNCHER 1
```

4. Capture evidence:

```bash
adb -s "$ANDROID_SERIAL" exec-out screencap -p > screenshots/current.png
```

5. Operate visible UI:

```bash
adb -s "$ANDROID_SERIAL" shell input tap <x> <y>
adb -s "$ANDROID_SERIAL" shell input swipe <x1> <y1> <x2> <y2> <durationMs>
adb -s "$ANDROID_SERIAL" shell input text "<escaped_text>"
adb -s "$ANDROID_SERIAL" shell input keyevent KEYCODE_BACK
```

6. Collect diagnostics when needed:

```bash
adb -s "$ANDROID_SERIAL" shell dumpsys window | rg 'mCurrentFocus|mFocusedApp'
adb -s "$ANDROID_SERIAL" logcat -d > logs/logcat.txt
```

Use `adb shell pm clear <package>` only when the case or test manager explicitly allows a clean-data run. Capture the before/after state and record that existing local data was removed.

## Android Known Pitfalls

- ADB coordinates are device-screen pixels, not desktop screenshot coordinates from another viewer. Use the ADB screenshot dimensions as the coordinate source.
- Always include `-s "$ANDROID_SERIAL"` after selecting a serial. Do not mix screenshots from one device with input/logs from another.
- Emulator slowness can invalidate timing. Prefer a real Android device for release smoke when available.
- If the app auto-enters the next course/content after completion, capture the off-path state and recover to the main path instead of exploring the new course.

## iOS: iPhone Mirroring + PyAutoGUI

Operate the real iPhone through the iPhone Mirroring Mac window using the local PyAutoGUI service.

1. Open iPhone Mirroring and keep the phone unlocked/connected.
2. Use TestFlight on the phone only to install, update, or select a build.
3. Ask for action-time confirmation before install/update/stop-testing/feedback actions.
4. Launch the app on the mirrored phone.
5. Start `scripts/ios-mirror-pyautogui-service.py`.
6. Use service screenshots before and after every key operation.
7. Use service `tap`, `drag`, `type`, and `key` actions for operation.

Service startup:

```bash
IOS_MIRROR_PYAUTO_ROOT="runs/ios-smoke" .venv-ios-mirror/bin/python scripts/ios-mirror-pyautogui-service.py
```

Useful calls:

```bash
curl -s http://127.0.0.1:17650/health
curl -s -X POST http://127.0.0.1:17650/window
curl -s -X POST http://127.0.0.1:17650/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"output":"screenshots/current.png"}'
curl -s -X POST http://127.0.0.1:17650/tap \
  -H 'Content-Type: application/json' \
  -d '{"x":42,"y":62,"space":"window"}'
curl -s -X POST http://127.0.0.1:17650/drag \
  -H 'Content-Type: application/json' \
  -d '{"x":520,"y":330,"x2":230,"y2":330,"duration":0.6,"space":"window"}'
```

## iOS Mirroring Route Boundaries

- The app runtime is a real iPhone, but evidence and input are mediated by macOS iPhone Mirroring.
- If audio, secure password entry, system privacy prompts, or mirror transport behavior cannot be captured faithfully, record it as a route limitation.
- If a WebView course passes only with manual click assistance, record the path as continued but mark that WebView input needs follow-up.
- PyAutoGUI screenshots are fast region screenshots. Keep iPhone Mirroring frontmost and uncovered, otherwise the evidence image can include covering Mac windows.

## Course Auto-Advance Rule

After any course completes, including beginner courses, the app may automatically enter the next course/content before evidence capture.

This recovery is only for confirmed post-completion auto-advance:

1. Capture a screenshot of the auto-entered/off-path state.
2. Use the top-left back/exit/pause control to return to the main learning path.
3. Confirm exit if the app asks.
4. If path position is uncertain, use the active case reset path, such as S05.
5. Continue with the next listed case.

Do not click top-left back/exit/home/pause while a course is still in progress to force progress.

If completion opens `学习之星` or another leaderboard/ranking page, capture it and tap the visible continue/next button to return to the main learning path. Treat this as normal completion handling, not an off-path failure.

Before tapping post-completion `继续`, `下一步`, or right-arrow style controls, always take a fresh screenshot and confirm the button is still on the intended page. Some pages auto-complete and return home while automation is waiting; a delayed coordinate tap can hit a home-path course entry or another feature. If the app has already returned to the main learning path, skip the stale click and continue with the next case.

Default waits: use 5 seconds only for voice/repeat auto-skip checks. For non-voice auto-advance, showcase completion, post-completion return, and normal screen transitions, wait 2 seconds, then capture the next screenshot.

## Guide Overlay Rule

If an in-app guide or coachmark overlay appears and it is not the active case target:

1. Capture a screenshot of the overlay.
2. Try tapping a safe blank area outside the highlighted or card content.
3. If blank-area dismissal fails, then try the visible close/back/continue control.
4. Record the dismissal method in the report.

Do not tap highlighted course cards or CTA buttons just to dismiss a guide unless the active case explicitly asks for that action.

## Precision Drag Controls

For handwriting, tracing, brushing, coloring, sliders, or draggable arrows:

1. Capture a baseline screenshot.
2. Attempt the visible drag path once or twice with route-native input.
3. On Android, use `adb shell input swipe` with device-screen coordinates and a realistic duration.
4. On iOS, use PyAutoGUI `drag` with window-relative coordinates and confirm the service reports points inside the iPhone Mirroring window.
5. After every drag, screenshot visible progress.
6. If progress resets or cannot finish, stop that case step and mark `自动化阻塞 / 需人工复核`.

For horizontal cards, level lists, or story carousels, drag blank/non-card areas between cards or above/below cards. Do not drag the card body unless selecting it is intended.

## Sensitive Data

Before typing a test account or password into the app, confirm the user has authorized that login for this route.

Never store raw passwords. If password entry causes a black/hidden projection surface only while the input field or keyboard is active, classify it as secure input behavior, hide the keyboard/input bar, capture the masked-password state, and continue.

## Reporting During Operation

Save screenshots before and after every key operation. Use names like:

- `01-home-before-open-login.png`
- `01-home-after-open-login.png`
- `12-s15-non-card-drag-result.png`

When stopped by a limitation, report the actual state; do not invent success. Try the case-defined recovery path before deciding whether downstream cases are blocked.
