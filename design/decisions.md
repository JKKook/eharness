# 결정 기록 (append-only)

형식: `- YYYY-MM-DD [판정] 제목 — 근거 한 줄`

- 2026-09-01 [채택] 관측 버스는 LLM 밖(파일/HTTP) — SendMessage는 토큰 소모·턴 지연이라 버스로 쓰지 않음
- 2026-09-01 [채택] 폴링 우선, push(훅)는 정확도 필요 시 — 세션 무변경으로 당일 검증 가능
- 2026-09-03 [결정] khaness 퇴역 — eharness를 관측+제어 우산으로 리뉴얼 (사용자 결정)
- 2026-09-03 [채택] 축은 why(design)·how(scaffold) 2개만, what·when·where·who는 능력별 필수 선언 필드 — 다중 값 축은 폴더 불가 (설계 문서 S7)
- 2026-09-03 [채택] 채택 게이트 5종(증거·자산·경계·되돌림·선언) — 증거 소스는 events 버스
- 2026-09-03 [결정] 파이썬 패키지 eharness/ → cctv/ 개명 (R1 직전 실행) — eharness/eharness 중복 제거, "cctv 패키지=읽기 전용 코드만" 경계를 이름으로 강제
- 2026-09-03 [확정] R 로드맵: R0 헌장·지도 → R1 wire → R2 comm → R3 khaness 퇴역, R4+는 게이트 위임 (설계 문서 S8)
- 2026-09-03 [완료] R0 구축 — design/{charter,map,decisions,specs/TEMPLATE}. verify: cctv 소급 스펙 작성으로 템플릿 검증
- 2026-09-03 [템플릿 메모] cctv 소급 작성에서 발견: 데몬형 능력은 how가 스킬·훅 목록이 아니라 패키지 전체 — TEMPLATE의 how에 `package:` 값 허용 명시
- 2026-09-03 [규칙] 문서 SSOT 원칙 — charter는 불변 원칙만 담고, 가변 바인딩(이름·경로·목표 형상·로드맵·외부 링크)은 map/specs가 정본 (사용자 피드백: 문서 소실·명칭 변경에 견디게)
- 2026-09-03 [완료] 관측 패키지 eharness/ → cctv/ 개명 (사용자 실행) + bin 진입점·tests 임포트 수정, launchd 수집기 재시작으로 새 경로 가동 확인
- 2026-09-03 [설계] wire의 기계 판독 선언은 자산 파일에 둔다(스킬·에이전트 frontmatter capability, 훅 json의 events) — 스펙 yaml은 사람·에이전트용 정본이라 파싱하지 않되, 스펙 파일 부재 시 설치 거부로 게이트 5를 기계적으로 강제. where는 당분간 global만(project 설치는 수요 발생 시)
- 2026-09-03 [완료] R1 배선기 — wire/ 패키지(제어면, cctv 밖), `eharness wire <능력> --install/--uninstall/--status`, 설치 기록 ~/.eharness/wire.json, settings 병합은 백업·멱등·tmp+replace. verify: 더미 능력 왕복 후 settings diff 0 + 멱등 + 타인 소유 스킬 거부 (tests/test_wire.py, 전체 21개 통과)
- 2026-09-04 [게이트 통과] comm — ①증거: 대시보드 부모지정·그룹 지정을 수동 반복(2026-09-02~03, 계층·그룹 UI 작업 내내) ②자산: 기존 스킬 없음, 대시보드는 사람 전용 ③경계: 제어면(세션이 스스로 등록하는 스킬) 한 문장 ④되돌림: wire comm --uninstall ⑤선언: specs/comm.md 6하 완비 → 착수
- 2026-09-04 [수정] comm 범위에서 SubagentStart 훅 제외 — 그 훅은 세션 내부 서브에이전트 신호라 세션 간 계층과 무관(세션 내부는 이미 transcript가 관측). comm은 스킬 1개로 시작, 자동 감지는 증거가 생기면 별도 판정
- 2026-09-04 [완료] R2 comm — scaffold/skills/cctv-register(SKILL.md+register.sh, 프로세스 트리로 자기 sid 해석 → parent/child/clear/group/ungroup/status), `wire comm --install` 배선. verify: 실세션(ethan-87)에서 group r2-verify 등록→행 반영→ungroup 원복, 스킬 핫로드 확인, 전체 테스트 21개 통과. settings 무변경(훅 미사용)
- 2026-09-04 [조사] 하네스 구성 요소 공식 문서 대조(code.claude.com/docs) — 기존 9개 중 8개 유지, verifier→verification 표현 변경, CC는 AGENTS.md 아닌 CLAUDE.md만 읽음, 신규 7종(Skills·Plugins·Workflows·Agent Teams·Auto Memory·rules/·Tool Search). "모델 세대 재검증"은 공식 체크리스트 없음(프루닝 권고만) — 우리는 운영 규칙으로 채택
- 2026-09-04 [채택] charter §4 구성 요소 설계 기준(유형별 불변 원칙 7: 지침 적정고도·프루닝, 상시/온디맨드 분리, 훅=결정론만, 도구 우선·MCP, 서브에이전트=격리 목적, 검증=실행 가능+작업자/평가자 분리, 최소 권한) + 운영 규칙 4(모델 세대 변경 = 전 능력 재검증·감가 게이트). 커버리지 바인딩은 map에
- 2026-09-04 [게이트 통과] probe(실측 테스트 게이트) — ①증거: 브라우저 무단 실행 반복 교정(no-browser 피드백) + 정적 검증만으로 오판한 사례, 사용자 직접 요청 ②자산: Playwright MCP는 이미 전역 등록 — 없는 건 사용 규약뿐 ③경계: 제어면 스킬 ④되돌림: wire probe --uninstall ⑤선언: specs/probe.md. 훅이 아닌 스킬인 이유: "실측 필요" 판단이 개입되는 권고적 행동(charter §4)
- 2026-09-04 [게이트 통과] status(관제 요약 서브에이전트) — ①증거: 세션 상태 파악 시 /api/sessions 대형 JSON을 메인 컨텍스트로 읽거나 대시보드 왕복 반복, 사용자 요청 ②자산: 없음(대시보드는 사람 전용) ③경계: 제어면 자산 — 관측면 API의 소비자(charter §4 서브에이전트 기준: 컨텍스트 격리·요약 반환) ④되돌림: wire status --uninstall ⑤선언: specs/status.md. cctv 데몬 자체의 LLM화는 결정 1호(관측 버스는 LLM 밖) 위배로 불채택 — 조회·요약만 위임
- 2026-09-04 [게이트 통과] dispatch(리더→자식 지시 분배) — ①증거: 병렬 세션 조율을 터미널 왕복으로 수동 반복, 사용자 요청 ②자산: SendMessage는 있으나 계층 주소록·분배·회신 규약 없음 ③경계: 제어면 스킬 — 전송은 리더 세션 자신의 SendMessage(공식 경로, P3 결정 준수), 수집기는 전송하지 않음(관측면 무개입 유지) ④되돌림: wire dispatch --uninstall ⑤선언: specs/dispatch.md. 의존: comm(자식 조회) — 미설치 시 이름 직접 확인으로 폴백
- 2026-09-04 [검증 완료] dispatch 실전 왕복 — 리더 bibim-intel-agent-33(AG_TREND)가 팀원 2명(ethan-9d·bibim-pms-web-e9)에게 지시 각 2건 발송(02:51~52Z), 2분 내 회신 4건 수신. 버스 실측으로 확인, 해당 구간 서브에이전트 개입 0건(설계 일치 — 세션-대-세션 경로만). specs/dispatch.md verify 충족
- 2026-09-04 [수정] dispatch 리더 제한 + 용어 병기(사용자 요청) — children 비면 발송 중단·등록 안내만(직접 이름 폴백 제거, "계층이 곧 권한"), "자식=팀원" 병기·트리거 추가
- 2026-09-04 [정정] 에이전트 로드 실측 — "핫로드 안 됨"은 오판: cctv-status가 세션 중 지연 로드됨(즉시는 아니나 재시작 불요). status 능력 verify 기록 정정
- 2026-09-04 [완료] dispatch — scaffold/skills/cctv-dispatch(지침 전용: 자식 조회→서수↔이름 매핑 제시→SendMessage 분배+회신 규약→발송 대장). wire 배선·핫로드·자식 조회 경로 확인. 잔여: 실전 분배·회신 왕복 미검증(임의 세션 테스트 메시지 금지 원칙 — 첫 실사용 시 기록)
- 2026-09-04 [완료] status — scaffold 첫 agent 자산(cctv-status: API 조회→고정 형식 ≤15줄 요약, tools Bash만). wire 배선 후 새 세션 E2E 통과(세션 16개 요약 반환, 원시 JSON 없음). 실측 발견: **에이전트는 스킬과 달리 핫로드 안 됨(세션 시작 시 로드)**. 잔여: 요약 품질(장기 실행 판정이 uptime과 혼동됨)은 실사용에서 튜닝
- 2026-09-04 [보류 연장] 드리프트 대조기(C1) 재판정 — 조건(능력 3개 배선: cctv·comm·probe)은 도달했으나 comm·probe의 실측 데이터가 당일치뿐이라 대조 대상이 없음. 2주 운용 후(2026-09-18) 재판정. 구축 모드 종료 → 운용 모드 전환(이후 착수는 증거 2회 트리거로만)
- 2026-09-04 [완료] A4 wire 설치 전 자산 자동 검증(oh-my-claude 비교에서 채택) — 스킬 .sh는 bash -n, 훅 선언은 events 리스트·hook.command 필수. 지침 규칙을 도구 강제로 승격(테스트 2건 추가, 총 23)
- 2026-09-04 [완료] A2 잔여 수치화(Quantify the residual, khaness 이관) — 전역 CLAUDE.md 4원칙에 추가: 완료 주장 시 미해결·미검증 수와 검증 범위(X/Y) 보고, 절대 표현 금지
- 2026-09-04 [완료] A3 위협 모델 명문화(khaness 이관) — charter 운영 규칙: 게이트는 심층 방어, 진짜 경계는 커밋 diff의 사람 검토
- 2026-09-04 [완료] A1 git 리포 초기화 — 목적: 변경 이력·복구 기준·diff 리뷰 경계의 전제. 규칙: 변경은 의미 단위로 커밋(decisions 항목과 함께). 같은 날 원격 연결(사용자 제공): github.com/JKKook/eharness — 푸시는 gh JKKook 계정 전환 경유(이 머신 활성 계정은 ethan-outlier)
- 2026-09-04 [완료] 리포 CLAUDE.md 신설 — R0 때 누락(사용자 지적). design/ 정본 포인터 + 실수 방지 줄만(§4 프루닝 기준): 게이트 순서 강제, ~/.claude 직접 편집 금지, cctv 읽기 전용, 무개입 훅, verify 명령, decisions 기록 의무
- 2026-09-04 [완료] probe — scaffold/skills/probe-playwright(지침 전용 스킬: 판정 기준 3 + 질문 게이트 + 최소 범위 실측 + 탭 정리), `wire probe --install`. verify: 설치·status 확인, 실전(질문→승인→실측) 검증은 첫 해당 에러 때 기록 예정
- 2026-09-04 [완료] R3 khaness 퇴역 — ① /usr/local/bin/run-hrs 심링크 제거(복원: `ln -s ~/tools/khaness/bin/run-hrs /usr/local/bin/run-hrs`) ② ~/.claude/commands/run-hrs.md → ~/tools/khaness/retired-global/ 이동 보존 ③ 전역 CLAUDE.md run-hrs 섹션 → "하네스=eharness, khaness 퇴역" 안내로 교체(백업 CLAUDE.md.bak-r3-20260904). verify: PATH·commands·settings 모두 khaness 없음. khaness 리포는 보존(guard-policy 이관 후보 포함). 잔존: practice/spec·spec-test 프로젝트 .claude/settings.json에 khaness 배선 — 범위 밖(스크립트가 리포에 남아 안 깨짐), 해당 프로젝트 재사용 시 정리
