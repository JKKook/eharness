#!/bin/bash
# UserPromptSubmit: 사용자 입력 제출 → 출력(추론) 생성 시작 시각 기록
input=$(cat)

[ -n "$(jq -r '.agent_id // empty' <<<"$input")" ] && exit 0

sid=$(jq -r '.session_id // "default"' <<<"$input")

dir="$HOME/.claude/hook-state"; mkdir -p "$dir"
f="$dir/$sid.state"
# shellcheck disable=SC1090
[ -f "$f" ] && source "$f"

# 질문 텍스트 저장 (완료 알림에 표시용, 앞 200자)
# head -c는 바이트 단위라 한글이 중간에 깨짐 → jq 슬라이싱(글자 단위) 사용
# 슬래시 명령/내부 알림 턴은 <command-name>·<task-notification> 등 태그가 프롬프트에
# 그대로 들어오므로 태그를 제거하고, 남는 게 없으면 빈 값(→ 기본 문구 대체)으로 둔다
jq -r '.prompt // ""
  | gsub("<[^>]*>"; " ")
  | gsub("[\r\n\t]"; " ")
  | gsub(" +"; " ")
  | gsub("^ +| +$"; "")
  | .[0:200]' <<<"$input" > "$dir/$sid.prompt"

now=$(date +%s)
cat > "$f" <<EOF
STATE=thinking
THINK_START=$now
TURN_START=$now
LAST_TOOL="${LAST_TOOL:-}"
LAST_SECS=${LAST_SECS:-0}
COUNT=0
EOF
exit 0
