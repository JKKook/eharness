"""수집기를 로그인 시 자동 기동·상시 유지하는 launchd 에이전트 설치/해제 (macOS)."""
import os, subprocess, sys
from . import EH_HOME
from .collector import DEFAULT_PORT

LABEL = "com.eharness.collect"
PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin", "eharness")
TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{python}</string><string>{bin}</string><string>collect</string><string>--port</string><string>{port}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
  <key>Nice</key><integer>-5</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
"""


def install(port=DEFAULT_PORT):
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    os.makedirs(EH_HOME, exist_ok=True)
    open(PLIST, "w").write(TEMPLATE.format(label=LABEL, python=sys.executable, bin=BIN, port=port, log=os.path.join(EH_HOME, "collect.log")))
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", PLIST], check=True)
    print(f"installed {PLIST}\nlog: {EH_HOME}/collect.log")


def uninstall():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    if os.path.exists(PLIST):
        os.remove(PLIST)
    print("uninstalled")


def status():
    r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True, text=True)
    if r.returncode != 0:
        print("not installed"); return
    for line in r.stdout.splitlines():
        if any(k in line for k in ("state =", "pid =", "last exit")):
            print(line.strip())
