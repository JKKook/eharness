"""능력(capability) 단위 설치/제거/상태.

- 기계가 읽는 배선 선언은 자산 파일에 있다: 스킬·에이전트 frontmatter의 `capability:`,
  훅 json({capability, events, hook}). 스펙(design/specs/<능력>.md)은 사람·에이전트용 정본으로,
  존재하지 않으면 설치를 거부한다(charter 게이트 5의 기계적 강제).
- settings.json 병합은 cctv/hooks.py와 같은 규약: 백업 → tmp 쓰기 → os.replace, 멱등.
- 설치 내역은 EH_HOME/wire.json에 기록 — uninstall이 정확히 그만큼만 걷는다.
"""
import json, os, shutil, time

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SCAFFOLD = os.path.join(ROOT, "scaffold")
SPECS = os.path.join(ROOT, "design", "specs")
CLAUDE_HOME = os.path.expanduser(os.environ.get("EHARNESS_CLAUDE_HOME", "~/.claude"))
EH_HOME = os.path.expanduser(os.environ.get("EHARNESS_HOME", "~/.eharness"))


def _fm_capability(path):
    """markdown frontmatter의 capability: 값 (없으면 None)."""
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for ln in lines[1:60]:
        if ln.strip() == "---":
            return None
        if ln.startswith("capability:"):
            return ln.split(":", 1)[1].strip()
    return None


def discover(cap):
    """scaffold에서 해당 능력 태그가 붙은 자산을 모은다."""
    a = {"skills": [], "agents": [], "hooks": []}
    for d in sorted(os.listdir(os.path.join(SCAFFOLD, "skills"))) if os.path.isdir(os.path.join(SCAFFOLD, "skills")) else []:
        md = os.path.join(SCAFFOLD, "skills", d, "SKILL.md")
        if _fm_capability(md) == cap:
            a["skills"].append(d)
    for f in sorted(os.listdir(os.path.join(SCAFFOLD, "agents"))) if os.path.isdir(os.path.join(SCAFFOLD, "agents")) else []:
        p = os.path.join(SCAFFOLD, "agents", f)
        if f.endswith(".md") and _fm_capability(p) == cap:
            a["agents"].append(f)
    for f in sorted(os.listdir(os.path.join(SCAFFOLD, "hooks"))) if os.path.isdir(os.path.join(SCAFFOLD, "hooks")) else []:
        if not f.endswith(".json"):
            continue
        try:
            decl = json.load(open(os.path.join(SCAFFOLD, "hooks", f)))
        except (OSError, ValueError):
            continue
        if decl.get("capability") == cap:
            a["hooks"].append(decl)
    return a


def _record_path():
    return os.path.join(EH_HOME, "wire.json")


def _load_record():
    try:
        return json.load(open(_record_path()))
    except (OSError, ValueError):
        return {}


def _save_record(rec):
    os.makedirs(EH_HOME, exist_ok=True)
    tmp = _record_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, _record_path())


def _settings_path():
    return os.path.join(CLAUDE_HOME, "settings.json")


def _load_settings():
    try:
        return json.load(open(_settings_path()))
    except (OSError, ValueError):
        return {}


def _save_settings(cfg):
    if os.path.exists(_settings_path()):
        shutil.copy2(_settings_path(), _settings_path() + ".bak-wire-" + time.strftime("%Y%m%d%H%M%S"))
    tmp = _settings_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, _settings_path())


def _abs_command(cmd):
    return cmd if os.path.isabs(cmd) else os.path.join(ROOT, cmd)


