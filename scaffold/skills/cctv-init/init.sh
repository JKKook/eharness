#!/bin/bash
# cctv-init (capability: init) — 수집기(127.0.0.1:PORT 로컬 파이썬 서버)를 켜고 관측 준비 상태를 보고
# usage: init.sh [start|status|stop] [--port N]
# 관측 전용: 세션·훅에 개입하지 않는다. 상시 서비스(launchd/systemd)가 있으면 그것을 깨우고, 없으면 nohup 기동.
set -euo pipefail
cmd="${1:-start}"; [ $# -gt 0 ] && shift
PORT="${EHARNESS_PORT:-7477}"
while [ $# -gt 0 ]; do case "$1" in --port) PORT="$2"; shift 2 ;; *) echo "usage: init.sh [start|status|stop] [--port N]" >&2; exit 2 ;; esac; done
EH_HOME="${EHARNESS_HOME:-$HOME/.eharness}"
API="http://127.0.0.1:$PORT"
PIDFILE="$EH_HOME/collect.pid"
LAUNCHD_PLIST="$HOME/Library/LaunchAgents/com.eharness.collect.plist"
SYSTEMD_UNIT="$HOME/.config/systemd/user/eharness-collect.service"

# eharness CLI 위치: 환경변수 → PATH → 기본 리포 경로
if [ -n "${EHARNESS_BIN:-}" ]; then BIN="$EHARNESS_BIN"     # 그대로 사용 (Windows: "python C:/.../bin/eharness")
else
  BIN="$(command -v eharness 2>/dev/null || true)"
  [ -n "$BIN" ] || BIN="$HOME/tools/eharness/bin/eharness"
  [ -x "$BIN" ] || BIN="python3 $BIN"
fi

health() { curl -sf -m 2 "$API/health" >/dev/null 2>&1; }

report() {
  echo "수집기: 실행 중 — $API  (대시보드 $API/)"
  curl -sf -m 5 "$API/api/sessions" | python3 -c '
import json,sys
d=json.load(sys.stdin); rows=d.get("rows",[]); alive=[r for r in rows if r.get("alive")]
print("세션: 살아있음 %d / 전체 %d  (계산 %sms)" % (len(alive), len(rows), d.get("took_ms","?")))' 2>/dev/null \
    || echo "세션: /api/sessions 조회 실패(재계산 대기 ~3s 후 재시도)"
  echo "훅 배선:"; $BIN hooks --port "$PORT" 2>/dev/null | sed 's/^/  /' || echo "  (eharness CLI 없음 — 훅 상태 미확인)"
}

case "$cmd" in
  status)
    if health; then report; else echo "수집기 응답 없음 — $API  (init.sh start 로 기동)"; exit 1; fi ;;
  start)
    if health; then echo "이미 실행 중"; report; exit 0; fi
    mkdir -p "$EH_HOME"
    if [ "$(uname -s)" = "Darwin" ] && [ -f "$LAUNCHD_PLIST" ]; then
      launchctl kickstart -k "gui/$(id -u)/com.eharness.collect" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "$LAUNCHD_PLIST"
      how="launchd(com.eharness.collect)"
    elif [ -f "$SYSTEMD_UNIT" ] && systemctl --user start eharness-collect 2>/dev/null; then
      how="systemd(eharness-collect)"
    else
      nohup $BIN collect --port "$PORT" >>"$EH_HOME/collect.log" 2>&1 &
      echo $! >"$PIDFILE"; how="nohup(pid $!, 로그 $EH_HOME/collect.log)"
    fi
    for _ in $(seq 1 20); do health && break; sleep 0.5; done
    if health; then echo "기동: $how"; report
    else echo "기동 실패: $how — $EH_HOME/collect.log 확인" >&2; exit 1; fi ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      pid=$(cat "$PIDFILE"); kill "$pid" 2>/dev/null && echo "중지: pid $pid" || echo "이미 종료됨(pid $pid)"; rm -f "$PIDFILE"
    elif health; then
      echo "init.sh 가 띄운 프로세스가 아님 — 서비스로 관리: launchctl bootout gui/\$(id -u)/com.eharness.collect | systemctl --user stop eharness-collect"; exit 1
    else echo "실행 중 아님"; fi ;;
  *) echo "usage: init.sh [start|status|stop] [--port N]" >&2; exit 2 ;;
esac
