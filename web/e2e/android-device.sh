#!/usr/bin/env bash
# Runs inside the emulator job: install the APK, launch it, attach to its WebView and sign in.
set -euo pipefail
adb install -r web/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n app.aaroh.lifeos/.MainActivity
sleep 15
adb exec-out screencap -p > android-1-launch.png
pid=$(adb shell pidof app.aaroh.lifeos | tr -d '\r')
echo "app pid: $pid"
adb forward tcp:9222 "localabstract:webview_devtools_remote_${pid}"
node web/e2e/android-device.cjs
adb exec-out screencap -p > android-4-device.png
