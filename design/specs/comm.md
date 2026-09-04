# comm (에이전트 통신 배선) 스펙

> 세션이 대시보드 없이 스스로를 관제 계층(리더/팀원)·세션 그룹에 등록/해제한다. 2026-09-04.

```yaml
capability: comm
why:    decisions.md#2026-09-04-게이트-통과   # 대시보드 부모지정·그룹 지정 수동 반복
what:   manual.json#parents · manual.json#groups   # 쓰기는 수집기 API 경유 — 직접 파일 접근 없음
how:    [skill:cctv-register]                # register.sh 포함. 훅 없음(SubagentStart 제외 결정 참조)
when:   [manual]                             # 사용자가 세션에 등록을 지시할 때
where:  global                               # 모든 세션에서 쓸 수 있어야 함
who:    all-sessions · no-human-gate         # 등록은 표시용 메타데이터 — 게이트·차단 없음
```

## 문제
리더/팀원 계층과 세션 그룹을 대시보드 관리 패널에서 사람이 클릭으로만 등록할 수 있어,
멀티 세션 작업을 시작할 때마다 수동 반복(2026-09-02~03 계층 UI 운용 내내).
세션에게 "너는 X의 팀원, 등록해"라고 말하면 끝나야 한다.

## 최소 설계
스킬 `cctv-register` 하나. 동봉 `register.sh`가:
1. 프로세스 트리를 올라가 `~/.claude/sessions/<pid>.json`에서 **자기 sid·이름**을 해석
2. 수집기 API 호출: `parent <이름>`(부모 지정) / `child <이름>`(자식 지정) / `clear`(부모 해제)
   / `group <이름>`(세션 그룹) / `ungroup`(그룹 해제) / `status`(자기 행 확인)
등록 즉시 대시보드·statusline·cmux 투영에 반영된다(수집기가 재계산).

## verify
설치 후 임의 세션에서 `register.sh group <임시명>` → `GET /api/sessions`의 자기 행 `sgroup` 반영
→ `ungroup`으로 원복. `status`가 자기 sid를 올바르게 해석하는지 확인.

## 되돌림
`eharness wire comm --uninstall` — `~/.claude/skills/cctv-register/` 제거(설정 변경 없음 — 훅 미사용).
등록된 계층·그룹 데이터는 manual.json에 남음(대시보드에서 해제 가능 — 데이터는 what 소유자인 수동 등록 체계의 것).
