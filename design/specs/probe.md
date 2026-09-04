# probe (실측 테스트 게이트) 스펙

> 작업 루프에서 에러가 정적 검증으로 판정 불가할 때, 사용자 승인 후에만 Playwright 실측 테스트로
> 승격한다. "브라우저를 띄우지 않는다" 원칙의 공식 예외 경로. 2026-09-04.

```yaml
capability: probe
why:    decisions.md#2026-09-04-게이트-통과-probe   # 무단 브라우저 실행 교정 반복 + 사용자 요청
what:   없음                                       # 무상태 — 소유 데이터 없음
how:    [skill:probe-playwright]                   # Playwright MCP는 외부 자산(이미 전역 등록)
when:   [on-demand]                                # 루프 중 에러가 실측 필요로 판정될 때 스킬 트리거
where:  global
who:    all-sessions · human-approve               # 진행 전 반드시 사용자 질문 — 최초의 사람 게이트 능력
```

## 문제
에러 검증이 양극단으로 실패해 왔다: 허락 없이 브라우저를 띄우거나(반복 교정됨),
정적 검사만으로 "될 것"이라 보고하고 실제 화면에서 깨지거나. 중간 경로(승인 게이트)가 없었다.

## 최소 설계
스킬 `probe-playwright` 하나(스크립트 없음 — 지침만):
1. 판정 기준: 루프 중 에러가 브라우저 동작·화면이 관건이라 정적/헤드리스로 재현·판정 불가할 때만.
2. 반드시 먼저 질문: "현재 발생한 오류는 실제 테스트가 필요합니다. Playwright로 테스트를 진행하시겠습니까?"
3. 승인 시: Playwright MCP로 최소 범위(작은 뷰포트, 해당 페이지만) 실측 → 끝나면 탭 정리.
   거부 시: 헤드리스·정적 검증으로 계속하고 한계를 보고.

## verify
`wire probe --install` 후 스킬이 세션 스킬 목록에 노출되는지. 실전 검증(질문→승인→실측 흐름)은
첫 해당 에러 발생 시 확인하고 decisions에 기록.

## 되돌림
`eharness wire probe --uninstall` — 스킬 제거뿐(설정·상태 변경 없음). Playwright MCP 등록은 외부 자산이라 무관.
