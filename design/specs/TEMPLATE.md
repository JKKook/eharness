# <능력 이름> 스펙

> 사본을 `specs/<능력>.md`로 만들어 작성. 6하를 못 채우면 설계 미성숙 = 보류 (charter §2 게이트 5).
> 착수 전 decisions.md에 게이트 5종 통과 기록이 먼저 있어야 한다.

```yaml
capability: <이름>            # scaffold 자산 frontmatter의 태그와 동일해야 함
why:    decisions.md#<날짜-이름>   # 채택 근거 링크
what:   <소유 상태의 SSOT 경로>    # 예: manual.json#parents, ~/.eharness/state/<이름>/
                                  # 다른 능력의 what과 겹치면 채택 거부
how:    [<메커니즘 목록>]          # 예: skill:<이름>, hook:<이벤트>, agent:<이름>, tool:<이름>
                                  # 데몬형 능력은 package:<경로> 허용
when:   [<트리거 목록>]            # 예: hook:<이벤트>, cron:<표현식>, manual, daemon
                                  # wire가 이 선언대로 배선한다. 보류 능력은 재검토일 명시
where:  global | project          # global=~/.claude, project=.claude. 격리 필요 시 sandbox|worktree 병기
who:    <주체> · <게이트>          # 예: all-sessions · no-human-gate, leader-only · human-approve
```

## 문제
<이 능력이 없어서 반복된 수동 작업·실패. events 버스의 증거를 날짜와 함께 인용>

## 최소 설계
<how에 선언한 자산 각각이 무엇을 하는지. 요청 밖 기능 금지 — 문제를 푸는 최소한만>

## verify
<배선 후 통과 기준. 실행 가능한 확인 방법으로(테스트·대시보드 확인·diff 0 등)>

## 되돌림
<`wire <이름> --uninstall`이 걷어낼 목록: 자산, settings 항목, what의 상태 영토>
