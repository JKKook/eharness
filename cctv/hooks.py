"""~/.claude/settings.json 에 관측용 훅을 멱등하게 병합/제거.

모드: async command (hooks/post-event.sh → curl → 수집기). http 타입은 async 미지원(동기 호출)이라 부하 시
도구 호출마다 지터가 세션에 얹혀 쓰지 않는다. 식별자: command 경로가 우리 스크립트이거나 url 이 우리 수집기인 항목."""
import json, os, shutil, time
from . import CLAUDE_HOME
from .collector import DEFAULT_PORT

EVENTS = ("SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure",
          "Stop", "SubagentStart", "SubagentStop", "Notification")
SETTINGS = os.path.join(CLAUDE_HOME, "settings.json")


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "hooks", "post-event.sh")


def _ours(h, port):
    if h.get("type") == "http":
        return h.get("url", "").startswith(f"http://127.0.0.1:{port}/")
    return h.get("type") == "command" and "eharness/hooks/post-event.sh" in h.get("command", "")


def _load():
    return json.load(open(SETTINGS)) if os.path.exists(SETTINGS) else {}


def _save(cfg):
    shutil.copy2(SETTINGS, SETTINGS + ".bak-eharness-" + time.strftime("%Y%m%d%H%M%S"))
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2); f.write("\n")
    os.replace(tmp, SETTINGS)


def install(port=DEFAULT_PORT, timeout=3):
    cfg = _load(); hooks = cfg.setdefault("hooks", {}); added = []
    for ev in EVENTS:
        groups = hooks.setdefault(ev, [])
        if any(_ours(h, port) for g in groups for h in g.get("hooks", [])):
            continue
        groups.append({"hooks": [{"type": "command", "command": SCRIPT, "async": True, "timeout": timeout}]})
        added.append(ev)
    if added:
        _save(cfg)
    print(f"installed on: {', '.join(added) or '(already present)'}")


def uninstall(port=DEFAULT_PORT):
    cfg = _load(); hooks = cfg.get("hooks", {}); removed = []
    for ev in list(hooks):
        kept = []
        for g in hooks[ev]:
            g["hooks"] = [h for h in g.get("hooks", []) if not _ours(h, port)]
            if g["hooks"]:
                kept.append(g)
            else:
                removed.append(ev)
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]
    if removed:
        _save(cfg)
    print(f"removed from: {', '.join(removed) or '(none)'}")


def status(port=DEFAULT_PORT):
    hooks = _load().get("hooks", {})
    for ev in EVENTS:
        on = any(_ours(h, port) for g in hooks.get(ev, []) for h in g.get("hooks", []))
        print(("on   " if on else "off  ") + ev)
