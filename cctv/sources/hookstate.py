"""hook-state/<sid>.state (기존 tool-start/end 훅이 씀) + <sid>.ctx (M2: statusline이 씀)."""
import os
from .. import CLAUDE_HOME


def _kv(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path, errors="replace").read().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def state(sid: str) -> dict:
    return _kv(os.path.join(CLAUDE_HOME, "hook-state", f"{sid}.state"))


def ctx(sid: str) -> dict:
    """statusline이 기록한 실제값: CTX_PCT, COST_USD, TS. 없으면 {}."""
    return _kv(os.path.join(CLAUDE_HOME, "hook-state", f"{sid}.ctx"))


def cache_group(sid: str, group):
    """세션 그룹명을 hook-state/<sid>.group 으로 캐시 — statusline 이 [이름·그룹] 으로 표시. 변경 시에만 쓴다."""
    path = os.path.join(CLAUDE_HOME, "hook-state", f"{sid}.group")
    try:
        cur = open(path).read().strip() if os.path.exists(path) else None
        if not group:
            if cur is not None:
                os.remove(path)
        elif cur != group:
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                f.write(group + "\n")
            os.replace(tmp, path)
    except OSError:
        pass


def touch_notif(sid: str):
    """Notification 훅(권한 요청·입력 대기) 수신 시각을 <sid>.notif 파일 mtime 으로 기록."""
    try:
        with open(os.path.join(CLAUDE_HOME, "hook-state", f"{sid}.notif"), "w"):
            pass
    except OSError:
        pass


def mtime(sid: str, ext: str) -> float:
    try:
        return os.path.getmtime(os.path.join(CLAUDE_HOME, "hook-state", f"{sid}.{ext}"))
    except OSError:
        return 0.0
