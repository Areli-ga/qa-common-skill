# Environment Guide

This skill has only two formal execution routes:

- Android: adb-only on a connected Android device or emulator.
- iOS: PyAutoGUI service on a real iPhone through macOS iPhone Mirroring.

External device-automation frameworks and desktop mirroring experiments are intentionally out of scope for this skill.

## Contents

- Mac requirements and environment check
- Android adb-only setup and notes
- iOS fresh-install preparation, iPhone Mirroring, and PyAutoGUI service setup
- Test data, installation, and troubleshooting

## Mac Requirements

- Codex desktop for visual inspection and report generation.
- Android SDK Platform Tools so `adb` is available for Android runs.
- An Android device or emulator with USB debugging enabled, visible in `adb devices`, and the target app installed or an APK path available.
- A Mac/iPhone pair that supports iPhone Mirroring when running iOS.
- TestFlight on the iPhone when installing or updating beta builds.
- For iOS scope that includes S02, the target TestFlight build manually prepared by the user as a fresh installation that has not been launched.
- Python 3 with `pyautogui`, `pillow`, and `flask` for the iOS route.
- macOS Accessibility and Screen Recording permissions granted for Codex, Terminal, and the app running the PyAutoGUI service.
- macOS English/ABC input source available for every iPhone Mirroring text-input step. Do not use a Chinese input source with PyAutoGUI typing.
- Browser or Finder access for opening the final HTML report.

## Environment Check

Run the bundled checker from the skill folder before the first run on a QA machine:

```bash
scripts/check-environment.sh all
scripts/check-environment.sh android
scripts/check-environment.sh ios
```

The script reports missing commands/packages and prints the install command to run. It does not click app UI or modify app data.

## Android Route

Use adb-only as the formal Android target.

1. Connect a real Android device or start an emulator.
2. Confirm the device is visible and authorized:

```bash
adb devices
```

3. Select one serial and use it for every Android command:

```bash
export ANDROID_SERIAL="<serial>"
export ANDROID_PACKAGE="com.giggleacademy.app"
```

4. If needed, install an APK provided by QA:

```bash
adb -s "$ANDROID_SERIAL" install -r "$ANDROID_APK_PATH"
```

5. Verify the package is installed and launch it:

```bash
adb -s "$ANDROID_SERIAL" shell pm path "$ANDROID_PACKAGE"
adb -s "$ANDROID_SERIAL" shell monkey -p "$ANDROID_PACKAGE" -c android.intent.category.LAUNCHER 1
```

6. Capture screenshots and logs:

```bash
adb -s "$ANDROID_SERIAL" exec-out screencap -p > screenshots/current.png
adb -s "$ANDROID_SERIAL" logcat -d > logs/logcat.txt
adb -s "$ANDROID_SERIAL" shell dumpsys window | rg 'mCurrentFocus|mFocusedApp'
```

For Giggle Academy, the default package is `com.giggleacademy.app`. Use `monkey -p` unless the test owner provides a current entry Activity.

Use `adb shell pm clear <package>` only when the case or test manager explicitly allows a clean-data run. Capture the before/after state and record that existing local data was removed.

## Android Notes

- ADB screenshot dimensions are the coordinate system for `adb shell input`.
- Bind screenshots, input, foreground checks, and Logcat to the same serial.
- IDEs may be open for development, but Android automation must still use adb-only in this skill.
- Emulator slowness can invalidate gesture timing. Move release smoke to a real device when this happens.

## iOS iPhone Mirroring Route

This route uses the real iPhone shown in macOS iPhone Mirroring. TestFlight is only the install/update channel. PyAutoGUI is used as a fast local input and screenshot service.

1. If S02 is in scope, confirm before automation that the user manually uninstalled the old App, installed the target build through TestFlight, and has not launched it yet.
2. If the fresh installation is not prepared at initial intake, stop before all automation, including S01 and S03. Explain that iOS has no Android-style convenient clear-data route and that uninstalling, reinstalling, and downloading through TestFlight may take significant time.
3. Ask for action-time confirmation before any uninstall or before clicking `安装`, `更新`, `停止测试`, notification toggles, or feedback submission.
4. Open iPhone Mirroring and keep the phone unlocked/connected.
5. Open TestFlight on the mirrored phone only when installing or updating the beta build.
6. Launch the App on the mirrored phone only after fresh-install readiness has been confirmed.
7. Start the PyAutoGUI service.
8. Use the service for screenshots, taps, drags, typing, and key presses.
9. Keep the iPhone Mirroring window visible, frontmost, and uncovered.
10. Before any App text input, switch the Mac input source to English/ABC. Keep it selected until the complete visible value has been verified in a fresh screenshot.

Known boundary: the app is running on a real iPhone, but evidence and input are mediated by the Mac mirror. If audio, secure input, or system privacy behavior cannot be observed through the mirror, mark the route limitation separately from product defects.

## iOS Fresh Install and S02 Supplemental Retest

