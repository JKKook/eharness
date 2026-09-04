import json


def dump(rows):
    return json.dumps([{**r, "tools": dict(r["tools"])} for r in rows], ensure_ascii=False, indent=1)
