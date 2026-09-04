"""~/.claude/sessions/<pid>.json — 세션 레지스트리 (비공개 포맷, 읽기 전용)."""
import glob, json, os
from .. import CLAUDE_HOME

FIELDS = ("pid", "sessionId", "cwd", "name", "status", "startedAt", "kind")
OPTIONAL = ("messagingSocketPath",)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def sessions(include_dead: bool = False):
    for path in sorted(glob.glob(os.path.join(CLAUDE_HOME, "sessions", "*.json"))):
        try:
            d = json.load(open(path))
        except (OSError, ValueError):
            continue
        if "sessionId" not in d:
            continue
        d["alive"] = alive(d.get("pid"))
        if include_dead or d["alive"]:
            yield d


def transcript_path(cwd: str, sid: str) -> str:
    return os.path.join(CLAUDE_HOME, "projects", cwd.replace("/", "-"), f"{sid}.jsonl")


def subagent_dir(cwd: str, sid: str) -> str:
    return os.path.join(CLAUDE_HOME, "projects", cwd.replace("/", "-"), sid, "subagents")
