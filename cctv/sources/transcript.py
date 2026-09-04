"""projects/<slug>/<sid>.jsonl — 트랜스크립트 (비공개 포맷). 필요한 레코드 4종만 스트리밍 파싱."""
import glob, json, os, re
from collections import Counter
from datetime import datetime

RECV_RE = re.compile(r'<cross-session-message\b([^>]*)>')
ATTR_RE = re.compile(r'([a-z-]+)="([^"]*)"')
DONE_RE = re.compile(r'<tool-use-id>([^<]+)</tool-use-id>')   # task-notification = 백그라운드 작업 종료
BG_TOOLS = ("Agent", "Workflow")


def _epoch(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def empty():
    return dict(title="", last_prompt="", last_user="", model="", ctx=0, in_tok=0, out_tok=0,
                cache_r=0, turns=0, tools=Counter(), last_ts="", series=[], comm={}, recent=[], tasks=[])


def _note_comm(r, direction, addr, name, ts):
    """comm[key] = {dir, addr, name, n, last} — 세션 간 메시지 송수신 집계 (본문은 저장하지 않음)."""
    addr = (addr or "").strip(); name = (name or "").strip()
    if not addr and not name:
        return
    key = f"{direction}|{addr or name}"
    e = r["comm"].setdefault(key, dict(dir=direction, addr=addr, name=name, n=0, last=None))
    e["n"] += 1
    if name and not e["name"]:
        e["name"] = name
    t = _epoch(ts or "")
    if t and (e["last"] is None or t > e["last"]):
        e["last"] = t


def _user_text(content):
    if isinstance(content, str):
        return content
    return " ".join(c.get("text", "") for c in (content or []) if isinstance(c, dict) and c.get("type") == "text")


def parse(path: str) -> dict:
    r = empty()
    if not os.path.exists(path):
        return r
    pend = None    # 진행 중 턴의 마지막 assistant 텍스트 (텍스트, epoch) — 다음 user 메시지 직전 것이 "그 턴의 응답"
    open_tools = {}   # tool_use id → 진행 중 작업. bg(Agent/Workflow/run_in_background Bash)는 task-notification 으로 종료
    def flush():
        if pend:
            r["recent"].append({"role": "claude", "x": pend[0][:2000], "t": pend[1]})
            del r["recent"][:-10]
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if "<task-notification>" in line:            # user 로 배달됐든 queue-operation 에 쌓였든, 뜬 시점 = 작업 종료 → 완료 표시로 유지
                for tid in DONE_RE.findall(line):
                    if tid in open_tools:
                        open_tools[tid]["done"] = True
                        open_tools[tid]["dt"] = _epoch(d.get("timestamp", ""))
            t = d.get("type")
            if t == "ai-title":
                r["title"] = d.get("aiTitle", "")
            elif t == "last-prompt":
                r["last_prompt"] = d.get("lastPrompt", "")
            elif t == "user":
                r["turns"] += 1
                content = (d.get("message") or {}).get("content")
                for c in content if isinstance(content, list) else []:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        e = open_tools.get(c.get("tool_use_id"))
                        if e and (not e["bg"] or c.get("is_error")):   # bg 는 즉시 ack — task-notification 까지 실행 중
                            e["done"] = True
                            e["dt"] = _epoch(d.get("timestamp", ""))
                txt = _user_text(content).strip()
                for m in RECV_RE.finditer(txt):             # 다른 세션에서 온 메시지
                    a = dict(ATTR_RE.findall(m.group(1)))
                    _note_comm(r, "recv", a.get("from"), a.get("from-name"), d.get("timestamp"))
                if txt and not txt.startswith(("<", "[Image")):   # system-reminder / tool_result / 이미지 첨부 마커 제외
                    # 진짜 사용자 턴 = 검토가 끝나고 다음 입력이 들어온 시점 → 완료분·중단된 포그라운드 일괄 만료 (실행 중 bg 만 유지)
                    open_tools = {k: e for k, e in open_tools.items() if e["bg"] and not e.get("done")}
                    r["last_user"] = txt
                    flush(); pend = None
                    r["recent"].append({"role": "user", "x": txt[:200], "t": _epoch(d.get("timestamp", ""))})
                    del r["recent"][:-10]
            elif t == "assistant":
                m = d.get("message") or {}
                u = m.get("usage") or {}
                r["model"] = m.get("model") or r["model"]
                r["last_ts"] = d.get("timestamp") or r["last_ts"]
                inp, cr, cc = u.get("input_tokens", 0), u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0)
                if inp + cr + cc > 0:                       # usage 전부 0인 합성 레코드(재개 마커)는 ctx에 반영하지 않음
                    r["ctx"] = inp + cr + cc
                    e = _epoch(d.get("timestamp", ""))
                    if e:
                        r["series"].append((e, r["ctx"]))    # (epoch, ctx) — 컨텍스트 증가 곡선
                r["in_tok"] += inp + cc
                r["cache_r"] += cr
                r["out_tok"] += u.get("output_tokens", 0)
                for c in m.get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text" and (c.get("text") or "").strip():
                        pend = (c["text"].strip(), _epoch(d.get("timestamp", "")))
                    elif c.get("type") == "tool_use":
                        r["tools"][c.get("name", "?")] += 1
                        inp = c.get("input") or {}
                        bg = c.get("name") in BG_TOOLS or bool(inp.get("run_in_background"))
                        desc = str(inp.get("description") or inp.get("name") or "").strip()
                        if c.get("id") and (bg or desc):     # 로컬은 description 있는 도구(Bash)만 — Read 등 순간 도구 제외
                            open_tools[c["id"]] = dict(tool=c.get("name", ""), desc=desc[:80], bg=bg,
                                                       t=_epoch(d.get("timestamp", "")))
                        if c.get("name") == "SendMessage":   # 다른 세션으로 보낸 메시지
                            to = str((c.get("input") or {}).get("to") or "")
                            _note_comm(r, "send", to if to.startswith("uds:") else "", "" if to.startswith("uds:") else to, d.get("timestamp"))
    flush()
    r["tasks"] = list(open_tools.values())[-100:]   # 시작 순서 유지 — 이번 사이클의 전 작업 (안전 상한 100)
    return r


def parse_subagents(directory: str) -> dict:
    """subagents/agent-*.jsonl 을 합산: 개수·도구 카운트·출력 토큰."""
    agg = dict(count=0, tools=Counter(), out_tok=0, comm={})
    for p in glob.glob(os.path.join(directory, "agent-*.jsonl")):
        sub = parse(p)
        agg["count"] += 1
        agg["tools"] += sub["tools"]
        agg["out_tok"] += sub["out_tok"]
        for k, e in sub["comm"].items():                  # 서브에이전트의 송신은 부모 세션 주소로 나간다
            m = agg["comm"].setdefault(k, dict(e, n=0, last=None)); m["n"] += e["n"]
            if e["last"] and (m["last"] is None or e["last"] > m["last"]): m["last"] = e["last"]
    return agg
