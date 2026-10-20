import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
for a, lo, hi in [("0xe50dd00a357018225b86e232e5cb8b762b533556", 83481000, 83518499), ("0xded28cc0001917222aa2b55ad55f1d236ef1be74", 83396250, 83403249)]:
    print("==", a)
    rs = touching([a], lo, hi, cached_only=True)
    for r in rs[:80]:
        print("  ", fmt(r), lab(r["from"]), "->", lab(r["to"]))
    print("   total", len(rs), "in", sum(1 for r in rs if r["to"] == a), "sum in", sum(r["eth"] for r in rs if r["to"] == a))
