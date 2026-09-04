import argparse
from . import core


def main(argv=None):
    p = argparse.ArgumentParser(prog="eharness wire", description="scaffold 자산을 능력 단위로 ~/.claude에 배선")
    p.add_argument("capability", nargs="?", help="능력 이름 (capability 태그)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--install", action="store_true")
    g.add_argument("--uninstall", action="store_true")
    g.add_argument("--status", action="store_true", help="기본 동작")
    a = p.parse_args(argv)
    if a.install or a.uninstall:
        if not a.capability:
            p.error("--install/--uninstall 은 capability 가 필요하다")
        (core.install if a.install else core.uninstall)(a.capability)
    else:
        core.status(a.capability)
