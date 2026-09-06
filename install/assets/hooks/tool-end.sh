#!/bin/bash
# PostToolUse: 도구 완료 → 소요시간 기록, statusline이 "💭 출력 생성 중 (직전: <도구> Ns)"를 표시
input=$(cat)

[ -n "$(jq -r '.agent_id // empty' <<<"$input")" ] && exit 0

sid=$(jq -r '.session_id // "default"' <<<"$input")
tool=$(jq -r '.tool_name // "?"' <<<"$input")

f="$HOME/.claude/hook-state/$sid.state"
# shellcheck disable=SC1090
[ -f "$f" ] && source "$f"

now=$(date +%s)
dur=$((now - ${START:-$now}))

cat > "$f" <<EOF
STATE=thinking
THINK_START=$now
LAST_TOOL="$tool"
LAST_SECS=$dur
COUNT=$(( ${COUNT:-0} + 1 ))
TURN_START=${TURN_START:-$now}
EOF
exit 0
