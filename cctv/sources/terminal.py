"""세션 프로세스 → 터미널(tty, cmux 워크스페이스/탭) 매핑.
- ps -E 로 세션 pid 의 환경변수(CMUX_WORKSPACE_ID 등)와 tty 를 한 번에 읽는다 (같은 사용자 프로세스만 가능).
- cmux workspace list --json 으로 워크스페이스 id → 사이드바 순서(index)·제목을 얻는다. cmux 가 없으면 tty 만."""
import json, os, shutil, subprocess

ENV_KEYS = ("CMUX_WORKSPACE_ID", "CMUX_SURFACE_ID")
LAST = {}   # 진단용: 마지막 호출의 rc/stderr
_cap = {"token": ""}   # cmux 소켓 capability — 세션 env 에서 가져와 CLI 인증에만 쓰고 API 에는 내보내지 않음


def ps_env(pids):
    out = {}
    if not pids:
        return out
    try:
        r = subprocess.run(["ps", "-E", "-o", "pid=,tty=,command=", "-p", ",".join(map(str, pids))],
                           capture_output=True, text=True, timeout=3)
        LAST["ps"] = dict(rc=r.returncode, err=r.stderr[-300:], lines=len(r.stdout.splitlines()), has_env="CMUX_WORKSPACE_ID=" in r.stdout, bytes=len(r.stdout))
        txt = r.stdout
    except (OSError, subprocess.SubprocessError) as e:
        LAST["ps"] = dict(exc=repr(e)); return out
    for line in txt.splitlines():
        out.update(parse_ps_line(line))
    return out


def parse_ps_line(line):
    parts = line.split()
    if len(parts) < 2 or not parts[0].isdigit():
        return {}
    info = {"tty": parts[1] if parts[1] not in ("??", "-") else ""}
    for tok in parts[2:]:
        for key in ENV_KEYS:
            if tok.startswith(key + "="):
                info[key.lower()] = tok[len(key) + 1:]
        if tok.startswith("CMUX_SOCKET_CAPABILITY=") and len(tok) > 24:
            _cap["token"] = tok[23:]
    return {int(parts[0]): info}


SESSION_FILE = os.path.expanduser("~/Library/Application Support/cmux/session-com.cmuxterm.app.json")  # cmux 가 실시간 저장하는 세션 상태 (그룹 정의 포함)


def cmux_groups(window_index=0):
    """워크스페이스 그룹(사이드바 폴더) → {"groups": {gid: {...}}, "ws_group": {workspace_id: gid}}.
    RPC(workspace.group.list — 라이브)를 우선 사용해 eharness 의 수정이 즉시 반영되게 하고,
    실패 시에만 cmux 세션 파일(저장이 수 초 늦다)로 폴백."""
    gs = cmux_rpc("workspace.group.list").get("groups")
    if gs is not None:
        groups = {g["id"]: dict(id=g["id"], name=g.get("name") or "", collapsed=bool(g.get("is_collapsed")), pinned=bool(g.get("is_pinned")), order=i)
                  for i, g in enumerate(gs) if g.get("id")}
        ws_group = {w: g["id"] for g in gs for w in (g.get("member_workspace_ids") or [])}
        LAST["cmux_groups"] = dict(src="rpc", groups=len(groups), mapped=len(ws_group))
        return {"groups": groups, "ws_group": ws_group}
    try:
        d = json.load(open(SESSION_FILE))
        wins = d.get("windows") or []
        tm = wins[min(window_index, len(wins) - 1)].get("tabManager", {}) if wins else {}
    except (OSError, ValueError, AttributeError):
        LAST["cmux_groups"] = "unreadable"; return {"groups": {}, "ws_group": {}}
    groups = {g["id"]: dict(id=g["id"], name=g.get("name") or "", collapsed=bool(g.get("isCollapsed")), pinned=bool(g.get("isPinned")), order=i)
              for i, g in enumerate(tm.get("workspaceGroups") or []) if g.get("id")}
    ws_group = {w.get("workspaceId"): w.get("groupId") for w in (tm.get("workspaces") or []) if w.get("workspaceId")}
    LAST["cmux_groups"] = dict(groups=len(groups), mapped=sum(1 for v in ws_group.values() if v))
    return {"groups": groups, "ws_group": ws_group}


def group_workspaces(workspaces, ginfo):
    """트리(사이드바) 순서를 유지하며 실제 그룹으로 묶는다. 그룹 없는 워크스페이스는 연속 구간마다 title None 버킷."""
    out, by_gid = [], {}
    for ws in workspaces:
        gid = ginfo["ws_group"].get(ws["id"]); g = ginfo["groups"].get(gid) if gid else None
        if g:
            if gid not in by_gid:
                by_gid[gid] = dict(title=g["name"], id=gid, collapsed=g["collapsed"], pinned=g["pinned"], workspaces=[]); out.append(by_gid[gid])
            by_gid[gid]["workspaces"].append(ws)
        else:
            if not out or out[-1]["title"] is not None:
                out.append(dict(title=None, id=None, collapsed=False, pinned=False, workspaces=[]))
            out[-1]["workspaces"].append(ws)
    return out


