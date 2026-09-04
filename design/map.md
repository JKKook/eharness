# 능력 지도 (map)

상태: **있음**(운용 중) / **부분**(일부 자산) / **없음**. 판정: **채택** / **보류** / **불채택**.
판정 변경은 반드시 `decisions.md`에 근거와 함께 기록.

## 바인딩 (charter의 역할 ↔ 현재 이름·구조. 가변 — 여기가 정본)

- 관측면 = **cctv** (`cctv/` 파이썬 패키지 — 2026-09-03 개명 완료)
- 제어면 = **scaffold**(자산, 첫 채택 능력 때 생성) + 배선기 **wire**(`wire/` 패키지, 설치 기록 `~/.eharness/wire.json`)
- 이벤트 버스 = `~/.eharness/events/*.jsonl`
- 설계 배경 문서(정본 아님): claude.ai/code 아티팩트 "eharness 리뉴얼 설계"

목표 형상 (폴더는 첫 채택 능력이 요구할 때 생성):

```
eharness/                ← 리포·CLI 이름은 우산(eharness) 유지
├── design/     charter · map · decisions · specs/
├── cctv/       관측 엔진 (현행 eharness/ 패키지 개명)
├── scaffold/   agents · skills · hooks · tools  (2차: loop · context · sandbox)
└── bin/        eharness wire <능력> --install/--uninstall/--status
```

## 능력

| 능력 | 상태 | 판정 | 근거 · 다음 행동 |
|---|---|---|---|
| 관측 (cctv) | 있음 | 채택 (운용 중) | M4 대시보드까지 완료. 소급 스펙 `specs/cctv.md` |
| 공통 배선 규약 (wire) | 부분 | **채택 → R1** | hooks --install 패턴을 스킬·에이전트·권한까지 일반화. 증거: 전역 스킬 수동 관리 반복 |
| 에이전트 통신 (comm) | 있음 | 채택 (운용 중) | 2026-09-04 배선 — `cctv-register` 스킬(자기 sid 해석 → parent/child/group API). 훅 없음(SubagentStart 제외 결정) |
| 실측 테스트 게이트 (probe) | 있음 | 채택 (운용 중) | 2026-09-04 배선 — `probe-playwright` 스킬: 루프 에러가 실측 필요 시 **사용자 질문 승인 후에만** Playwright 진행(최초 human-approve 능력). no-browser 원칙의 공식 예외 경로 |
| 관제 요약 (status) | 있음 | 채택 (운용 중) | 2026-09-04 배선 — `cctv-status` 서브에이전트(첫 agent 자산): API 대형 JSON을 대신 읽고 ≤15줄 요약만 부모 반환(charter §4 격리·요약 기준 1호 적용). 에이전트는 지연 로드됨(즉시 아님·재시작 불요 — 2026-09-04 정정) |
| 지시 분배 (dispatch) | 있음 | 채택 (운용 중) | 2026-09-04 배선 — `cctv-dispatch` 스킬: **리더 전용**(children 없으면 발송 중단·등록 안내, 계층이 곧 권한), 자식(=팀원)별 지시를 SendMessage로 병렬 분배 + 회신 규약(결과 요약·잔여 수치화). 의존 comm. 실전 왕복 검증은 첫 사용 시 |
| khaness 퇴역·이관 | — | **완료 2026-09-04** | 이관 판정표 실행 완료 — guard-policy만 보류 후보로 khaness 리포에 보존 |
| 골 온톨로지 (goal) | 없음 | 보류 | what 영토(`~/.eharness/state/`) 1호 후보. 장기 다세션 작업에서 목표 유실 증거 2회 시 재판정 |
| 플랜/런타임 분리 | 없음 | 보류 | 플랜은 spec 스킬군에 있음. 런타임 가드 상태파일의 pain 증거 대기 |
| 드리프트 대조기 (audit) | 없음 | 보류 (연장) | 선언↔실측 대조(설계 문서 S7). 조건(능력 3개)은 2026-09-04 도달했으나 실측 데이터 부족 — **2026-09-18 재판정** |
| 가드 (파괴 명령 거부 등) | 없음 | 보류 | khaness guard-policy에서 아이디어 이관. 사고 증거 발생 시 재판정 |
| OTLP 내보내기 | 없음 | 보류 (P2) | 주간 비용 집계 필요성 생기면 |
| 딥인터뷰·PRD·플래닝 | 자산 있음 | 불채택 | spec-init / design-to-spec / spec-build가 담당 — 재발명 금지 |
| 베리파이/픽스 루프 | 자산 있음 | 불채택 | spec-verify · /code-review가 담당 |
| 팀 토폴로지 (스타·공유 버스) | 자산 있음 | 불채택 | Claude Code Agent/SendMessage/Agent Teams + cctv 관측으로 충분 |

