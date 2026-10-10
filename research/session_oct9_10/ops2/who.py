"""all cached txs touching addresses in [lo, hi] (cache only, no RPC). usage: who.py lo hi addr..."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
lo, hi = int(sys.argv[1]), int(sys.argv[2])
for a in sys.argv[3:]:
    rs = touching([a], lo, hi, cached_only=True)
    print("==", a, lab(a.lower()), len(rs))
    for r in rs[:40]: print("  ", fmt(r), lab(r["from"]), "->", lab(r["to"]))
