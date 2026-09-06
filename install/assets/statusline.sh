#!/bin/bash
# Claude Code custom statusline
# stdin으로 세션 JSON을 받아 2줄 출력:
#  1줄: 모델(색상) / 구독 한도(n% 사용 · 리셋, 계정 공통) / 디렉토리 / git 브랜치
#  2줄: [출력 생성 예상 프로그래스바(좌측)] / 누적 추론시간 / [컨텍스트 프로그래스바(우측)]
# 텍스트는 모델명을 제외하고 전부 터미널 기본 전경색. 색상은 바 막대에만 적용.
#
# 성능: 세션당 렌더 비용을 낮추기 위해 외부 프로세스 호출을 최소화한다.
# (jq 2회 · stat 1회 · git 1회. 시각 계산·포맷은 jq 안에서 끝내고, 나머지는 전부 bash 내장)

input=$(cat)

# ── 입력 JSON을 한 번에 파싱 (쉘 대입문으로 받아 eval). 현재시각도 jq 에서 함께 받아 date 포크를 없앤다 ──
eval "$(jq -r '
  "NOW_EPOCH=\((now|floor)|tostring|@sh)",
  "MODEL=\((.model.display_name // "?")|@sh)",
  "CWD=\((.workspace.current_dir // .cwd // "?")|@sh)",
  "SESSION_ID=\((.session_id // "default")|@sh)",
  "PCT=\(((.context_window.used_percentage // 0)|floor)|tostring|@sh)",
  "API_MS=\(((.cost.total_api_duration_ms // 0)|floor)|tostring|@sh)",
  "COST_USD=\(((.cost.total_cost_usd // 0)*10000|floor/10000)|tostring|@sh)",
  "CUR_RL=\((.rate_limits // {})|tojson|@sh)"
' <<<"$input" 2>/dev/null)"
[ -z "${NOW_EPOCH:-}" ] && NOW_EPOCH=0
[ -z "${MODEL:-}" ] && MODEL="?"
[ -z "${CWD:-}" ] && CWD="?"
[ -z "${SESSION_ID:-}" ] && SESSION_ID="default"
[ -z "${PCT:-}" ] && PCT=0
[ -z "${API_MS:-}" ] && API_MS=0
[ -z "${COST_USD:-}" ] && COST_USD=0

