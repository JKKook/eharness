"""수동 등록: 세션 그룹(이름 있는 묶음)과 세션 간 통신 링크. ~/.eharness/manual.json 에 저장.
세션은 재시작하면 sid 가 바뀌므로 {sid, name} 을 함께 저장하고, 해석 시 sid → name 순으로 매칭한다."""
import json, os, uuid
from . import EH_HOME

PATH = os.path.join(EH_HOME, "manual.json")
EMPTY = {"groups": [], "links": [], "parents": []}


def load():
    try:
        d = json.load(open(PATH))
        return {"groups": [g for g in d.get("groups", []) if g.get("name") and isinstance(g.get("members"), list)],
                "links": [l for l in d.get("links", []) if isinstance(l, dict) and l.get("a") and l.get("b")],
                "parents": [e for e in d.get("parents", []) if isinstance(e, dict) and e.get("child") and e.get("parent")]}
    except (OSError, ValueError):
        return dict(EMPTY)


def save(d):
    groups = []
    for g in (d.get("groups") or [])[:32]:
        name = str(g.get("name", ""))[:40].strip()
        members = [{"sid": str(m.get("sid", ""))[:64], "name": str(m.get("name", ""))[:64]} for m in (g.get("members") or [])[:64]]
        if name and members:
            groups.append({"id": g.get("id") or uuid.uuid4().hex[:8], "name": name, "members": members})
    links = []
    for l in (d.get("links") or [])[:128]:
        a, b = l.get("a") or {}, l.get("b") or {}
        ka, kb = (a.get("sid") or "") + "|" + (a.get("name") or ""), (b.get("sid") or "") + "|" + (b.get("name") or "")
        if (a.get("name") or a.get("sid")) and (b.get("name") or b.get("sid")) and ka != kb:
            links.append({"a": {"sid": str(a.get("sid", ""))[:64], "name": str(a.get("name", ""))[:64]},
                          "b": {"sid": str(b.get("sid", ""))[:64], "name": str(b.get("name", ""))[:64]}})
    parents, seen = [], set()
    for e in (d.get("parents") or [])[:128]:
        c, pa = e.get("child") or {}, e.get("parent") or {}
        kc = (c.get("sid") or "") + "|" + (c.get("name") or "")
        if not (c.get("sid") or c.get("name")) or not (pa.get("sid") or pa.get("name")) or kc in seen:
            continue
        seen.add(kc)
        parents.append({"child": {"sid": str(c.get("sid", ""))[:64], "name": str(c.get("name", ""))[:64]},
                        "parent": {"sid": str(pa.get("sid", ""))[:64], "name": str(pa.get("name", ""))[:64]}})
    out = {"groups": groups, "links": links, "parents": parents}
    os.makedirs(EH_HOME, exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)
    return out


def assign_group(sid, name, group):
    """세션(sid/name)을 이름 있는 세션 그룹에 배정한다(세션당 1그룹 — 다른 그룹에서는 뺀다).
    group 이 없으면 해제. 없는 그룹명이면 새로 만든다. 빈 그룹은 save() 필터로 자연 소멸."""
    d = load()
    for g in d["groups"]:
        g["members"] = [m for m in g["members"]
                        if not (sid and m.get("sid") == sid) and not (name and m.get("name") == name)]
    if group:
        g = next((g for g in d["groups"] if g["name"] == group), None)
        if not g:
            g = {"name": group, "members": []}
            d["groups"].append(g)
        g["members"].append({"sid": sid or "", "name": name or ""})
    return save(d)


def resolve_ref(ref, by_sid, by_name):
    return by_sid.get(ref.get("sid")) or by_name.get(ref.get("name"))


def assign_parent(sid, name, parent_sid=None, parent_name=None):
    """세션(child)의 부모 에이전트를 지정/해제한다. 자식당 부모 1개, 자기 자신·순환 금지."""
    d = load()
    same = lambda ref, s2, n2: (s2 and ref.get("sid") == s2) or (n2 and ref.get("name") == n2)
    d["parents"] = [e for e in d["parents"] if not same(e["child"], sid, name)]
    if parent_sid or parent_name:
        # 순환 방지: 지정하려는 부모의 조상 사슬에 child 가 있으면 거부
        cur_s, cur_n = parent_sid, parent_name
        for _ in range(64):
            if (sid and cur_s == sid) or (name and cur_n == name):
                return {"error": "순환 구조 — 자기 자신(또는 자손)을 부모로 지정할 수 없음"}
            up = next((e for e in d["parents"] if same(e["child"], cur_s, cur_n)), None)
            if not up:
                break
            cur_s, cur_n = up["parent"].get("sid"), up["parent"].get("name")
        d["parents"].append({"child": {"sid": sid or "", "name": name or ""},
                             "parent": {"sid": parent_sid or "", "name": parent_name or ""}})
    return save(d)