iOS does not provide an Android-style convenient clear-App-data command. Use uninstall plus TestFlight reinstall to create a fresh state for S02.

Before an iOS run that includes S02:

1. Tell the user to manually uninstall the old App and install the target build through TestFlight before automation begins.
2. Require the newly installed App to remain unopened so the first-launch path is preserved.
3. Confirm the build/version and readiness before starting S01.

Do not use the later supplemental-S02 ordering rule to bypass this initial prerequisite. Running S03 first is allowed only after an automation run already started with a valid fresh installation and S02 later became blocked.

If S02 needs a fresh-install retest after the run has started:

1. Keep the current installation and finish S03 plus every later reachable case first.
2. Record S02 as pending supplemental retest; do not sacrifice downstream coverage by uninstalling immediately.
3. After downstream coverage is complete, ask for action-time confirmation, uninstall the App, and reinstall the target build through TestFlight.
4. Account for TestFlight download time, then run S02 as a separate supplemental segment and link its evidence to the original report.

## iPhone Mirroring PyAutoGUI Service

Create a local virtualenv if needed:

```bash
python3 -m venv .venv-ios-mirror
.venv-ios-mirror/bin/python -m pip install pyautogui pillow flask
```

Start the service after iPhone Mirroring is open:

```bash
IOS_MIRROR_PYAUTO_ROOT="runs/ios-smoke" \
.venv-ios-mirror/bin/python scripts/ios-mirror-pyautogui-service.py
```

Useful calls:

```bash
curl -s http://127.0.0.1:17650/health
curl -s -X POST http://127.0.0.1:17650/window
curl -s -X POST http://127.0.0.1:17650/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"output":"screenshots/001-home.png"}'
curl -s -X POST http://127.0.0.1:17650/tap \
  -H 'Content-Type: application/json' \
  -d '{"x":42,"y":62,"space":"window"}'
curl -s -X POST http://127.0.0.1:17650/drag \
  -H 'Content-Type: application/json' \
  -d '{"x":520,"y":330,"x2":230,"y2":330,"duration":0.6,"space":"window"}'
```

Coordinates default to iPhone Mirroring window-relative points, not screenshot pixels. The service re-detects and raises the mirror window before each action, then validates window-relative points are inside the mirror window.

Optional configuration:

```bash
IOS_MIRROR_APP_QUERY="iPhone"
IOS_MIRROR_PYAUTO_PORT="17650"
IOS_MIRROR_PYAUTO_ROOT="runs/ios-smoke"
IOS_MIRROR_PYAUTO_PAUSE="0.05"
```

PyAutoGUI screenshots are region screenshots. They are fast, but they capture the currently visible desktop region, so do not cover iPhone Mirroring with Codex, browser windows, or notification overlays during evidence capture.

## Test Data

Use local environment variables or untracked notes for credentials:

```bash
APP_QA_USERNAME=""
APP_QA_PASSWORD=""
GA_TEST_EMAIL=""
GA_TEST_PASSWORD=""
GA_EXPECTED_CHILD_NAME=""
GA_NEW_CHILD_NAME=""
ANDROID_SERIAL=""
ANDROID_PACKAGE="com.giggleacademy.app"
ANDROID_APK_PATH=""
IOS_BUNDLE_ID="com.giggleacademy.app"
```

Do not commit real account passwords or API keys.

## Skill Installation for Teammates

Copy only the pure `app-ui-qa` skill folder:

```bash
mkdir -p ~/.codex/skills
cp -R app-ui-qa ~/.codex/skills/app-ui-qa
```

Restart Codex so it discovers the skill. Do not copy exploration folders into this skill.

## Troubleshooting

- `adb: command not found`: install Android SDK Platform Tools, then add its folder to `PATH`.
- `adb unauthorized`: unlock the Android device and accept the debugging prompt.
- Android screenshots/logs look like the wrong device: re-run `adb devices`, pick one serial, and use `adb -s <serial>` everywhere.
- TestFlight install button absent: confirm Apple ID beta access, build validity, and build availability.
- TestFlight install/update needs confirmation: ask immediately before clicking the install/update UI.
- iOS S02 is requested but no fresh TestFlight installation is ready: stop before automation, ask the user to prepare it, and explain that uninstall/reinstall plus download may take significant time.
- iPhone Mirroring cannot find the phone: unlock the iPhone, keep Bluetooth/Wi-Fi on, bring it near the Mac, then retry the mirror connection.
- iPhone Mirroring screenshot captures Codex or another app: bring iPhone Mirroring to the front, move covering windows away, then retake the PyAutoGUI screenshot.
- iPhone Mirroring text is transformed, duplicated, or otherwise abnormal: stop before submitting, switch the Mac input source to English/ABC, reset the field/page, and type or paste again into a confirmed empty field.
- Password screen appears black only while typing: treat as secure input, hide keyboard/input bar, then screenshot the masked state.
