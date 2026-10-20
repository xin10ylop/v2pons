import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
X = ["0x5b18301c6d69c6916d01bda3d6a62818206f8ca9", "0x94e12c341cd84e1f8c17300813d46a3427b5c498", "0x5477a0daa7e8510ade3822bc5b7d78cc31494b1c", "0x92b66c43b3f27c258877847c8c420e554daf4fd1"]
for a in X:
    rs = touching([a], 83340750, 83342749, cached_only=True)
    print("==", a, len(rs), "txs; in", sum(1 for r in rs if r["to"] == a), "out", sum(1 for r in rs if r["from"] == a))
    for r in rs[:12]: print("  ", fmt(r), lab(r["from"]), "->", lab(r["to"]))
    if len(rs) > 12:
        print("   ...")
        for r in rs[-6:]: print("  ", fmt(r), lab(r["from"]), "->", lab(r["to"]))
