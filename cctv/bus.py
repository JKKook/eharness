"""events/YYYY-MM-DD.jsonl — append-only 이벤트 버스. 훅 입력에서 메타데이터만 남긴다(도구 인자·결과 본문 저장 안 함)."""
import glob, json, os, re, time
from . import CLAUDE_HOME, EH_HOME

EVENTS_DIR = os.path.join(EH_HOME, "events")
KEEP = ("session_id", "hook_event_name", "tool_name", "tool_use_id", "agent_id", "agent_type", "cwd", "permission_mode", "prompt_id")
RENAME = {"session_id": "sid", "hook_event_name": "event", "tool_name": "tool"}
CANON = {e.lower(): e for e in ("SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
                                "PostToolUseFailure", "Stop", "SubagentStart", "SubagentStop", "Notification")}
_SOCK = re.compile(r"^uds:/tmp/cc-socks/(\d+)\.sock$")


def _sock_name(to: str):
    """G5: uds 소켓 주소를 레지스트리에서 세션 이름으로 역해석 (이벤트 시각 기준, 읽기 전용)."""
    m = _SOCK.match(to)
    if not m:
        return None
    try:
        return json.load(open(os.path.join(CLAUDE_HOME, "sessions", f"{m.group(1)}.json"))).get("name")
    except (OSError, ValueError):
        return None


def to_event(hook_input: dict) -> dict:
    ev = {"v": 1, "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time()*1000)%1000:03d}Z"}
    for k in KEEP:
        if hook_input.get(k) not in (None, ""):
            ev[RENAME.get(k, k)] = hook_input[k]
    name = ev.get("event")
    if isinstance(name, str):                                 # G3: 이벤트명 변형(sessionEnd 등) 정규화
        ev["event"] = CANON.get(name.lower(), name)
    ti = hook_input.get("tool_input") or {}
    tool = hook_input.get("tool_name")
    if tool == "SendMessage":                                 # 세션 간 메시지: 대상만(본문 없음)
        to = str(ti.get("to") or "")
        if to:
            ev["to"] = to[:120]
            n = _sock_name(to)                                # G5: 회신(uds 주소)의 수신자 이름
            if n:
                ev["to_name"] = n
    elif tool == "Skill" and ti.get("skill"):                 # G1: 어떤 스킬을 썼는지
        ev["skill"] = str(ti["skill"])[:80]
    elif tool in ("Agent", "Task") and ti.get("subagent_type"):   # G2 보조: 위임 시점의 유형
        ev["agent_type"] = str(ti["subagent_type"])[:60]
    if "agent_type" not in ev and hook_input.get("subagent_type"):    # G2: 대체 키 수용
        ev["agent_type"] = str(hook_input["subagent_type"])[:60]
    if ev.get("event") == "Notification":                     # G4: 입력 대기 vs 권한 요청 구분 근거
        msg = str(hook_input.get("message") or "")
        if msg:
            ev["msg"] = msg[:120]
    if ev.get("event") == "PostToolUseFailure":
        ev["ok"] = False
    if ev.get("event") == "SessionStart":
        ev["source"] = hook_input.get("source")
    return ev


def append(ev: dict) -> str:
    os.makedirs(EVENTS_DIR, exist_ok=True)
    path = os.path.join(EVENTS_DIR, time.strftime("%Y-%m-%d") + ".jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return path


def files():
    return sorted(glob.glob(os.path.join(EVENTS_DIR, "*.jsonl")))


def read(days=1, sid=None):
    for path in files()[-days:]:
        for line in open(path, errors="replace"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if sid is None or ev.get("sid", "").startswith(sid):
                yield ev


def prune(keep_days=14):
    cutoff = time.time() - keep_days * 86400
    for path in files():
        if os.path.getmtime(path) < cutoff:
            os.remove(path)