# ── eharness(M2): 실제 컨텍스트 점유율·누적 비용을 세션별 .ctx 파일로 노출 (값이 바뀔 때만 원자적으로 씀) ──
CTX_FILE="$HOME/.claude/hook-state/${SESSION_ID}.ctx"
CTX_LINE="CTX_PCT=${PCT}
COST_USD=${COST_USD}"
if [ ! -f "$CTX_FILE" ] || [ "$(<"$CTX_FILE")" != "$CTX_LINE
TS=${CTX_TS:-}" ]; then
  CTX_TS=$NOW_EPOCH
  printf '%s\nTS=%s\n' "$CTX_LINE" "$CTX_TS" > "$CTX_FILE.tmp.$$" 2>/dev/null && mv -f "$CTX_FILE.tmp.$$" "$CTX_FILE" 2>/dev/null
fi
[ -z "${CUR_RL:-}" ] && CUR_RL='{}'

# 계정(구독) 사용량 한도 — 세션 JSON엔 "그 세션의 마지막 응답 시점" 스냅샷이 실려 와서
# 놀고 있는 터미널은 옛 값을 보여준다 → 전 세션 공유 캐시와 병합해 항상 최신 값으로 통일.
# 신선도 판정: 윈도우가 다르면 resets_at이 늦은 쪽. 같은 윈도우면 "최근 활성 세션"의
# 스냅샷만 캐시를 덮어쓴다(쓰기 게이트) — 사용%가 하향 조정돼도 그대로 반영되고,
# 유휴 터미널의 옛 스냅샷은 읽기 전용이라 캐시를 오염시키지 못한다.
RL_CACHE="$HOME/.claude/hook-state/rate-limits.json"
STATE_FILE="$HOME/.claude/hook-state/${SESSION_ID}.state"
mkdir -p "$HOME/.claude/hook-state"

# 훅 상태 파일은 한 번만 읽는다 (RL 신선도 판정 + 좌측 프로그래스바 양쪽에서 사용)
RL_ACTIVE=0
if [ -f "$STATE_FILE" ]; then
  # shellcheck disable=SC1090
  source "$STATE_FILE"
  RL_MTIME=$(stat -f %m "$STATE_FILE" 2>/dev/null || stat -c %Y "$STATE_FILE" 2>/dev/null || echo 0)   # BSD(macOS) → GNU(Linux) 순
  if [ "${STATE:-}" = "running" ] || [ "${STATE:-}" = "thinking" ] \
     || [ $(( NOW_EPOCH - RL_MTIME )) -le 300 ]; then RL_ACTIVE=1; fi
fi

# ── 캐시 병합 + 표시값 추출을 jq 한 번으로 ──
# 캐시는 문자열로 넘기고 jq 안에서 fromjson? 로 파싱 — 손상/부재 시에도 {} 로 안전 폴백
# ($(<file)) 은 cat 포크 없이 읽는다. 캐시 파일을 새로 만들지 않는다.
RL_RAW='{}'
[ -f "$RL_CACHE" ] && RL_RAW=$(<"$RL_CACHE")
eval "$(jq -r -n \
  --argjson cur "$CUR_RL" \
  --arg old_raw "$RL_RAW" \
  --arg active "$RL_ACTIVE" \
  --arg now "$NOW_EPOCH" '
  def fresher(cur; old):
    if cur == null then old elif old == null then cur
    elif (cur.resets_at // 0) > (old.resets_at // 0) then cur
    elif (cur.resets_at // 0) < (old.resets_at // 0) then old
    elif $active == "1" then cur
    else old end;
  # epoch → 24시간 이내면 "15:00", 그 외 "08/18"
  def fmt_reset(t; n): if (t - n) < 86400 then (t|strflocaltime("%H:%M")) else (t|strflocaltime("%m/%d")) end;
  ($now|tonumber) as $n
  | ((($old_raw | fromjson?) // {}) | if type == "object" then . else {} end) as $o
  | ({five_hour: fresher($cur.five_hour; $o.five_hour),
      seven_day: fresher($cur.seven_day; $o.seven_day)}
     | with_entries(select(.value != null))) as $m
  # 윈도우가 이미 리셋 시각을 지났으면: 새 윈도우 기준 0% 사용으로 표시
  | (($m.five_hour.resets_at) | if . == null then null else floor end) as $fr
  | (($m.seven_day.resets_at) | if . == null then null else floor end) as $sr
  | (if ($fr != null and $fr <= $n) then "0"
     else (($m.five_hour.used_percentage) | if . == null then "" else (floor|tostring) end) end) as $fp
  | (if ($sr != null and $sr <= $n) then "0"
     else (($m.seven_day.used_percentage) | if . == null then "" else (floor|tostring) end) end) as $sp
  | (if ($fr != null and $fr > $n) then $fr else null end) as $frv
  | (if ($sr != null and $sr > $n) then $sr else null end) as $srv
  | "RL_MERGED=\($m|tojson|@sh)",
    "RL_5H=\($fp|@sh)",
    "RL_7D=\($sp|@sh)",
    "RL_5H_RESET=\((if $frv == null then "" else ($frv|tostring) end)|@sh)",
    "RL_7D_RESET=\((if $srv == null then "" else ($srv|tostring) end)|@sh)",
    "RL_5H_FMT=\((if $frv == null then "" else fmt_reset($frv; $n) end)|@sh)",
    "RL_7D_FMT=\((if $srv == null then "" else fmt_reset($srv; $n) end)|@sh)"
' 2>/dev/null)"
[ -z "${RL_MERGED:-}" ] && RL_MERGED='{}'
if [ "$RL_ACTIVE" = "1" ]; then
  printf '%s' "$RL_MERGED" > "$RL_CACHE.tmp.$$" 2>/dev/null && mv -f "$RL_CACHE.tmp.$$" "$RL_CACHE" 2>/dev/null
fi

# ── 색상 (모델명 + 바 막대 전용) ──
RESET=$'\033[0m'; MAGENTA=$'\033[35m'
PURPLE=$'\033[38;2;108;113;196m'   # 출력 생성 바 (#6C71C4)
AMBER=$'\033[38;5;214m'            # ctx 바

draw_bar() { # 사용% 폭 → "██░░░░░░░░"
  local pct=$1 width=$2 filled bar="" i
  filled=$((pct * width / 100)); [ "$filled" -gt "$width" ] && filled=$width
  for ((i=0; i<width; i++)); do
    if [ "$i" -lt "$filled" ]; then bar+="█"; else bar+="░"; fi
  done
  printf '%s' "$bar"
}

fmt_dur() { # 초 → "1m 23s"
  local s=$1
  if [ "$s" -ge 3600 ]; then printf '%dh %dm' $((s/3600)) $((s%3600/60))
  elif [ "$s" -ge 60 ]; then printf '%dm %ds' $((s/60)) $((s%60))
  else printf '%ds' "$s"; fi
}

# ── 1줄: 모델 · 구독 한도(텍스트) · 디렉토리 · git ──
DIR_SHORT=${CWD/#$HOME/\~}
BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null)
USAGE_SEG=""
if [ -n "${RL_5H:-}" ]; then
  USAGE_SEG+="세션(5시간) ${RL_5H}% 사용"
  [ -n "${RL_5H_RESET:-}" ] && USAGE_SEG+=" · ${RL_5H_FMT} 리셋"
fi
if [ -n "${RL_7D:-}" ]; then
  USAGE_SEG+="${USAGE_SEG:+ | }주간 ${RL_7D}% 사용"
  [ -n "${RL_7D_RESET:-}" ] && USAGE_SEG+=" · ${RL_7D_FMT} 리셋"
fi
# ── eharness: 세션 이름(레지스트리 name, 대시보드 행과 동일). sid 별로 한 번만 조회해 캐시 ──
NAME_FILE="$HOME/.claude/hook-state/${SESSION_ID}.name"
if [ -f "$NAME_FILE" ]; then
  read -r SESSION_NAME < "$NAME_FILE"
else
  SESSION_NAME=$(jq -r --arg sid "$SESSION_ID" 'select(.sessionId==$sid) | .name // empty' "$HOME"/.claude/sessions/*.json 2>/dev/null | head -1)
  [ -n "$SESSION_NAME" ] && printf '%s\n' "$SESSION_NAME" > "$NAME_FILE" 2>/dev/null
fi
# ── eharness: 세션 그룹(대시보드 '그룹이동'이 hook-state/<sid>.group 에 기록) → [이름·그룹] ──
GROUP_FILE="$HOME/.claude/hook-state/${SESSION_ID}.group"
SESSION_GROUP=""
[ -f "$GROUP_FILE" ] && read -r SESSION_GROUP < "$GROUP_FILE"
LINE1="${MAGENTA}${MODEL}${RESET}"
if [ -n "${SESSION_NAME:-}" ] || [ -n "${SESSION_GROUP:-}" ]; then
  LINE1+=" ${AMBER}[${SESSION_NAME:-?}${SESSION_GROUP:+·${SESSION_GROUP}}]${RESET}"
fi
[ -n "$USAGE_SEG" ] && LINE1+=" | ${USAGE_SEG}"
LINE1+=" | ${DIR_SHORT}"
[ -n "$BRANCH" ] && LINE1+=" | ${BRANCH}"

# ── 좌측: 훅이 기록한 진행 상태 (출력 생성 예상 프로그래스바) ──
ACTIVITY=""
if [ -f "$STATE_FILE" ]; then
  NOW=$NOW_EPOCH
  case "${STATE:-}" in
    running|thinking)
      # 전체 응답(질문 제출 → 완료) 통합 프로그래스바: 예상시간 | 바 | 남은 시간
      ELAPSED=$((NOW - ${TURN_START:-NOW}))
      EST=""
      if [ -f "$HOME/.claude/hook-state/turn-ema" ]; then
        read -r EST < "$HOME/.claude/hook-state/turn-ema" 2>/dev/null
      fi
      [ -z "$EST" ] && EST=30
      [ "$EST" -lt 5 ] && EST=5
      TW=10
      TP=$((ELAPSED * 100 / EST)); [ "$TP" -gt 100 ] && TP=100
      TF=$((TP * TW / 100)); [ "$TF" -gt "$TW" ] && TF=$TW
      TBAR=""
      for ((i=0; i<TW; i++)); do
        if [ "$i" -lt "$TF" ]; then TBAR+="█"; else TBAR+="░"; fi
      done
      REMAIN=$((EST - ELAPSED))
      if [ "$REMAIN" -ge 0 ]; then
        ACTIVITY="예상 $(fmt_dur "$EST") | ${PURPLE}[${TBAR}]${RESET} ${TP}% | 남은 $(fmt_dur "$REMAIN")"
      else
        ACTIVITY="예상 $(fmt_dur "$EST") | ${PURPLE}[${TBAR}]${RESET} 100% | +$(fmt_dur "$((-REMAIN))") 초과"
      fi
      ;;
    idle)
      ACTIVITY="대기"
      [ -n "${LAST_TURN_SECS:-}" ] && ACTIVITY+=" (지난 턴 $(fmt_dur "$LAST_TURN_SECS") · ${LAST_TURN_TOOLS:-0} tools)"
      ;;
  esac
fi

# ── 우측: 컨텍스트 사용량 프로그래스바 ──
[ -z "$PCT" ] && PCT=0
CTX_SEG="${AMBER}[$(draw_bar "$PCT" 20)]${RESET} ${PCT}% ctx"

# 누적 추론(API) 시간
API_S=$(( ${API_MS%.*} / 1000 ))
MID_SEG="추론 $(fmt_dur "$API_S")"

# ── 마지막 줄 조립: [진행 상태] | 추론 | [ctx 바] ──
LINE2=""
[ -n "$ACTIVITY" ] && LINE2+="${ACTIVITY} | "
LINE2+="${MID_SEG} | ${CTX_SEG}"

printf '%s\n%s\n' "$LINE1" "$LINE2"
