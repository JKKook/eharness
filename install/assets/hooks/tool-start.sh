#!/bin/bash
# PreToolUse: 도구 실행 시작 기록 → statusline이 "▶ <도구> 실행 중 Ns"를 표시
input=$(cat)

# 서브에이전트의 도구 호출은 제외 (메인 세션만 추적)
[ -n "$(jq -r '.agent_id // empty' <<<"$input")" ] && exit 0

sid=$(jq -r '.session_id // "default"' <<<"$input")
tool=$(jq -r '.tool_name // "?"' <<<"$input")

dir="$HOME/.claude/hook-state"; mkdir -p "$dir"
f="$dir/$sid.state"
# shellcheck disable=SC1090
[ -f "$f" ] && source "$f"

now=$(date +%s)
# idle 상태(또는 첫 실행)에서 도구가 돌기 시작하면 새 턴으로 간주
if [ "${STATE:-idle}" = "idle" ]; then
  TURN_START=$now
  COUNT=0
fi

cat > "$f" <<EOF
STATE=running
TOOL="$tool"
START=$now
LAST_TOOL="${LAST_TOOL:-}"
LAST_SECS=${LAST_SECS:-0}
COUNT=${COUNT:-0}
TURN_START=${TURN_START:-$now}
EOF
exit 0
