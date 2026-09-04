# cctv 루프 실측 대장 (loop-log, append-only)

> 하네스 능력들이 실전에서 도는 **루프**(왕복 사이클)를 상시 측정·기록한다. 판정은 하지 않는다 —
> 여기 쌓인 수치가 charter §2 게이트 1(증거)·드리프트 대조기 재판정(2026-09-18)의 입력이 된다.
> 기록 주체: 관제 그룹 `loop-eng`에 등록된 기록 세션(자가 페이스 wakeup, 읽기 전용 조회만).
> 원천: 이벤트 버스 `~/.eharness/events/*.jsonl` + 수집기 API. 시각은 UTC(Z).

## 보유 임무 (장기 — /clear에 유실되지 않도록 여기 보관)

- **M1 C1 드리프트 대조기 재판정 준비 — 2026-09-18** (2026-09-04 05:3xZ 리더 ethan-87이 이관, 사유: 리더 터미널은 /clear 잦음).
  ① loop-log 2주치 실측을 근거로 채택/보류 재판정 자료 작성 — 판정 자체는 사용자·리더 승인 후 decisions에 기록
  ② 같은 날 "분기 리뷰": B1~B5 증거 카운터 점검 + 계측 상태(G1~G5 보강 여부) 리뷰를 loop-log 항목으로 정리
  ③ 리더가 G1~G5 보강 진행 중(버스에 skill명·agent_type·이벤트명 정규화·Notification msg·to_name 추가 예정) — 배선 통지 후 틱부터 새 필드 활용, 측정 스크립트 갱신

## 측정 루프 정의

| 루프 | 사이클 | 측정치 | 원천 이벤트 |
|---|---|---|---|
| L1 dispatch | 리더 SendMessage(to=이름) → 팀원 회신(to=uds:) | 발송·회신 건수, 첫 회신 지연(분), 10분 무회신 = 지연 신호 | PreToolUse tool=SendMessage |
| L2 turn | UserPromptSubmit → Stop | 프롬프트·Stop 수, 도구/프롬프트, 실패율, 미종결(pre−post−fail) | UserPromptSubmit·Stop·Pre/PostToolUse(+Failure) |
| L3 subagent | SubagentStart → Stop | 유형별 건수(cctv-status 사용 포함), Skill/Agent 호출 수 | SubagentStart/Stop·tool=Skill/Agent |
| L4 probe | 에러 → 승인 질문 → 실측 | 대리 지표: 브라우저 MCP 도구 실패 수(직접 신호 없음 — 아래 계측 공백) | PostToolUseFailure tool=mcp__* |
| L5 collector | 3초 폴링·훅 push | health, 행 수, took_ms, 스키마 이탈 이벤트 | /health·/api/sessions |

항목 형식: `### #NNNN YYYY-MM-DD HH:MMZ · 창 <since→now>` 아래 L1~L5 한 줄씩 + `발견`·`계측 공백`·`잔여`.
아무 변화 없는 틱은 기록하지 않는다(대장은 변화만 담는다).

## 계측 공백 (버스가 답하지 못하는 것 — 드리프트 대조기 증거)

- G1 `tool=Skill` 이벤트에 스킬 이름이 없다 → cctv-register·probe-playwright·cctv-dispatch 사용 횟수를 직접 셀 수 없음 (2026-09-04 발견)
- G2 `SubagentStop`의 `agent_type` 대부분 None(4일간 129건 중 121건) → Start와 짝 맞추기 불가
- G3 `sessionEnd`(소문자) 변형 1건(2026-09-04T00:57Z) — 이벤트명 스키마 이탈
- G4 `Notification`에 종류(source) 없음 69/69 → 입력 대기 vs 권한 요청 구분 불가
- G5 dispatch 회신은 `to=uds:` 소켓 경로만 남아 수신자 이름을 역해석해야 함(현재 발송 후 첫 uds 송신을 회신으로 추정)

## 항목

### #0001 2026-09-04 04:25Z · 창 2026-09-01→04 (기준선, 4일 4,879건)

