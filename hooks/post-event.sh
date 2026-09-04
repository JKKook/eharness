#!/bin/sh
# eharness 관측 훅 (async): 훅 입력 JSON을 그대로 수집기로 전달. 관측 전용 — 절대 차단하지 않는다(항상 exit 0).
# 수집기가 없으면 연결 거부로 즉시 끝난다(-m 2 = 최대 2초). -H 'Expect:' 는 curl의 100-continue 1초 대기 방지.
curl -s -m 2 -o /dev/null -H 'Expect:' -H 'Content-Type: application/json' --data-binary @- "http://127.0.0.1:${EHARNESS_PORT:-7477}/hook" >/dev/null 2>&1
exit 0
