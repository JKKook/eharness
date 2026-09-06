---
name: cctv-init
description: eharness 관측(cctv)을 시작 — 로컬 파이썬 수집기(127.0.0.1:7477)를 켜고 세션·훅 배선 상태를 보고. 사용자가 "cctv 켜", "관측 시작", "수집기 띄워", "cctv-init", "대시보드 안 떠"라고 하면 사용. 다른 cctv 스킬이 "수집기 응답 없음"으로 실패할 때도 사용.
capability: init
---

# cctv-init — 관측 시작

수집기(로컬 파이썬 HTTP 서버)가 살아 있어야 훅 이벤트가 쌓이고 대시보드·cctv-register·cctv-status가 동작한다.
이 스킬은 수집기를 **켜고** 준비 상태를 보고할 뿐, 세션·훅에 개입하지 않는다.

## 실행 방법

```bash
bash ~/.claude/skills/cctv-init/init.sh [start|status|stop] [--port N]
```

| 명령 | 뜻 |
|---|---|
| `start` (기본) | 이미 떠 있으면 그대로 보고. 아니면 상시 서비스(macOS launchd / Linux systemd)를 깨우고, 서비스가 없으면 `eharness collect`를 nohup으로 기동(pid는 `~/.eharness/collect.pid`) |
| `status` | 수집기 응답·살아있는 세션 수·훅 배선(on/off) 보고. 응답 없으면 exit 1 |
| `stop` | `start`가 nohup으로 띄운 프로세스만 중지. 서비스로 도는 수집기는 안내만 하고 건드리지 않음 |

## 절차

1. `start`를 실행하고 출력을 그대로 요약해 보고한다: 기동 방식(launchd/systemd/nohup), 세션 수, 훅 on/off.
2. 훅이 `off`인 이벤트가 있으면 `eharness hooks --install` 실행을 안내한다(이 스킬은 settings.json을 건드리지 않는다).
3. 대시보드 주소 `http://127.0.0.1:7477/`를 알려준다. 브라우저 탭은 사용자가 요청할 때만 연다.

## 주의

- eharness CLI 경로: PATH의 `eharness` → 없으면 `~/tools/eharness/bin/eharness`. 다른 위치면 `EHARNESS_BIN`으로 지정.
- 기동 실패 시 `~/.eharness/collect.log`를 보고 포트 충돌(`--port`)이나 python3 부재를 확인한다.
