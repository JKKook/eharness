"""소스 3종을 세션 행(row schema v1)으로 합친다."""
import glob, os
from . import SCHEMA_VERSION, context_window
from . import manual as manual_mod
from .sources import registry, transcript, hookstate, terminal


CMUX_STATUS_DIR = os.path.expanduser("~/.local/state/cmux-claude-status")


def _cmux_status_tabs():
    """cmux-status.sh 훅이 남긴 사이드바 상태 행 파일들(탭 UUID). 행 없음 = '기본' 판정에 사용."""
    try:
        return {n.upper() for n in os.listdir(CMUX_STATUS_DIR) if n not in ("current", "watcher.lock")}
    except OSError:
        return set()


def collect(include_dead=False, subagents=False):
    window = context_window()
    try:                                                    # 최근 턴 소요시간 EMA (statusline 훅이 기록, 전 세션 공용)
        ema = int(open(os.path.join(registry.CLAUDE_HOME, "hook-state", "turn-ema")).read().strip())
    except (OSError, ValueError):
        ema = None
    rows = []
    status_tabs = _cmux_status_tabs()
    sessions = list(registry.sessions(include_dead))
    penv = terminal.ps_env([s["pid"] for s in sessions if s.get("alive")])
    tree = terminal.cmux_tree()
    wsmap = terminal.workspaces_from_tree(tree) if tree else terminal.cmux_workspaces()
    for s in sessions:
        sid, cwd = s["sessionId"], s.get("cwd", "")
        tpath = registry.transcript_path(cwd, sid)
        if not os.path.exists(tpath):                       # 다른 cwd 에서 재개된 세션: sid 로 전역 탐색
            hits = glob.glob(os.path.join(registry.CLAUDE_HOME, "projects", "*", f"{sid}.jsonl"))
            tpath = hits[0] if hits else tpath
        tr = transcript.parse(tpath)
        pts = tr.pop("series")
        step = max(1, -(-len(pts) // 80))                    # ≤80 점으로 다운샘플 (올림, 마지막 점은 항상 유지)
        pts = pts[::step] + ([pts[-1]] if pts and (len(pts) - 1) % step else [])
        hs = hookstate.state(sid)
        cx = hookstate.ctx(sid)
        pe = penv.get(s.get("pid"), {}); ws = wsmap.get(pe.get("cmux_workspace_id", ""), {})
        term = dict(tty=pe.get("tty", ""), ws_id=pe.get("cmux_workspace_id", ""), ws_ref=ws.get("ref", ""),
                    ws_index=ws.get("index"), ws_title=ws.get("title", ""), ws_selected=ws.get("selected", False), ws_group=ws.get("group"))
        tool_since = None
        if hs.get("STATE") == "running" and hs.get("START", "").isdigit():
            tool_since = int(hs["START"])
        # 메시지 상태: Notification(권한/입력 대기)이 마지막 훅 상태 기록보다 새로우면 '입력 필요(need)',
        # 아니면 실행 중(run) / 응답 완료 후 검토 대기(rev)
        running = hs.get("STATE") in ("running", "thinking")
        need = hookstate.mtime(sid, "notif") > hookstate.mtime(sid, "state")
        msg_state = "need" if need else ("run" if running else "rev")
        # cmux 사이드바에 상태 행이 없는 검토 세션 = 훅 설치 이전 활동/clear 이후 무이벤트 → '기본(none)'
        if msg_state == "rev" and term["ws_id"] and term["ws_id"].upper() not in status_tabs:
            msg_state = "none"
        row = dict(schema_version=SCHEMA_VERSION, terminal=term, tool_since=tool_since,
                   msg_state=msg_state, turn_eta=ema,
                   turn_start=int(hs["TURN_START"]) if hs.get("TURN_START", "").isdigit() else None,
                   last_turn_secs=int(hs["LAST_TURN_SECS"]) if hs.get("LAST_TURN_SECS", "").isdigit() else None, sock=s.get("messagingSocketPath", ""), name=s.get("name") or sid[:8], status=s.get("status", ""),
                   kind=s.get("kind", ""), pid=s.get("pid"), sid=sid, cwd=cwd, alive=s["alive"],
                   started=(s.get("startedAt") or 0) / 1000,
                   hook_state=hs.get("STATE", ""), cur_tool=hs.get("TOOL", "") if hs.get("STATE") == "running" else "",
                   ctx_pct=round(100 * tr["ctx"] / window, 1), ctx_source="usage", cost_usd=None,
                   series=[(round(t), round(100 * c / window, 1)) for t, c in pts], **tr)
        # 완료분은 다음 사용자 입력까지 유지(transcript 가 만료), 실행 중 로컬은 턴 진행·승인 대기 동안만(검토/기본 상태의 미완 fg = 중단 잔재)
        row["tasks"] = [t for t in row["tasks"] if t.get("done") or t["bg"] or msg_state in ("run", "need")]

        if cx.get("CTX_PCT"):
            try:
                row["ctx_pct"], row["ctx_source"] = float(cx["CTX_PCT"]), "statusline"
                row["cost_usd"] = float(cx.get("COST_USD") or 0) or None
            except ValueError:
                pass
        if subagents:
            sa = transcript.parse_subagents(os.path.join(os.path.dirname(tpath), sid, "subagents"))
            row["subagents"] = sa["count"]
            row["tools"] = row["tools"] + sa["tools"]
            row["out_tok"] += sa["out_tok"]
            for k, e in sa["comm"].items():
                m = row["comm"].setdefault(k, dict(e, n=0, last=None)); m["n"] += e["n"]
                if e["last"] and (m["last"] is None or e["last"] > m["last"]): m["last"] = e["last"]
        rows.append(row)
    rows.sort(key=lambda r: (r["status"] != "busy", -r["started"]))
    man = manual_mod.load()
    mem = {}                                               # 세션 그룹(수동 그룹) 멤버십: sid 우선, 이름 폴백
    for g in man.get("groups", []):
        for m in g.get("members", []):
            if m.get("sid"): mem.setdefault("sid:" + m["sid"], g["name"])
            if m.get("name"): mem.setdefault("name:" + m["name"], g["name"])
    for r in rows:
        r["sgroup"] = mem.get("sid:" + r["sid"]) or mem.get("name:" + r["name"])
    resolve_parents(rows, man)
    for r in rows:
        if r.get("alive"):                                 # statusline [이름·표시] — 자식은 ↳부모, 아니면 세션 그룹
            hookstate.cache_group(r["sid"], ("↳" + r["parent"]["name"]) if r.get("parent") else r["sgroup"])
    resolve_comm(rows, man)
    project_agent_badges(rows, wsmap)
    project_metrics(rows)
    return rows, window, attach_sessions(tree, rows)


_BADGES = {}   # ws_id → 마지막으로 적용한 제목 접미사 (변경분만 rename — 3초 주기 스팸 방지)
_SUFFIX_RE = __import__("re").compile(r"\s*⟨[^⟩]*⟩\s*$")
_ICON_RE = __import__("re").compile(r"\s*[👥🗣]\uFE0F?\s*$")
_ICONS = {}   # ws_id → 리더 아이콘 부착 여부 (변경분만 rename)


def project_agent_badges(rows, wsmap):
    """agent→sub_agent 계층을 cmux 사이드바 상태 pill 로 투영 + 과거 제목 ⟨⟩ 접미사 잔재 청소.
    부모 = "AGENT · 자식 n"(파랑), 자식 = "↳ 부모"(주황). cmux 0.64는 이름 옆 커스텀 뱃지 미지원
    (커스텀 사이드바 .js 런타임은 신버전 전용 — ~/.config/cmux/sidebars/eharness.js 준비됨)."""
    by_sid = {r["sid"]: r for r in rows if r.get("alive")}
    want = {}
    for r in rows:
        ws = r.get("alive") and (r.get("terminal") or {}).get("ws_id")
        if not ws:
            continue
        if r.get("parent"):
            p = by_sid.get(r["parent"]["sid"])
            pt = (p and (p.get("terminal") or {}).get("ws_title")) or r["parent"]["name"]
            want[ws] = ("팀원 ↳ " + _ICON_RE.sub("", _SUFFIX_RE.sub("", pt))[:14], None, "#1BAF7A")
        elif r.get("children"):
            want[ws] = (f"리더 · 자식 {len(r['children'])}", "person.2.fill", "#E8A33C")
        else:
            want.setdefault(ws, None)
    leaders = {r["terminal"]["ws_id"] for r in rows if r.get("alive") and r.get("children") and (r.get("terminal") or {}).get("ws_id")}
    for ws in want:
        cur = (wsmap.get(ws) or {}).get("title", "")
        if not cur:
            continue
        if _SUFFIX_RE.search(cur):                       # 제목 ⟨⟩ 접미사 방식의 잔재 제거 (1회성)
            cur = _SUFFIX_RE.sub("", cur).rstrip()
            terminal.ws_rename(ws, cur)
        # 리더 세션의 워크스페이스 이름 옆 아이콘 (👥) — 사이드바에서 리더를 한눈에
        is_lead, has_new = ws in leaders, cur.rstrip().endswith(("🗣", "🗣️"))
        has_any = bool(_ICON_RE.search(cur))
        if is_lead and not has_new:
            terminal.ws_rename(ws, _ICON_RE.sub("", cur).rstrip() + " 🗣️")
        elif not is_lead and has_any:
            terminal.ws_rename(ws, _ICON_RE.sub("", cur).rstrip())
        _ICONS[ws] = is_lead
    for ws, v in want.items():
        if _BADGES.get(ws, "?") == v:
            continue
        if v is None:
            if _BADGES.get(ws):
                terminal.ws_status(ws, "eharness_agent")
        else:
            terminal.ws_status(ws, "eharness_agent", v[0], icon=v[1], color=v[2])
        _BADGES[ws] = v
    for ws in [w for w, v in _BADGES.items() if v and w not in want]:
        terminal.ws_status(ws, "eharness_agent")
        _BADGES[ws] = None


_METRICS = {}   # ws_id → 마지막 지표 pill 값
_PROGRESS = {}  # ws_id → 진행바 표시 여부


def project_metrics(rows):
    """모니터링 지표를 cmux 사이드바에 투영: 턴 진행바(남은 시간)만 — ctx pill은 폐지.
    워크스페이스에 세션이 여럿이면 작업 중 세션 우선."""
    import time as _t
    now = _t.time()
    best = {}
    for r in rows:
        ws = r.get("alive") and (r.get("terminal") or {}).get("ws_id")
        if not ws:
            continue
        cur = best.get(ws)
        if cur is None or (r.get("status") == "busy" and cur.get("status") != "busy"):
            best[ws] = r
    for ws, r in best.items():
        if _METRICS.get(ws) != "off":                   # 과거 ctx pill 잔재 제거 (사용자 요청으로 지표 pill 폐지)
            terminal.ws_status(ws, "eharness_ctx")
            _METRICS[ws] = "off"
        # 턴 진행바: 작업 중 + 예상시간이 유효할 때만, 1시간 이상 초과한 장기 실행은 표시 안 함
        run = r.get("msg_state") == "run" and r.get("turn_start") and r.get("turn_eta")
        if run:
            el = now - r["turn_start"]; rem = r["turn_eta"] - el
            run = rem > -3600
        if run:
            lbl = ("남은 " + _dur(rem)) if rem >= 0 else ("+" + _dur(-rem) + " 초과")
            terminal.ws_progress(ws, min(1.0, el / r["turn_eta"]), lbl)
            _PROGRESS[ws] = True
        elif _PROGRESS.get(ws):
            terminal.ws_progress(ws)
            _PROGRESS[ws] = False


def _dur(s):
    s = int(s)
    return f"{s//3600}h{(s%3600)//60:02d}m" if s >= 3600 else (f"{s//60}m{s%60:02d}s" if s >= 60 else f"{s}s")


def resolve_parents(rows, man):
    """수동 parents 를 살아있는 세션에 매핑: row.parent={sid,name}, row.children=[{sid,name}], row.depth.
    행 순서를 가족 단위로 재배열(부모 바로 아래에 자손 DFS) — 표가 그대로 계층으로 보이게."""
    live = [r for r in rows if r.get("alive")]
    by_sid = {r["sid"]: r for r in live}; by_name = {r["name"]: r for r in live}
    for r in rows:
        r["parent"] = None; r["children"] = []; r["depth"] = 0
    for e in man.get("parents", []):
        c = by_sid.get(e["child"].get("sid")) or by_name.get(e["child"].get("name"))
        pa = by_sid.get(e["parent"].get("sid")) or by_name.get(e["parent"].get("name"))
        if c and pa and c["sid"] != pa["sid"]:
            c["parent"] = {"sid": pa["sid"], "name": pa["name"]}
            pa["children"].append({"sid": c["sid"], "name": c["name"]})
    ordered, seen = [], set()
    def walk(r, d):
        if r["sid"] in seen:
            return
        seen.add(r["sid"]); r["depth"] = d; ordered.append(r)
        for ch in sorted(r["children"], key=lambda x: x["name"]):
            if ch["sid"] in by_sid:
                walk(by_sid[ch["sid"]], d + 1)
    for r in rows:
        if not r.get("alive"):
            continue
        if not r["parent"] or (r["parent"]["sid"] not in by_sid):
            walk(r, 0)
    dead = [r for r in rows if not r.get("alive")]
    rows[:] = ordered + [r for r in live if r["sid"] not in seen] + dead


def resolve_comm(rows, man=None):
    """송수신 상대(uds 소켓 경로 / 이름)를 살아있는 세션에 매핑하고, 수동 등록(그룹·링크)과 합쳐
    연결 요소마다 comm_group(1..) 과 comm_label(수동 그룹 이름이 있으면 그것)을 배정.
    row.comm_peers = [{sid, name, sent, recv, last, manual}], row.comm_other = [...] (죽었거나 미확인 상대)."""
    man = man or {"groups": [], "links": []}
    live = [r for r in rows if r.get("alive")]
    by_addr = {("uds:" + r["sock"]): r["sid"] for r in live if r.get("sock")}
    by_name = {r["name"]: r["sid"] for r in live}
    by_sid = {r["sid"]: r for r in live}
    parent = {r["sid"]: r["sid"] for r in live}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for r in rows:
        peers, other = {}, {}
        entries = list(r.pop("comm", {}).values())
        addr_name = {e["addr"]: e["name"] for e in entries if e["addr"] and e["name"]}   # 수신에서 알게 된 주소→이름
        for e in entries:
            sid = by_addr.get(e["addr"]) or by_name.get(e["name"].split(" [")[0]) or None
            if sid and sid != r["sid"] and sid in by_sid:
                p = peers.setdefault(sid, dict(sid=sid, name=by_sid[sid]["name"], sent=0, recv=0, last=None))
            else:
                label = e["name"] or addr_name.get(e["addr"]) or e["addr"].replace("uds:/tmp/cc-socks/", "pid ").replace(".sock", "")
                p = other.setdefault(label, dict(label=label, sent=0, recv=0, last=None))
            p["sent" if e["dir"] == "send" else "recv"] += e["n"]
            if e["last"] and (p["last"] is None or e["last"] > p["last"]): p["last"] = e["last"]
        r["comm_peers"] = sorted(peers.values(), key=lambda p: -(p["sent"] + p["recv"]))
        r["comm_other"] = sorted(other.values(), key=lambda p: -(p["sent"] + p["recv"]))[:8]
        if r.get("alive"):
            for sid in peers:
                a, b = find(r["sid"]), find(sid)
                if a != b: parent[a] = b
    # 수동 링크: 양쪽을 peer 로 추가(manual 표시) + 같은 그룹으로
    by_name = {r["name"]: r for r in live}
    def _peer(r, other):
        for p in r["comm_peers"]:
            if p["sid"] == other["sid"]:
                p["manual"] = True; return
        r["comm_peers"].append(dict(sid=other["sid"], name=other["name"], sent=0, recv=0, last=None, manual=True))
    for l in man.get("links", []) + [{"a": e["child"], "b": e["parent"]} for e in man.get("parents", [])]:
        ra = manual_mod.resolve_ref(l["a"], by_sid, by_name); rb = manual_mod.resolve_ref(l["b"], by_sid, by_name)
        if not ra or not rb or ra["sid"] == rb["sid"]: continue
        _peer(ra, rb); _peer(rb, ra)
        a, b = find(ra["sid"]), find(rb["sid"])
        if a != b: parent[a] = b
    # 수동 그룹: 멤버끼리 묶고, 컴포넌트 라벨로 그룹 이름 사용
    label_of = {}
    for g in man.get("groups", []):
        members = [m for m in (manual_mod.resolve_ref(x, by_sid, by_name) for x in g["members"]) if m]
        for m in members[1:]:
            a, b = find(members[0]["sid"]), find(m["sid"])
            if a != b: parent[a] = b
        if members:
            label_of[members[0]["sid"]] = g["name"]
    roots, root_label = {}, {}
    for sid, name in label_of.items():
        root_label.setdefault(find(sid), name)
    for r in sorted(live, key=lambda r: r["started"]):          # 그룹 번호는 가장 오래된 세션 순으로 안정적으로
        root = find(r["sid"])
        members = [x for x in live if find(x["sid"]) == root]
        if len(members) >= 2:
            r["comm_group"] = roots.setdefault(root, len(roots) + 1)
            r["comm_label"] = root_label.get(root)
        else:
            r["comm_group"] = None; r["comm_label"] = None
    for r in rows:
        r.setdefault("comm_group", None); r.setdefault("comm_label", None)


def attach_sessions(tree, rows):
    """cmux 트리의 surface 에 세션을 tty 로 붙인다(없으면 워크스페이스 id 로). 트리 밖 세션은 outside 에."""
    if not tree:
        return {"windows": [], "outside": [r["sid"] for r in rows if r.get("alive")]}
    by_tty = {r["terminal"]["tty"]: r["sid"] for r in rows if r.get("alive") and r["terminal"].get("tty")}
    placed = set()
    for w in tree["windows"]:
        for g in w["groups"]:
            for ws in g["workspaces"]:
                for p in ws["panes"]:
                    for sf in p["surfaces"]:
                        sid = by_tty.get(sf.get("tty") or "")
                        sf["sid"] = sid
                        if sid:
                            placed.add(sid)
                # tty 매칭 실패했지만 env 로 워크스페이스는 아는 세션 → 워크스페이스에 직접
                ws["unplaced"] = [r["sid"] for r in rows if r.get("alive") and r["sid"] not in placed and r["terminal"].get("ws_id") == ws["id"]]
                placed.update(ws["unplaced"])
    return {"windows": tree["windows"], "outside": [r["sid"] for r in rows if r.get("alive") and r["sid"] not in placed]}
