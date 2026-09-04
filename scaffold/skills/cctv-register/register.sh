#!/bin/bash
# cctv-register (capability: comm) — 이 세션을 관제 계층/그룹에 등록·해제
# usage: register.sh parent <이름> | child <이름> | clear | group <이름> | ungroup | status
set -euo pipefail
PORT="${EHARNESS_PORT:-7477}"
API="http://127.0.0.1:$PORT"
SESS_DIR="${EHARNESS_CLAUDE_HOME:-$HOME/.claude}/sessions"

# 프로세스 트리를 올라가며 세션 레지스트리에 있는 pid를 찾아 sid·이름 해석
p=$$
SID=""; NAME=""
while [ "$p" -gt 1 ] 2>/dev/null; do
  if [ -f "$SESS_DIR/$p.json" ]; then
    SID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sessionId"])' "$SESS_DIR/$p.json")
    NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("name") or "")' "$SESS_DIR/$p.json")
    break
  fi
  p=$(ps -o ppid= -p "$p" | tr -d ' ') || break
  [ -n "$p" ] || break
done
if [ -z "$SID" ]; then
  echo "ERROR: 프로세스 트리에서 Claude 세션을 찾지 못함 ($SESS_DIR)" >&2
  exit 1
fi

post() { # post <경로> <json필드들...>  (python이 json 조립)
  local path="$1"; shift
  curl -sS -m 5 -X POST "$API$path" -d "$(python3 -c '
import json,sys
d={}
for kv in sys.argv[1:]:
    k,v=kv.split("=",1)
    d[k]=v
print(json.dumps(d,ensure_ascii=False))' "$@")"
  echo
}

cmd="${1:-status}"; arg="${2:-}"
case "$cmd" in
  parent)  [ -n "$arg" ] || { echo "usage: register.sh parent <부모 세션 이름>" >&2; exit 2; }
           post /api/parent "sid=$SID" "name=$NAME" "parent_name=$arg" ;;
  child)   [ -n "$arg" ] || { echo "usage: register.sh child <자식 세션 이름>" >&2; exit 2; }
           post /api/parent "name=$arg" "parent_sid=$SID" "parent_name=$NAME" ;;
  clear)   post /api/parent "sid=$SID" "name=$NAME" ;;
  group)   [ -n "$arg" ] || { echo "usage: register.sh group <그룹 이름>" >&2; exit 2; }
           post /api/session-group "sid=$SID" "name=$NAME" "group=$arg" ;;
  ungroup) post /api/session-group "sid=$SID" "name=$NAME" ;;
  status)  curl -sS -m 5 "$API/api/sessions" | python3 -c '
import json,sys
sid=sys.argv[1]
for r in json.load(sys.stdin)["rows"]:
    if r["sid"]==sid:
        print(json.dumps({"sid":sid[:8],"name":r["name"],"parent":r.get("parent"),
                          "children":r.get("children"),"sgroup":r.get("sgroup")},ensure_ascii=False)); break
else: print("row not found (수집기 재계산 대기 ~3s 후 재시도)")' "$SID" ;;
  *) echo "usage: register.sh parent <이름> | child <이름> | clear | group <이름> | ungroup | status" >&2; exit 2 ;;
esac
