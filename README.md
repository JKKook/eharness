# eharness

한 머신의 모든 Claude Code 세션을 **밖에서** 관측하는 개인용 운용 하네스.
**규칙: eharness 훅은 관측만 한다 (exit 0 / 빈 응답, 차단 없음).** 세션 안의 판단·게이트는 khaness 등 세션 내 워크플로우의 몫.

```
eharness ps [--json] [--all] [--subagents]   # 세션 표 1회
eharness watch [N]                            # N초마다 갱신 (터미널 pane에 고정)
eharness collect [--install|--status|--uninstall]  # 127.0.0.1:7477 수집기 + 대시보드 / launchd 상주 등록
#   GET /            대시보드 (cmux: `cmux open http://127.0.0.1:7477/ --no-focus`)
#   GET /api/sessions (백그라운드 3초 주기 계산 → 즉시 응답, took_ms 포함), /api/events?since=|limit=&sid=   JSON
eharness events [-f] [--sid X] [--days N] [--json]  # 이벤트 버스 조회
eharness doctor                               # 비공개 포맷 필드 존재 점검
```

## 데이터 소스 (전부 읽기 전용)
| 지표 | 소스 |
|---|---|
| 세션 목록·busy/idle | `~/.claude/sessions/<pid>.json` |
| 작업 제목, 토큰 트래픽, 도구 카운트, ctx 근사치(`~` 표시) | `~/.claude/projects/<slug>/<sid>.jsonl` (+ `<sid>/subagents/`) |
| 지금 실행 중인 도구 | `~/.claude/hook-state/<sid>.state` (기존 tool-start/end 훅) |
| ctx 실제값·누적 비용 | `~/.claude/hook-state/<sid>.ctx` (statusline.sh가 기록) |
| 이벤트 시계열 | `~/.eharness/events/YYYY-MM-DD.jsonl` (hooks type:http → `eharness collect`) |

## 대시보드
- 상단 타일: 세션 수(busy/idle), 오늘 비용(세션별 바), 분당 이벤트(60분 스파크라인), 도구 실패 수, 평균 ctx.
- 활동 타임라인: 세션별 스윔레인. 연한 파랑 = 턴(prompt→stop), 진한 파랑 = 도구 실행(Pre→PostToolUse), 빨간 마름모 = 실패. 15m/1h/4h.
- 표: ctx 게이지(80%↑ 빨강, `~`=근사치) · ctx 추세 스파크라인 · 비용 인라인 바.
- 세션 표시 이름은 **대화 제목(ai-title)** → 마지막 질문 → 레지스트리 이름 순 폴백. 레지스트리 이름은 작은 글씨(statusline `[이름]`과 매칭).
- 영역(전체 지표·타임라인·세션 목록·최근 이벤트)마다 `접기/펼치기` 토글, 상태는 localStorage(`eh.sec`)에 저장.
- 차트는 배경 채움 없이 마크만(막대/선), 각 차트에 항목·최대값·시간 범위 캡션을 HTML로 표기. 분할 칸의 차트 SVG에는 텍스트를 넣지 않아(`preserveAspectRatio=none`) 늘어나도 깨지지 않음.
- 세션 목록은 **트리(cmux 사이드바 구조) / 표** 토글. 트리는 `cmux tree --all --json`으로 윈도우 → 그룹 → 워크스페이스(#n) → 탭(surface)을 만들고 세션을 **tty**로 surface에 붙인다(실패 시 워크스페이스 id). 그룹(사이드바 폴더)은 CLI가 노출하지 않아 cmux가 실시간 저장하는 `~/Library/Application Support/cmux/session-com.cmuxterm.app.json`의 `tabManager.workspaceGroups` + 워크스페이스 `groupId`로 읽는다(`terminal.cmux_groups`). 그룹의 접힘/고정 상태도 함께 읽어 트리 기본값으로 사용. 세션 없는 탭(셸·브라우저)은 흐리게 표시, 노드별 접기 상태는 localStorage(`eh.tree`).
- 보기 탭 2개: **전체**(요약 전용 — 타일 + 타임라인 + 표(제목·터미널·상태·컨텍스트·비용·토큰·턴·가동) + 이벤트; 세션별 트래킹 컬럼은 없음) / **분할**(살아있는 세션을 최대 24칸 그리드, 작업 중 우선·왼쪽 파란 테두리, 칸 = 터미널 #·제목·상태·지금 실행 중·마지막 질문·활동 미니 타임라인(전체 타임라인과 같은 표기: 턴 띠/도구 막대/실패/지금, 칸 안에 범례·시간축)·컨텍스트/비용/턴; "작업 중만" 필터; 분할 상단에 cmux 폴더 기준 카테고리 필터(전체/ETHAN/… + 기타, 선택 기억). 24칸 초과분은 마지막 칸에 `+n`으로 표시.
- **터미널 컬럼**: 세션 pid의 환경변수(`ps -E`)에서 `CMUX_WORKSPACE_ID`를 읽고 `cmux workspace list --json`과 조인 → cmux 사이드바 순서 `#n` + 탭 제목(+tty). cmux 소켓은 "cmux 안에서 시작된 프로세스만" 허용하므로 launchd 수집기는 세션 env의 `CMUX_SOCKET_CAPABILITY`로 인증한다(토큰은 API에 노출하지 않음). 진단: `GET /api/debug`.
- 라벨은 한국어 + 단위, 헤더/타일 hover 툴팁, 상단 `지표 설명` 버튼으로 정의 표.
- 터미널 statusline 1줄에 같은 세션 이름이 `[ethan-6c]`로 표시됨(`~/.claude/statusline.sh`, `hook-state/<sid>.name` 캐시) — 표와 터미널을 눈으로 매칭.
- 색: dataviz 기본 팔레트(계열 파랑 + 상태 빨강), 라이트/다크 검증 통과.