def _cmux_exe():
    exe = shutil.which("cmux") or os.environ.get("CMUX_BUNDLED_CLI_PATH") or "/Applications/cmux.app/Contents/Resources/bin/cmux"
    return exe if os.path.exists(exe) else None


def _cmux_env():
    env = {**os.environ, "CMUX_QUIET": "1"}
    if not env.get("CMUX_SOCKET_CAPABILITY") and _cap["token"]:   # cmux 밖(launchd)에서는 세션의 capability 로 인증
        env["CMUX_SOCKET_CAPABILITY"] = _cap["token"]
    if not env.get("CMUX_SOCKET_PATH"):
        sock = os.path.expanduser(f"~/.local/state/cmux/cmux-{os.getuid()}.sock")
        if os.path.exists(sock):
            env["CMUX_SOCKET_PATH"] = sock
    return env


def cmux_tree():
    """cmux tree --all --json → 단순화된 계층. 실패하면 None.
    {"windows":[{ref,index,selected_ws_ref,groups:[{title|None, workspaces:[{id,ref,index(1-based),title,selected,
       panes:[{ref,focused,surfaces:[{ref,type,title,tty,selected,url}]}]}]}]}]}"""
    exe = _cmux_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "tree", "--all", "--json"], capture_output=True, text=True, timeout=4, env=_cmux_env())
        LAST["cmux_tree"] = dict(rc=r.returncode, err=r.stderr[-300:])
        d = json.loads(r.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        LAST.setdefault("cmux_tree", {})["exc"] = repr(e); return None
    windows = []
    for wi, w in enumerate(d.get("windows", [])):
        wslist = []
        for ws in w.get("workspaces", []):
            title = ws.get("title") or ""
            wslist.append(dict(
                id=ws.get("id"), ref=ws.get("ref", ""), index=(ws.get("index") or 0) + 1, title=title, selected=bool(ws.get("selected")),
                panes=[dict(ref=p.get("ref", ""), focused=bool(p.get("focused")),
                            surfaces=[dict(ref=sf.get("ref", ""), type=sf.get("type", ""), title=sf.get("title") or "", tty=sf.get("tty") or "",
                                           selected=bool(sf.get("selected")), url=sf.get("url")) for sf in p.get("surfaces", [])])
                       for p in ws.get("panes", [])]))
        groups = group_workspaces(wslist, cmux_groups(wi))
        windows.append(dict(ref=w.get("ref", ""), index=(w.get("index") or 0) + 1, selected_ws_ref=w.get("selected_workspace_ref", ""), groups=groups))
    return {"windows": windows}


def workspaces_from_tree(tree):
    out = {}
    for w in (tree or {}).get("windows", []):
        for g in w["groups"]:
            for ws in g["workspaces"]:
                out[ws["id"]] = dict(ref=ws["ref"], index=ws["index"], title=ws["title"], selected=ws["selected"], group=g["title"])
    return out


def cmux_workspaces():
    """{workspace_id: {ref, index(1-based), title, selected, cwd, last_prompt}} — cmux 없거나 실패하면 {}."""
    exe = _cmux_exe()
    if not exe:
        return {}
    env = _cmux_env()
    try:
        r = subprocess.run([exe, "workspace", "list", "--json"], capture_output=True, text=True, timeout=3, env=env)
        LAST["cmux"] = dict(exe=exe, rc=r.returncode, err=r.stderr[-400:], out=r.stdout[:120], sock=env.get("CMUX_SOCKET_PATH"), cap=bool(env.get("CMUX_SOCKET_CAPABILITY")))
        ws = json.loads(r.stdout).get("workspaces", [])
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        LAST.setdefault("cmux", {})["exc"] = repr(e); return {}
    return {w["id"]: dict(ref=w.get("ref", ""), index=(w.get("index") or 0) + 1, title=w.get("title", ""),
                          selected=bool(w.get("selected")), cwd=w.get("current_directory", ""),
                          last_prompt=w.get("latest_submitted_message") or "")
            for w in ws if w.get("id")}


def cmux_rpc(method, params=None):
    """cmux rpc <method> [json] → dict. 실패하면 {"error": ...}."""
    exe = _cmux_exe()
    if not exe:
        return {"error": "cmux CLI 없음"}
    cmd = [exe, "rpc", method] + ([json.dumps(params, ensure_ascii=False)] if params else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5, env=_cmux_env())
    except (OSError, subprocess.SubprocessError) as e:
        return {"error": repr(e)}
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()[-300:] or f"rc={r.returncode}"}
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except ValueError:
        return {}


def ws_status(ws, key, value=None, icon=None, color=None):
    """cmux 사이드바 상태 pill 설정(value 없으면 제거). 실패해도 조용히 넘어간다(표시용)."""
    exe = _cmux_exe()
    if not exe or not ws:
        return
    cmd = [exe, "clear-status", key, "--workspace", ws] if value is None else           [exe, "set-status", key, value, "--workspace", ws] + (["--icon", icon] if icon else []) + (["--color", color] if color else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4, env=_cmux_env())
        LAST["ws_status"] = dict(rc=r.returncode, err=r.stderr[-200:], ws=ws, val=value)
    except (OSError, subprocess.SubprocessError) as e:
        LAST["ws_status"] = dict(exc=repr(e))