## 구성 요소 커버리지 (charter §4 유형 ↔ 현재 바인딩. 2026-09-04 공식 문서 대조)

공식 구성 요소 실측(code.claude.com/docs 기준): 기존 9개 중 8개 유지, verifier는 "verification/check"로
표현 변경, 신규 = Skills · Plugins · Workflows · Agent Teams · Auto Memory · `.claude/rules/` · Tool Search.

| 구성 요소 | 우리 상태 | 비고 |
|---|---|---|
| 지침 (전역 CLAUDE.md — AGENTS.md 아님, CC는 CLAUDE.md만 읽음) | 사용 중 | 4원칙 + 하네스 안내. §4 프루닝 기준으로 정기 리뷰 |
| `.claude/rules/` (경로별 조건 규칙) | 미사용 — 후보 | 전역 CLAUDE.md가 비대해지면 구조화 대상 |
| Skills (온디맨드 지침) | **사용 중** | comm 능력(cctv-register) + spec 스킬군(외부 자산) |
| 훅 | 관측면만 사용 | 제어면 훅은 비어 있음 — 가드 능력(보류)이 첫 후보 |
| 도구 / MCP | 규약 커버 | Playwright MCP는 전역 등록(외부 자산). 사용 규약 = probe 능력(승인 게이트). 그 외 MCP는 수요 시 |
| 서브에이전트 · Workflows · Agent Teams | 관측 + 자산 1 | 제품 기능은 cctv가 관측. 자체 자산은 `cctv-status`(status 능력) 1개 — 격리·요약 반환 기준 준수. 오케스트레이션은 여전히 안 만듦 |
| 검증 (verification) | 부분 | 설계층은 게이트 5 + 스펙 verify. 작업 루프 판정부는 비어 있음(아티팩트 S9, R4 후보) |
| 컨텍스트 관리 (Auto-compaction · Tool Search) | 제품 기능 | 우리 몫은 §4 상시/온디맨드 분리 기준 준수 |
| Auto Memory | 사용 중 | 프로젝트·피드백 기억이 자동 축적 — 별도 설계 불요 |
| Plugins (skills·agents·hooks·MCP 번들) | 보류 | **wire의 배포 대안** — scaffold를 외부 배포할 일이 생기면 plugin manifest 전환 재판정 |
| 권한·샌드박싱 (5모드) · Checkpointing · Managed Settings · Workspace Trust | 제품 기능 | 개인용 단일 사용자라 하네스 설계 불요 — who 선언(§4 권한 기준)으로만 관여 |

## khaness 이관 판정표 (R3 실행 목록)

khaness 실측: 에이전트 44개, 스킬·명령 대규모(debate/DGE/gsd 계열), hooks.json, config/guard-policy.yaml.
전역 배선은 `/usr/local/bin/run-hrs` + `~/.claude/commands/run-hrs.md` + 전역 CLAUDE.md의 run-hrs 지침뿐(전역 settings.json에 khaness 훅 없음 — 프로젝트별 배선 방식).

| khaness 자산 | 판정 | 근거 |
|---|---|---|
| DGE 루프·debate 엔진(Planner/Critic/Architect) | 버림 | spec 스킬군·/plan과 중복. 리포는 보존(삭제 안 함) |
| 에이전트 44종 | 버림 (개별 소급 가능) | 대부분 기본 기능·spec 스킬군과 중복. 특정 에이전트가 그리워지면 증거로 개별 채택 |
| evaluator·validator 스택 | 버림 | spec-verify · /code-review 담당 |
| 2-Strike Rule (실패→영구 규칙화) | **아이디어 흡수됨** | S6 증거 기반 채택 루프가 동형 — 별도 이관 불요 |
| guard-policy.yaml (파괴 명령 거부·민감 파일 보호) | **이관 후보 (보류)** | 유일하게 겹치지 않는 실용 자산. "가드" 능력으로 map에 등재, 증거 시 채택 |
| run-hrs · run-hrs.md · 전역 CLAUDE.md 지침 | **퇴역 완료 2026-09-04** | 심링크 제거, run-hrs.md는 khaness/retired-global/ 보존, CLAUDE.md는 "하네스=eharness" 안내로 교체. 잔존: practice/spec·spec-test의 프로젝트 배선(범위 밖) |

## 로드맵 (고정은 R3까지 — 이후는 charter §2 게이트가 결정)

- R0 헌장·지도 — **완료 2026-09-03** (본 디렉터리)
- R1 배선기 wire (+관측 패키지 cctv 개명) — **완료 2026-09-03**
- R2 1호 능력 comm (계층 자동 등록) — **완료 2026-09-04**
- R3 khaness 퇴역 — **완료 2026-09-04**
- R4+ 로드맵이 아니라 채택 게이트가 결정. R5 후보: 드리프트 대조기(능력 3개 배선 후 재판정)
