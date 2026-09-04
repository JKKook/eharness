# cctv (관측) 스펙 — 소급 작성

> R0 verify용: 이미 운용 중인 능력을 TEMPLATE로 작성해 6하가 채워지는지 확인. 2026-09-03.

```yaml
capability: cctv
why:    decisions.md#2026-09-01   # 세션 14개 동시 운용 시 상태 파악 불가 → 관측 버스는 LLM 밖
what:   ~/.eharness/{events/, manual.json} + row schema v1 (API 응답)
        # 예외적 ~/.claude 쓰기: hook-state/<sid>.group 캐시 (charter §1 화이트리스트)
how:    [package:cctv/ (collect·collector·bus·sources·view),
         hook:10종(post-event.sh async), script:statusline.sh(.ctx 기록), launchd:com.eharness.collect]
when:   [daemon(launchd 상주 + 3초 폴링), hook:SessionStart/End·UserPromptSubmit·Pre/PostToolUse(+Failure)·Stop·SubagentStart/Stop·Notification]
where:  global   # 머신 전체 세션, 서빙은 127.0.0.1:7477 한정
who:    all-sessions · no-human-gate   # 훅은 모든 세션에서 자동, 대시보드 조회·수동 그룹 지정만 사람
```

## 문제
동시 세션 14개(2026-09-01 실측)에서 "지금 누가 뭘 하나·컨텍스트가 얼마나 찼나"를 알 방법이
터미널 순회뿐이었다. 세션에 코드를 넣지 않고 밖에서 관측해야 함.

## 최소 설계
파일 3종(레지스트리·트랜스크립트·hook-state) 3초 폴링 + 훅 10종 async push → row v1 조립 →
JSON 캐시 → 대시보드/CLI. 상세는 설계 문서 아키텍처(M4) 섹션.

## verify
`eharness doctor` 통과 + `GET /health` ok + 대시보드에 살아있는 세션 표시.
(운용 중 — 현재 전부 통과 상태)

## 되돌림
`eharness hooks --uninstall` + `eharness collect --uninstall`(launchd 해제) + `~/.eharness/` 삭제 +
hook-state의 `.group`·`.ctx` 캐시 삭제. statusline.sh는 백업(.bak-20260902)으로 복원.
```

## 소급 작성에서 발견한 것 (템플릿 피드백)
- how가 스킬·훅 목록으로 안 끝나는 데몬형 능력이 존재 → TEMPLATE에 `package:` 값 허용 명시함.
- what에 "예외적 쓰기"를 적을 자리가 필요했음 → 주석으로 병기하는 관례 채택 (charter 화이트리스트 참조).
- 그 외 6하 전부 채워짐 — 게이트 5(선언) 통과. verify 완료.
