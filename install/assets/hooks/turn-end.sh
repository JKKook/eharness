#!/bin/bash
# Stop: 턴 종료 → 턴 소요시간/도구 수 요약 기록 + 완료 알림음
input=$(cat)

[ -n "$(jq -r '.agent_id // empty' <<<"$input")" ] && exit 0

sid=$(jq -r '.session_id // "default"' <<<"$input")

f="$HOME/.claude/hook-state/$sid.state"
# shellcheck disable=SC1090
[ -f "$f" ] && source "$f"

now=$(date +%s)
turn=$((now - ${TURN_START:-$now}))

# 전체 턴(질문 제출 → 응답 완료) 소요시간으로 예상치(EMA) 갱신
if [ -n "${TURN_START:-}" ] && [ "$turn" -gt 0 ]; then
  ema="$HOME/.claude/hook-state/turn-ema"
  est=$(cat "$ema" 2>/dev/null); [ -z "$est" ] && est=$turn
  new=$(( (est * 3 + turn + 2) / 4 )); [ "$new" -lt 5 ] && new=5
  echo "$new" > "$ema"
fi

cat > "$f" <<EOF
STATE=idle
LAST_TURN_SECS=$turn
LAST_TURN_TOOLS=${COUNT:-0}
LAST_TOOL="${LAST_TOOL:-}"
LAST_SECS=${LAST_SECS:-0}
COUNT=0
EOF

# 데스크톱 알림: 어떤 질문이 완료됐는지 표시 (창 포커스 여부와 무관하게 항상)
q=""
qfile="$HOME/.claude/hook-state/$sid.prompt"
[ -f "$qfile" ] && q=$(jq -Rrs '.[0:120]' "$qfile")
[ -z "$q" ] && q="응답이 완료되었습니다"
# osascript 문자열 이스케이프
q=${q//\\/\\\\}; q=${q//\"/\\\"}
if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${q}\" with title \"Claude Code\" subtitle \"응답 완료\"" >/dev/null 2>&1 &
elif command -v notify-send >/dev/null 2>&1; then
  notify-send "Claude Code · 응답 완료" "$q" >/dev/null 2>&1 &
fi
exit 0
