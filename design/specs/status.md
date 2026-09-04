# status (관제 요약 서브에이전트) 스펙

> 세션이 "다른 세션들 뭐 해?"를 물을 때, 서브에이전트가 수집기 API의 대형 JSON을 대신 읽고
> 부모에게 **요약만** 반환한다. charter §4 서브에이전트 기준(격리 목적·요약 반환)의 1호 적용. 2026-09-04.

```yaml
capability: status
why:    decisions.md#2026-09-04-게이트-통과-status   # 대형 JSON 메인 컨텍스트 소모·대시보드 왕복 반복
what:   없음                                        # 무상태 — 읽기 전용 조회
how:    [agent:cctv-status]                         # scaffold 첫 에이전트 자산. 스킬 불요(에이전트 description이 트리거)
when:   [on-demand]                                 # 사용자가 관제 요약을 요청하면 메인 세션이 위임
where:  global
who:    all-sessions · no-human-gate                # 읽기 전용 조회라 게이트 불요
```

## 문제
관제 상태를 알려면 ① 사람이 대시보드로 왕복하거나 ② 세션이 `/api/sessions` 전체 JSON(세션 14개 × row v1)을
자기 컨텍스트로 읽어야 한다 — ②는 주의 예산을 크게 소모하고 매번 반복된다.

## 최소 설계
에이전트 `cctv-status` 하나: 수집기 API(`/api/sessions`, `/api/events`)를 Bash(curl+python3)로 조회해
고정 형식 요약(총괄 / 주의 필요 / 계층·그룹 / 특이 이벤트, ≤15줄)만 반환. 원시 JSON 반환 금지.
수집기가 죽어 있으면 그 사실과 복구 명령을 보고. cctv 데몬에는 어떤 변경도 없음(LLM-free 유지).

## verify
`wire status --install` 후 이 세션에서 Agent 도구로 `cctv-status`를 실제 호출 —
살아있는 세션 요약이 고정 형식·원시 JSON 없이 반환되는지.

## 되돌림
`eharness wire status --uninstall` — `~/.claude/agents/cctv-status.md` 제거뿐(설정·상태 무변경).