def install(cap):
    if not os.path.exists(os.path.join(SPECS, f"{cap}.md")):
        raise SystemExit(f"거부: design/specs/{cap}.md 없음 — 게이트 5(선언) 미통과. 스펙부터 작성하라.")
    a = discover(cap)
    if not (a["skills"] or a["agents"] or a["hooks"]):
        raise SystemExit(f"거부: scaffold에 capability:{cap} 자산이 없다.")
    rec = _load_record()
    mine = rec.get(cap, {"skills": [], "agents": [], "hooks": []})
    entry = {"skills": [], "agents": [], "hooks": [], "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}

    for name in a["skills"]:
        dst = os.path.join(CLAUDE_HOME, "skills", name)
        if os.path.exists(dst) and name not in mine["skills"]:
            raise SystemExit(f"거부: {dst} 가 이미 있고 wire 소유가 아님 — 수동 정리 후 재시도.")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(os.path.join(SCAFFOLD, "skills", name), dst)
        entry["skills"].append(name)

    for f in a["agents"]:
        dst = os.path.join(CLAUDE_HOME, "agents", f)
        if os.path.exists(dst) and f not in mine["agents"]:
            raise SystemExit(f"거부: {dst} 가 이미 있고 wire 소유가 아님 — 수동 정리 후 재시도.")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(SCAFFOLD, "agents", f), dst)
        entry["agents"].append(f)

    cfg = _load_settings()
    hooks = cfg.setdefault("hooks", {})
    changed = False
    for decl in a["hooks"]:
        h = dict(decl["hook"])
        h["command"] = _abs_command(h["command"])
        for ev in decl.get("events", []):
            groups = hooks.setdefault(ev, [])
            if not any(x.get("command") == h["command"] for g in groups for x in g.get("hooks", [])):
                groups.append({"hooks": [h]})
                changed = True
            entry["hooks"].append([ev, h["command"]])
    if not cfg["hooks"]:
        del cfg["hooks"]
    if changed:
        _save_settings(cfg)

    rec[cap] = entry
    _save_record(rec)
    print(f"installed {cap}: skills={entry['skills']} agents={entry['agents']} hooks={len(entry['hooks'])}건"
          + ("" if changed or not entry["hooks"] else " (settings 변경 없음 — 이미 배선됨)"))


def uninstall(cap):
    rec = _load_record()
    entry = rec.get(cap)
    if not entry:
        print(f"{cap}: 설치 기록 없음")
        return
    for name in entry.get("skills", []):
        dst = os.path.join(CLAUDE_HOME, "skills", name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
    for f in entry.get("agents", []):
        dst = os.path.join(CLAUDE_HOME, "agents", f)
        if os.path.exists(dst):
            os.remove(dst)
    cfg = _load_settings()
    hooks = cfg.get("hooks", {})
    ours = {(ev, cmd) for ev, cmd in entry.get("hooks", [])}
    changed = False
    for ev in list(hooks):
        kept = []
        for g in hooks[ev]:
            g["hooks"] = [x for x in g.get("hooks", []) if (ev, x.get("command")) not in ours]
            if g["hooks"]:
                kept.append(g)
            else:
                changed = True
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]
    if "hooks" in cfg and not cfg["hooks"]:
        del cfg["hooks"]
    if changed:
        _save_settings(cfg)
    del rec[cap]
    _save_record(rec)
    print(f"uninstalled {cap}")


def status(cap=None):
    rec = _load_record()
    caps = set(rec)
    for sub, probe in (("skills", lambda d: _fm_capability(os.path.join(SCAFFOLD, "skills", d, "SKILL.md"))),
                       ("agents", lambda f: _fm_capability(os.path.join(SCAFFOLD, "agents", f)))):
        base = os.path.join(SCAFFOLD, sub)
        if os.path.isdir(base):
            caps |= {c for c in (probe(x) for x in os.listdir(base)) if c}
    base = os.path.join(SCAFFOLD, "hooks")
    if os.path.isdir(base):
        for f in os.listdir(base):
            if f.endswith(".json"):
                try:
                    c = json.load(open(os.path.join(base, f))).get("capability")
                    if c:
                        caps.add(c)
                except (OSError, ValueError):
                    pass
    if cap:
        caps &= {cap}
    if not caps:
        print("능력 없음 (scaffold 자산·설치 기록 모두 비어 있음)")
        return
    for c in sorted(caps):
        a = discover(c)
        spec = "spec ok " if os.path.exists(os.path.join(SPECS, f"{c}.md")) else "spec 없음"
        inst = "installed " + rec[c].get("ts", "") if c in rec else "미설치"
        print(f"{c:<16} {spec}  자산 s{len(a['skills'])}/a{len(a['agents'])}/h{len(a['hooks'])}  {inst}")
