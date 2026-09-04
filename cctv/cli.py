import argparse, os, sys, time
from . import VERSION, CLAUDE_HOME
from .collect import collect
from .view import table, jsonout


def cmd_ps(a):
    rows, window, _ = collect(a.all, a.subagents)
    print(jsonout.dump(rows) if a.json else table.render(rows, window))


def cmd_watch(a):
    try:
        while True:
            rows, window, _ = collect(a.all, a.subagents)
            print("\033[2J\033[H" + table.render(rows, window), flush=True)
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass


def cmd_collect(a):
    from . import launchd
    if a.install: return launchd.install(a.port)
    if a.uninstall: return launchd.uninstall()
    if a.status: return launchd.status()
    from .collector import serve
    serve(a.port)


def cmd_events(a):
    import json
    from . import bus
    def fmt(ev):
        extra = ev.get("tool") or ev.get("source") or ""
        agent = f" [{ev['agent_type']}]" if ev.get("agent_type") else ""
        return f"{ev['ts'][11:23]}  {ev.get('sid','')[:8]}  {ev.get('event',''):<20}{agent} {extra}"
    for ev in bus.read(a.days, a.sid):
        print(json.dumps(ev, ensure_ascii=False) if a.json else fmt(ev))
    if a.follow:
        import time
        seen = set(bus.files()); pos = {f: os.path.getsize(f) for f in seen}
        try:
            while True:
                for f in bus.files():
                    size = os.path.getsize(f)
                    if size > pos.get(f, 0):
                        with open(f) as fh:
                            fh.seek(pos.get(f, 0))
                            for line in fh:
                                try: ev = json.loads(line)
                                except ValueError: continue
                                if a.sid is None or ev.get("sid","").startswith(a.sid):
                                    print(json.dumps(ev, ensure_ascii=False) if a.json else fmt(ev), flush=True)
                        pos[f] = size
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass


def cmd_hooks(a):
    from . import hooks
    if a.install: hooks.install(a.port)
    elif a.uninstall: hooks.uninstall(a.port)
    else: hooks.status(a.port)


def cmd_doctor(a):
    """비공개 포맷 의존 필드가 현재 버전에서 아직 존재하는지 점검."""
    from .sources import registry, transcript
    ok = True
    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(("ok   " if cond else "FAIL ") + msg)
    live = list(registry.sessions())
    check(live, f"registry: {len(live)} live session(s) in {CLAUDE_HOME}/sessions")
    for f in registry.FIELDS:
        check(all(f in s for s in live), f"registry field '{f}' present in all")
    with_tr = [s for s in live if os.path.exists(registry.transcript_path(s["cwd"], s["sessionId"]))]
    check(with_tr, f"transcript: {len(with_tr)}/{len(live)} sessions have a transcript file")
    parsed = [transcript.parse(registry.transcript_path(s["cwd"], s["sessionId"])) for s in with_tr]
    check(any(p["ctx"] > 0 for p in parsed), "transcript usage fields yield ctx > 0 for at least one session")
    check(any(p["tools"] for p in parsed), "transcript tool_use blocks found")
    check(os.path.isdir(os.path.join(CLAUDE_HOME, "hook-state")), "hook-state dir exists (tool-start/end hooks wired)")
    sys.exit(0 if ok else 1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="eharness", description="로컬 Claude Code 세션 관제")
    p.add_argument("--version", action="version", version=f"eharness {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("ps", cmd_ps), ("watch", cmd_watch)):
        sp = sub.add_parser(name, help="세션 표 (ps: 1회, watch: 반복)")
        sp.add_argument("--all", action="store_true", help="죽은 pid의 레지스트리 잔재 포함")
        sp.add_argument("--subagents", action="store_true", help="서브에이전트 트랜스크립트 합산")
        if name == "ps":
            sp.add_argument("--json", action="store_true")
        else:
            sp.add_argument("interval", nargs="?", type=float, default=3.0)
        sp.set_defaults(fn=fn)
    sp = sub.add_parser("collect", help="127.0.0.1 HTTP 수집기 (hooks type:http → events.jsonl)")
    sp.add_argument("--port", type=int, default=7477)
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--install", action="store_true", help="launchd 에이전트로 상시 기동 등록 (macOS)")
    g.add_argument("--uninstall", action="store_true"); g.add_argument("--status", action="store_true")
    sp.set_defaults(fn=cmd_collect)
    sp = sub.add_parser("events", help="이벤트 버스 조회")
    sp.add_argument("--follow", "-f", action="store_true"); sp.add_argument("--sid", help="세션 ID 접두사")
    sp.add_argument("--days", type=int, default=1); sp.add_argument("--json", action="store_true"); sp.set_defaults(fn=cmd_events)
    sp = sub.add_parser("hooks", help="settings.json 에 관측용 http 훅 병합/제거 (기본: 상태)")
    sp.add_argument("--port", type=int, default=7477)
    g = sp.add_mutually_exclusive_group(); g.add_argument("--install", action="store_true"); g.add_argument("--uninstall", action="store_true")
    sp.set_defaults(fn=cmd_hooks)
    sub.add_parser("doctor", help="비공개 포맷 필드 존재 점검").set_defaults(fn=cmd_doctor)
    a = p.parse_args(argv)
    a.fn(a)
