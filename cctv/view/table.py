import os, time


def k(n):
    return f"{n/1000:.0f}k" if n >= 1000 else str(int(n))


def age(ts):
    s = int(time.time() - ts)
    return f"{s//3600}h{(s%3600)//60:02d}m" if s >= 3600 else f"{s//60}m"


def render(rows, window, home=os.path.expanduser("~")):
    busy = sum(r["status"] == "busy" for r in rows)
    out = [f"eharness  {time.strftime('%H:%M:%S')}  sessions={len(rows)} busy={busy}  ctx_window={k(window)}", ""]
    out.append(f"{'NAME':<24}{'TERM':<9}{'ST':<6}{'CTX':>7}{'IN':>7}{'CACHE':>7}{'OUT':>6}{'TURN':>5}{'COST':>8}  {'NOW':<10}{'TOP TOOLS':<28}{'UP':>6}  TITLE / CWD")
    for r in rows:
        st = "BUSY" if r["status"] == "busy" else ("dead" if not r.get("alive", True) else "idle")
        t = r.get("terminal", {}); term = (f"ws{t['ws_index']}" if t.get("ws_index") else (t.get("tty") or "-"))[:8]
        now = (r["cur_tool"] or "-")[:10]
        tools = " ".join(f"{n}:{c}" for n, c in r["tools"].most_common(3))[:28]
        title = (r["title"] or r["last_prompt"] or r["last_user"] or "(no prompt yet)").replace("\n", " ")[:40]
        ctx = f"{r['ctx_pct']}%" + ("" if r["ctx_source"] == "statusline" else "~")
        cost = f"${r['cost_usd']:.2f}" if r.get("cost_usd") else "-"
        out.append(f"{r['name'][:23]:<24}{term:<9}{st:<6}{ctx:>7}{k(r['in_tok']):>7}{k(r['cache_r']):>7}{k(r['out_tok']):>6}{r['turns']:>5}{cost:>8}  {now:<10}{tools:<28}{age(r['started']):>6}  {title}  ·  {r['cwd'].replace(home, '~')}")
    return "\n".join(out)