## 세션 간 통신 그룹
- 트랜스크립트에서 `SendMessage` tool_use의 `to`(송신)와 `<cross-session-message from=… from-name=…>`(수신)를 집계(`transcript.comm`, 본문 미저장). 수집기가 레지스트리의 `messagingSocketPath`/`name`으로 살아있는 세션에 매핑하고 union-find로 연결 요소 → `comm_group`(1..), `comm_peers`(살아있는 상대: 보냄/받음/마지막), `comm_other`(종료·미확인 상대).
- 전체 보기 **세션 통신 그래프** 영역 — `2D | 3D` 전환(기억됨). 2D = 아크 다이어그램(같은 통신 그룹을 나란히 두고 그룹 띠 `G1 · n`으로 감쌈; 노드 한 줄 — 살아있는 세션 그룹순, 종료된 상대는 오른쪽 끝·점선; 위쪽 호 = 메시지 방향(화살촉)·굵기/숫자 = 누적 횟수; 주황 = 선택 범위 내 실제 전송 이벤트). 통신 기록 없는 세션은 기본 숨김(토글). **관리** 버튼: 수동 그룹(이름으로 묶기)·통신 링크(A↔B, 점선) 등록 — `GET/POST /api/manual` → `~/.eharness/manual.json`, 세션 재시작 시 이름으로 재매칭, 수동 그룹 이름이 G번호 대신 라벨로. 3D = 의존성 없는 Canvas 투영: 통신 그룹마다 섬(원판), 종료된 상대는 높은 섬, 메시지는 공중의 3D 호 + 화살촉(굵기 = 횟수, 주황 = 최근), 드래그 회전·휠 줌·자동 회전(prefers-reduced-motion 시 정지), hover 툴팁, **타임라인 재생**(▶/배속/슬라이더 — 범위 내 메시지를 시간 순 펄스로, 호 굵기·횟수는 시점 누적; 슬라이더 끝=라이브, 라이브에선 방금 메시지 자동 펄스; `?demoflow=1`은 화면 전용 가짜 흐름으로 애니메이션 미리보기), 장면을 캔버스에 자동 맞춤. URL 해시 `#grid`(분할 시작), `#comm3d`(3D 그래프 시작). 접기 가능.

## 검증 방법 (브라우저 창 띄우지 않기)
- 문법: `node -e` 로 `<script>` 블록 `new Function` 검사, `python3 -m unittest discover -s tests`.
- 화면: 헤드리스 Chrome CLI — `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --user-data-dir=<임시> --window-size=1200,760 --virtual-time-budget=9000 --screenshot=<out.png> http://127.0.0.1:7477/#comm3d`. Playwright MCP/`cmux browser`는 사용자 화면에 탭·pane을 띄우므로 쓰지 않는다.
- 분할 칸 테두리 색 = 그룹 색(`--g1..--g6`, dataviz 범주형에서 파랑 제외), 배지 `↔ G1 · n`, 옵션 줄 범례; 전체 보기의 트리/표/타임라인엔 색점. 이벤트 버스는 SendMessage의 `to`만 기록해 "메시지 전송 → 상대"로 표시.

## 실행 모델
- 뷰어(`ps`/`watch`)는 터미널이 열려 있을 때만 도는 프로세스. 상태는 전부 파일에 있어 닫았다 열어도 잃는 게 없다.
- 수집기(`collect`)는 훅 push를 받는 headless 리시버라 상시 필요 → `eharness collect --install`(launchd, KeepAlive).
- 수집기가 죽어도 세션은 영향 없음(훅 async·timeout). 그 구간 이벤트만 비고 폴링 소스로 보완.

## 이벤트 스키마 v1
`{v, ts, sid, event, tool?, tool_use_id?, agent_id?, agent_type?, cwd, permission_mode?, prompt_id?, ok?, source?}` — 메타데이터만. 도구 인자·결과·프롬프트 본문은 저장하지 않는다.

## 테스트
`python3 -m unittest discover -s tests`
