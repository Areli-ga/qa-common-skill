#!/usr/bin/env bash
set -u

target="${1:-all}"
fail=0

say() {
  printf '%s\n' "$*"
}

ok() {
  say "[ok] $*"
}

warn() {
  say "[warn] $*"
}

missing() {
  fail=1
  say "[missing] $*"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

check_common() {
  say "== Common =="
  if has_cmd node; then
    ok "node: $(node -v)"
  else
    missing "node is required to render report.html with scripts/render-manual-report.mjs"
  fi

  if has_cmd python3; then
    ok "python3: $(python3 --version 2>&1)"
  else
    missing "python3 is required for the iOS PyAutoGUI service"
  fi
}

check_android() {
  say "== Android adb-only =="
  if ! has_cmd adb; then
    missing "adb not found. Install Android SDK Platform Tools and add it to PATH."
    return
  fi

  ok "adb: $(adb version | head -n 1)"
  adb devices

  serial="${ANDROID_SERIAL:-}"
  package="${ANDROID_PACKAGE:-com.giggleacademy.app}"
  if [ -z "$serial" ]; then
    warn "ANDROID_SERIAL is not set. Pick one serial from adb devices before running smoke."
    return
  fi

  state="$(adb -s "$serial" get-state 2>/dev/null || true)"
  if [ "$state" = "device" ]; then
    ok "ANDROID_SERIAL=$serial is online"
  else
    missing "ANDROID_SERIAL=$serial is not online or not authorized"
    return
  fi

  if adb -s "$serial" shell pm path "$package" >/dev/null 2>&1; then
    ok "Android package installed: $package"
  else
    warn "Android package not found: $package"
    warn "If QA provided an APK, install with: adb -s \"$serial\" install -r \"\$ANDROID_APK_PATH\""
  fi
}

check_ios() {
  say "== iOS iPhone Mirroring + PyAutoGUI =="
  say "[required] If S02 is in scope, have the user manually prepare the target TestFlight build as a fresh, not-yet-launched installation before automation; reinstall/download may take significant time."
  say "[required] Switch the macOS input source to English/ABC before every iPhone Mirroring text-input step; Chinese input sources can transform or duplicate PyAutoGUI keystrokes."
  if ! has_cmd osascript; then
    missing "osascript not found; macOS automation is required for iPhone Mirroring window detection"
  else
    ok "osascript available"
  fi

  ios_python="${IOS_MIRROR_PYTHON:-}"
  if [ -z "$ios_python" ] && [ -x ".venv-ios-mirror/bin/python" ]; then
    ios_python=".venv-ios-mirror/bin/python"
  fi
  if [ -z "$ios_python" ]; then
    ios_python="python3"
  fi

  if has_cmd "$ios_python" || [ -x "$ios_python" ]; then
    ok "iOS python runner: $ios_python"
    "$ios_python" - <<'PY'
import importlib.util
missing = [m for m in ("pyautogui", "PIL", "flask") if importlib.util.find_spec(m) is None]
if missing:
    print("[missing] Python packages: " + ", ".join(missing))
    print("[hint] python3 -m venv .venv-ios-mirror && .venv-ios-mirror/bin/python -m pip install pyautogui pillow flask")
    raise SystemExit(1)
print("[ok] Python packages: pyautogui, pillow, flask")
PY
    if [ $? -ne 0 ]; then
      fail=1
    fi
  fi

  if pgrep -if "iPhone Mirroring" >/dev/null 2>&1; then
    ok "iPhone Mirroring process is running"
  else
    warn "iPhone Mirroring is not running. Open it and connect/unlock the iPhone before an iOS smoke run."
  fi

  say "[hint] macOS permissions: grant Accessibility and Screen Recording to Codex, Terminal, and the Python runner."
}

case "$target" in
  all)
    check_common
    check_android
    check_ios
    ;;
  android)
    check_common
    check_android
    ;;
  ios)
    check_common
    check_ios
    ;;
  *)
    say "Usage: $0 [all|android|ios]"
    exit 2
    ;;
esac

exit "$fail"
