# eharness 작업 지침

- **판단·규칙의 정본은 `design/`** — 먼저 `design/charter.md`(불변 원칙·채택 게이트 5)를 따르고, 현재 바인딩·로드맵은 `design/map.md`, 이력은 `design/decisions.md`.
- 새 능력은 반드시 이 순서로만: 게이트 5 통과 기록(decisions) → `design/specs/<능력>.md`(6하) → scaffold 자산(frontmatter `capability:` 태그) → `bin/eharness wire <능력> --install`. **`~/.claude`를 직접 편집하지 않는다.**
- `cctv/` 패키지에는 읽기 전용 코드만 — 쓰기는 능력 스펙 what에 선언된 화이트리스트뿐. 제어 코드는 `wire/`·`scaffold/`에.
- 관측 훅·스크립트는 무개입 — 항상 exit 0 / 빈 JSON 응답, 차단·판단 없음.
- verify: `python3 -m unittest discover -s tests`. 수집기 반영: `launchctl kickstart -k gui/$UID/com.eharness.collect` 후 `curl -s 127.0.0.1:7477/health`.
- 판정·완료·개정은 `design/decisions.md`에 한 줄 append — 기록 없는 착수 금지.
- 변경은 의미 단위로 커밋한다(관련 decisions 항목과 같은 커밋). 커밋 없는 작업 종료 금지.
