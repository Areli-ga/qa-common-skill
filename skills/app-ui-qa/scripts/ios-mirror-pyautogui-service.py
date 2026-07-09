#!/usr/bin/env python3
import os
import subprocess
import time
from pathlib import Path

import pyautogui
from flask import Flask, jsonify, request

app = Flask(__name__)
ROOT = Path(os.environ.get("IOS_MIRROR_PYAUTO_ROOT", ".")).resolve()
APP_NAME_QUERY = os.environ.get("IOS_MIRROR_APP_QUERY", "iPhone")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = float(os.environ.get("IOS_MIRROR_PYAUTO_PAUSE", "0.05"))


def activate_window():
    script = f'''
tell application "System Events"
    set mirrorProc to first application process whose name contains "{APP_NAME_QUERY}"
    set frontmost of mirrorProc to true
    set bestWindow to missing value
    set bestArea to 0
    repeat with candidateWindow in windows of mirrorProc
        set candidateSize to size of candidateWindow
        set candidateArea to (item 1 of candidateSize) * (item 2 of candidateSize)
        if candidateArea > bestArea then
            set bestArea to candidateArea
            set bestWindow to candidateWindow
        end if
    end repeat
    if bestWindow is missing value then error "No iPhone Mirroring window found"
    set mirrorWindow to bestWindow
    perform action "AXRaise" of mirrorWindow
    set windowPosition to position of mirrorWindow
    set windowSize to size of mirrorWindow
    return (name of mirrorProc) & "|" & (item 1 of windowPosition) & "|" & (item 2 of windowPosition) & "|" & (item 1 of windowSize) & "|" & (item 2 of windowSize)
end tell
'''
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        text=True,
        capture_output=True,
    )
    parts = result.stdout.strip().split("|")
    if len(parts) != 5:
        raise RuntimeError(f"Unexpected iPhone Mirroring window response: {result.stdout!r}")
    name, x, y, width, height = parts
    return {
        "name": name,
        "x": int(x),
        "y": int(y),
        "width": int(width),
        "height": int(height),
    }


def resolve_output(value, default_name):
    output = Path(value or default_name)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def to_screen_point(rect, x, y, space):
    if space == "screen":
        return int(x), int(y)
    if space != "window":
        raise ValueError("space must be 'window' or 'screen'")
    if x < 0 or y < 0 or x > rect["width"] or y > rect["height"]:
        raise ValueError(
            f"window point ({x}, {y}) is outside iPhone Mirroring rect "
            f"{rect['width']}x{rect['height']}"
        )
    return int(rect["x"] + x), int(rect["y"] + y)


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "pyautogui": getattr(pyautogui, "__version__", "unknown"),
            "screen": list(pyautogui.size()),
            "root": str(ROOT),
        }
    )


@app.post("/window")
def window():
    started = time.perf_counter()
    rect = activate_window()
    return jsonify({"ok": True, "window": rect, "durationMs": round((time.perf_counter() - started) * 1000, 1)})


@app.post("/screenshot")
def screenshot():
    started = time.perf_counter()
    body = request.get_json(silent=True) or {}
    rect = activate_window()
    output = resolve_output(body.get("output"), f"screenshot-{int(time.time())}.png")
    image = pyautogui.screenshot(
        region=(rect["x"], rect["y"], rect["width"], rect["height"])
    )
    image.save(output)
    return jsonify(
        {
            "ok": True,
            "mode": "pyautogui-region",
            "output": str(output),
            "window": rect,
            "imageSize": list(image.size),
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        }
    )


@app.post("/tap")
def tap():
    started = time.perf_counter()
    body = request.get_json(force=True)
    rect = activate_window()
    sx, sy = to_screen_point(rect, body["x"], body["y"], body.get("space", "window"))
    pyautogui.click(sx, sy)
    return jsonify(
        {
            "ok": True,
            "action": "tap",
            "screen": [sx, sy],
            "window": rect,
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        }
    )


@app.post("/drag")
def drag():
    started = time.perf_counter()
    body = request.get_json(force=True)
    rect = activate_window()
    space = body.get("space", "window")
    sx, sy = to_screen_point(rect, body["x"], body["y"], space)
    ex, ey = to_screen_point(rect, body["x2"], body["y2"], space)
    duration = float(body.get("duration", 0.5))
    pyautogui.moveTo(sx, sy, duration=0.05)
    pyautogui.dragTo(ex, ey, duration=duration, button="left")
    return jsonify(
        {
            "ok": True,
            "action": "drag",
            "from": [sx, sy],
            "to": [ex, ey],
            "window": rect,
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        }
    )


@app.post("/type")
def type_text():
    started = time.perf_counter()
    body = request.get_json(force=True)
    rect = activate_window()
    text = str(body.get("text", ""))
    if body.get("x") is not None and body.get("y") is not None:
        sx, sy = to_screen_point(rect, body["x"], body["y"], body.get("space", "window"))
        pyautogui.click(sx, sy)
    interval = float(body.get("interval", 0.03))
    pyautogui.write(text, interval=interval)
    return jsonify(
        {
            "ok": True,
            "action": "type",
            "chars": len(text),
            "window": rect,
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        }
    )


@app.post("/key")
def key():
    started = time.perf_counter()
    body = request.get_json(force=True)
    rect = activate_window()
    if "keys" in body:
        pyautogui.hotkey(*body["keys"])
        key_value = body["keys"]
    else:
        key_value = body["key"]
        pyautogui.press(key_value)
    return jsonify(
        {
            "ok": True,
            "action": "key",
            "key": key_value,
            "window": rect,
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("IOS_MIRROR_PYAUTO_PORT", "17650"))
    app.run(host="127.0.0.1", port=port)
