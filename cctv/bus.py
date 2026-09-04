"""events/YYYY-MM-DD.jsonl — append-only 이벤트 버스. 훅 입력에서 메타데이터만 남긴다(도구 인자·결과 본문 저장 안 함)."""
import glob, json, os, time
from . import EH_HOME

EVENTS_DIR = os.path.join(EH_HOME, "events")
KEEP = ("session_id", "hook_event_name", "tool_name", "tool_use_id", "agent_id", "agent_type", "cwd", "permission_mode", "prompt_id")
RENAME = {"session_id": "sid", "hook_event_name": "event", "tool_name": "tool"}


def to_event(hook_input: dict) -> dict:
    ev = {"v": 1, "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time()*1000)%1000:03d}Z"}
    for k in KEEP:
        if hook_input.get(k) not in (None, ""):
            ev[RENAME.get(k, k)] = hook_input[k]
    if hook_input.get("tool_name") == "SendMessage":          # 세션 간 메시지: 대상만(본문 없음)
        to = str((hook_input.get("tool_input") or {}).get("to") or "")
        if to:
            ev["to"] = to[:120]
    if hook_input.get("hook_event_name") == "PostToolUseFailure":
        ev["ok"] = False
    if hook_input.get("hook_event_name") == "SessionStart":
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
