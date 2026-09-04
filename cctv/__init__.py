"""eharness — 로컬 Claude Code 세션 전체를 밖에서 관측하는 개인용 운용 하네스."""
import json, os

VERSION = "0.1.0"
SCHEMA_VERSION = 1
CLAUDE_HOME = os.path.expanduser(os.environ.get("EHARNESS_CLAUDE_HOME", "~/.claude"))
EH_HOME = os.path.expanduser(os.environ.get("EHARNESS_HOME", "~/.eharness"))


def context_window() -> int:
    """설정 모델이 [1m]이면 1M, 아니면 200k. settings.json이 없거나 깨져도 200k."""
    try:
        model = json.load(open(os.path.join(CLAUDE_HOME, "settings.json"))).get("model", "")
    except (OSError, ValueError):
        model = ""
    return 1_000_000 if "[1m]" in model else 200_000