def ws_progress(ws, value=None, label=None):
    """cmux 워크스페이스 진행바 설정(value 없으면 제거)."""
    exe = _cmux_exe()
    if not exe or not ws:
        return
    cmd = [exe, "clear-progress", "--workspace", ws] if value is None else           [exe, "set-progress", f"{max(0.0, min(1.0, value)):.2f}", "--workspace", ws] + (["--label", label] if label else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4, env=_cmux_env())
        LAST["ws_progress"] = dict(rc=r.returncode, err=r.stderr[-200:], ws=ws, val=value)
    except (OSError, subprocess.SubprocessError) as e:
        LAST["ws_progress"] = dict(exc=repr(e))


def ws_rename(ws, title):
    exe = _cmux_exe()
    if not exe or not ws or not title:
        return
    try:
        r = subprocess.run([exe, "rename-workspace", "--workspace", ws, title], capture_output=True, text=True, timeout=4, env=_cmux_env())
        LAST["ws_rename"] = dict(rc=r.returncode, err=r.stderr[-200:], ws=ws, title=title)
    except (OSError, subprocess.SubprocessError) as e:
        LAST["ws_rename"] = dict(exc=repr(e))


def group_move(ws_id, group_id=None, new_group=None, debug=False):
    """워크스페이스를 실제 cmux 사이드바 그룹(폴더)으로 이동한다.
    group_id → 기존 그룹에 추가, new_group → 새 그룹 생성(이름 지정), 둘 다 없으면 그룹에서 빼기.
    제약(실측): 앵커 워크스페이스는 다른 그룹에 add 하면 invalid_state, remove 하면 그룹이 통째로 해산
    → 먼저 앵커를 다른 멤버에게 넘기고(단독이면 그룹 삭제=해제) 진행한다. 빠져나온 그룹이 비면 삭제."""
    steps = []
    def rpc(m, prm=None):
        r = cmux_rpc(m, prm)
        steps.append({"m": m, "p": prm, "r": r if not m.endswith("list") else {"groups": len(r.get("groups") or [])}})
        return r
    def done(ok, err=None):
        out = {"ok": ok}
        if err: out["error"] = err
        if debug: out["steps"] = steps
        return out
    groups = cmux_rpc("workspace.group.list").get("groups") or []
    gid_of = {w: g["id"] for g in groups for w in (g.get("member_workspace_ids") or [])}
    from_gid = gid_of.get(ws_id)
    from_g = next((g for g in groups if g["id"] == from_gid), None)

    def release_anchor():
        """ws 가 지금 그룹의 앵커면 다른 멤버에게 이양, 단독 멤버면 그룹 삭제(=해제). 그룹이 삭제됐으면 True."""
        if not from_g or from_g.get("anchor_workspace_id") != ws_id:
            return False
        others = [w for w in (from_g.get("member_workspace_ids") or []) if w != ws_id]
        if others:
            rpc("workspace.group.set_anchor", {"group_id": from_gid, "workspace_id": others[0]})
            return False
        rpc("workspace.group.delete", {"group_id": from_gid})
        return True

    if new_group:
        # group.create 는 대상 지정 불가(임의 워크스페이스를 앵커로 잡음) → rename → 대상 add →
        # 앵커를 대상으로 이양 → 잘못 잡힌 워크스페이스는 빼서 원래 그룹으로 복구.
        out = rpc("workspace.group.create", {})
        g = out.get("group") or {}
        if not g.get("id"):
            return done(False, out.get("error") or "그룹 생성 실패")
        rpc("workspace.group.rename", {"group_id": g["id"], "name": new_group})
        victims = [w for w in (g.get("member_workspace_ids") or []) if w != ws_id]
        release_anchor()
        out = rpc("workspace.group.add", {"group_id": g["id"], "workspace_id": ws_id})
        if victims and not out.get("error"):
            rpc("workspace.group.set_anchor", {"group_id": g["id"], "workspace_id": ws_id})
        for v in victims:
            rpc("workspace.group.remove", {"group_id": g["id"], "workspace_id": v})
            if gid_of.get(v):
                rpc("workspace.group.add", {"group_id": gid_of[v], "workspace_id": v})
    elif group_id:
        if group_id == from_gid:
            return done(True)
        release_anchor()
        out = rpc("workspace.group.add", {"group_id": group_id, "workspace_id": ws_id})
    else:
        if not from_g:
            return done(True)
        if release_anchor():
            out = {}                                   # 단독 앵커였음 → 그룹 삭제로 이미 해제 완료
        else:
            out = rpc("workspace.group.remove", {"group_id": from_gid, "workspace_id": ws_id})
    if out.get("error"):
        return done(False, out["error"])
    if from_gid and from_gid != group_id:              # 원래 그룹이 비면 빈 폴더가 남지 않게 삭제
        for g in cmux_rpc("workspace.group.list").get("groups") or []:
            if g["id"] == from_gid and not g.get("member_count"):
                rpc("workspace.group.delete", {"group_id": from_gid})
    return done(True)
