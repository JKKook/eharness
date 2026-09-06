# init (관측 시작) 스펙

> 세션 안에서 수집기(로컬 파이썬 서버)를 켜고 관측 준비 상태를 확인한다. 2026-09-06.

```yaml
capability: init
why:    decisions.md#2026-09-06-init          # Windows(WSL) 설치에서 launchd 전용 collect --install 불가 + 수집기 죽은 상태 인지 지연
what:   ~/.eharness/collect.pid               # init이 nohup으로 띄운 수집기 pid만 소유. 서비스(launchd/systemd)·settings.json은 소유하지 않음
how:    [skill:cctv-init]                     # init.sh 포함. 훅 없음
when:   [manual]                              # 사용자가 관측 시작/상태 확인을 지시할 때, 다른 cctv 스킬이 "수집기 응답 없음"일 때
where:  global
who:    all-sessions · no-human-gate          # 읽기 전용 서버 기동 — 게이트·차단 없음
```

## 문제
수집기가 죽어 있으면 훅 이벤트가 버려지고 cctv-register·cctv-status가 "수집기 응답 없음"으로 끝난다.
그때마다 사람이 터미널에서 `eharness collect`를 따로 띄워야 했고, 상시 등록(`collect --install`)은 launchd 전용이라
Windows(WSL2)·Linux에서는 쓸 수 없다(2026-09-06 Windows 설치 가이드 작성 중 확인). 세션에게 "cctv 켜"라고 말하면 끝나야 한다.

## 최소 설계
스킬 `cctv-init` 하나. 동봉 `init.sh`가:
1. `GET /health`로 생존 확인 — 살아 있으면 기동 없이 보고만
2. 아니면 플랫폼 순서로 기동: macOS launchd plist 있으면 `kickstart` → Linux systemd 유닛 있으면 `start` → 둘 다 없으면 `eharness collect` nohup(+pid 파일)
3. 보고: 수집기 주소, 살아있는 세션 수(`/api/sessions`), 훅 배선 on/off(`eharness hooks`)
`stop`은 자기 pid 파일의 프로세스만 종료(서비스는 안내만). settings.json·훅은 건드리지 않는다.

## verify
`tests/test_init.py` — 빈 포트에서 `status` exit 1, `start`로 실제 서버 기동 후 `/health` ok, `stop`으로 종료·pid 파일 제거.
설치 후 임의 세션에서 `init.sh status` → 실행 중 보고 + 훅 on 목록.

## 되돌림
`eharness wire init --uninstall` — `~/.claude/skills/cctv-init/` 제거(설정 변경 없음). `~/.eharness/collect.pid`는 `stop`이 지움.
