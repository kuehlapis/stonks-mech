"""Make a bot variant: copy python/ to sim/versions/<name>/ and override module constants.

  python sim/variant.py NAME brain.FIGHT_EDGE=0.55 survival.HOLD_DEPTH=0.6 ...

Each override replaces the first line `NAME = ...` (or `A, B = ...` tuples are not supported) in that module.
"""
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    name, overrides = sys.argv[1], sys.argv[2:]
    dst = os.path.join(REPO, "sim", "versions", name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(REPO, "python"), dst, ignore=shutil.ignore_patterns("tests", "__pycache__", "Dockerfile"))
    for o in overrides:
        lhs, val = o.split("=", 1)
        mod, const = lhs.split(".")
        p = os.path.join(dst, mod + ".py")
        s = open(p, encoding="utf-8").read()
        s2, n = re.subn(rf"^{const}\s*=\s*[^#\n]*", f"{const} = {val}  ", s, count=1, flags=re.M)
        if n != 1:
            sys.exit(f"{const} not found in {mod}.py")
        open(p, "w", encoding="utf-8").write(s2)
    print(dst)


if __name__ == "__main__":
    main()
