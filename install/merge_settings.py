"""settings.json 에 훅·statusLine 스니펫을 병합 — command 경로 기준 멱등, 백업 → tmp → os.replace.
usage: merge_settings.py <settings.json> <snippet.json>   (스니펫 형식: {"hooks": {...}, "statusLine": {...}})"""
import json, os, shutil, sys, time


def merge(cfg, add):
    """(변경된 cfg, 추가/갱신 건수). 같은 command 가 이미 있으면 건너뛴다."""
    hooks = cfg.setdefault("hooks", {})
    n = 0
    for ev, groups in add.get("hooks", {}).items():
        have = {h.get("command") for g in hooks.setdefault(ev, []) for h in g.get("hooks", [])}
        for g in groups:
            g2 = {**g, "hooks": [h for h in g["hooks"] if h.get("command") not in have]}
            if g2["hooks"]:
                hooks[ev].append(g2); n += len(g2["hooks"])
    if "statusLine" in add and cfg.get("statusLine") != add["statusLine"]:
        cfg["statusLine"] = add["statusLine"]; n += 1
    return cfg, n


def main(path, snip):
    cfg = json.load(open(path)) if os.path.exists(path) else {}
    cfg, n = merge(cfg, json.load(open(snip)))
    if n:
        if os.path.exists(path):
            shutil.copy2(path, f"{path}.bak-install-{time.strftime('%Y%m%d%H%M%S')}")
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2); f.write("\n")
        os.replace(tmp, path)
    print(f"settings.json: {n}개 항목 추가/갱신" if n else "settings.json: 변경 없음(이미 병합됨)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