- L1 dispatch: 리더 발송 6건(bibim-intel-agent-33→ethan-9d 4·bibim-pms-web-e9 2), 회신 확인 4건, 첫 회신 지연 0.5·0.7·2.3·3.1분. 무회신 2건 — 09-03 07:47Z(다음날까지 없음), **09-04 04:02Z ethan-9d(10분 무회신 = 회신 규약 v2 지연 신호 1호**, 04:06Z Notification 발생 → 입력 대기 추정, G4로 확정 불가)
- L2 turn: 일별 prompts 39/106/120/60 · tools/prompt 10.5→5.5→5.3→4.8 · fail% 4.2/3.3/3.8/1.4 · 미종결 0/6/4/1. 실패 도구: Bash 38 · Playwright/Chrome 11(09-01에만) · StructuredOutput 7 · Read 5 · Artifact 2 · Agent 1
- L3 subagent: general-purpose Start 6 · cctv-status 1(09-04 E2E) · claude-code-guide 1. Skill 호출 8 · Agent 호출 9 (스킬 종류 불명 — G1)
- L4 probe: 브라우저 MCP 실패 09-01 11건 → probe 배선(09-04) 이후 0건. 실전 질문→승인 흐름 관측 0회(스펙 verify 미충족 상태 유지)
- L5 collector: health ok · launchd pid 1499 running · 행 15 · took_ms 912 · 스키마 이탈 1(G3)
- 발견: dispatch 왕복은 정상 시 3분 내(4/4). 지연 신호 1건이 실측 첫 사례 — 팀원 자가 보고(soft 규약) 미이행 여부는 다음 틱에서 확인
- 잔여: 미검증 3(probe 실전 흐름, dispatch 지연 사례의 원인, G5 회신 매칭 정확도). 검증 범위 5/5 루프 측정 성공
- 추가 발견(04:30Z): **동일 리포 동시 편집 충돌 1건** — 기록 커밋 d636817 준비 중 다른 세션이 decisions.md에 "대시보드 헤더 CPU 표시" 줄을 추가하고 cctv/collector.py·dashboard.html을 미커밋 수정 중이었음. decisions 줄은 내 커밋에 딸려 들어감(코드는 그 세션 워킹트리에 남음). 리더/그룹 미등록 세션 간 같은 리포 작업은 관제가 잡지 못함 — 골 온톨로지·comm 자동 감지 재판정용 증거 1호

### #0002 2026-09-04 04:58Z · 창 04:25→04:58Z (29건, 세션 2)

- L1 dispatch: 발송 0 · 회신 0. #0001 지연 신호(04:02Z→ethan-9d) 지속 — 리더 bibim-intel-agent-33·팀원 ethan-9d·bibim-pms-web-e9 셋 다 04:04~05Z부터 idle·입력 대기(msg_state need). 무회신 원인 = 작업 정체가 아니라 팀원이 사용자 입력 대기로 전환(리더도 동시에 대기). 회신 규약의 "착수 보고"가 발송 전 단계에서 끊긴 사례
- L2 turn: prompts 1 · fail 0 · 미종결 0 (기록 세션 자신 포함)
- L3~L4: 없음 · L5: health ok · took_ms 994
- 잔여: #0001의 미검증 3 → 2 (지연 원인 확인됨)

### #0003 2026-09-04 05:41Z · 창 04:58→05:41Z (69건, 세션 3) — 계측 보강 배선 + 기록 세션 자신의 dispatch 왕복

- L1 dispatch: 리더 ethan-87→eharness-96(기록 세션) 발송 2건(05:38:11Z 임무 이관 · 05:39:52Z G 보강 통지). 1건 회신 0.5분(05:38:38Z), 2건은 본 항목 커밋 직후 회신. 리더 사칭 여부 확인 없이 접수함 — 계층(manual.json parents)에 ethan-87→eharness-96 등록은 없음 → "계층이 곧 권한" 규약이 수신 측에는 적용되지 않는 실측 1호
- 계측 보강(리더 배선, 05:39Z 수집기 재시작, 스키마 v1 유지 가산 필드): G1 `skill` · G2 `agent_type`/`subagent_type` · G3 이벤트명 정규화(sessionEnd→SessionEnd, 이후 이탈로 계수 안 함) · G4 Notification `msg` · G5 uds 발송 `to_name`. 측정 스크립트 v2로 갱신
- 보강 후 실측(05:39→05:41Z, 16건): G1 skill 채움 1/1(g-test 합성) · G4 msg 채움 1/1(합성, "permission") · G2 subagent 이벤트 0건 → 채움율 측정 불가(다음 실 subagent 때) · G5 uds 발송 0건(기록 세션 회신은 재시작 전 05:38Z라 to_name 없음 — 본 항목 직후 회신이 첫 실검증)
- L2 turn: prompts 9 · fail 0 · 미종결 2(진행 중 턴) · L3: 없음 · L4: 브라우저 MCP 실패 0 · L5: health ok · took_ms 692
- 잔여: G2 채움율·G5 to_name 실검증 2건 대기, 미검증 2 유지(probe 실전 흐름·회신 매칭 정확도는 G5 확인 시 해소)
- 추가(05:41:17Z): **G5 실검증 통과** — 기록 세션 회신 이벤트에 `to_name: ethan-87` 채움 확인(1/1). 회신 매칭이 소켓 역해석 추정에서 이름 확정으로 승격 → 잔여 미검증 2→1(probe 실전 흐름만 남음)
