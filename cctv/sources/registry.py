"""~/.claude/sessions/<pid>.json — 세션 레지스트리 (비공개 포맷, 읽기 전용)."""
import glob, json, os, re
from .. import CLAUDE_HOME

FIELDS = ("pid", "sessionId", "cwd", "name", "status", "startedAt", "kind")
OPTIONAL = ("messagingSocketPath",)


def alive(pid: int) -> bool:
    if os.name == "nt":   # Windows의 os.kill(pid, 0)은 TerminateProcess — 절대 쓰지 않는다. 핸들 조회로만 판정
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ok = k32.GetExitCodeProcess(h, ctypes.byref(code)); k32.CloseHandle(h)
            return bool(ok) and code.value == 259                 # STILL_ACTIVE
        except (OSError, TypeError, ValueError, AttributeError):
            return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def slug(cwd: str) -> str:
    """projects/<slug> — Claude Code 규칙: 경로 구분자(/, \\)와 드라이브 콜론을 '-'로."""
    return re.sub(r"[\\/:]", "-", cwd)


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
    return os.path.join(CLAUDE_HOME, "projects", slug(cwd), f"{sid}.jsonl")


def subagent_dir(cwd: str, sid: str) -> str:
    return os.path.join(CLAUDE_HOME, "projects", slug(cwd), sid, "subagents")
