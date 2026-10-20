"""0x3fc5b8b8 in every cached block range (no RPC): all txs from/to it"""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
rng = [(83057750, 83095499), (83181000, 83224999), (83236750, 83237999), (83240750, 83319749), (83340750, 83342749), (83385500, 83386749), (83396250, 83403249),
       (83408750, 83410249), (83430250, 83430999), (83432000, 83432499), (83456250, 83456999), (83458000, 83458749), (83479250, 83479999), (83481000, 83518499),
       (83647500, 83647999), (83650250, 83665249), (83667500, 83668249), (83677250, 83678249), (83680500, 83681249), (83906500, 83927999)]
for a, b in rng:
    rs = touching([C], a, b, cached_only=True)
    ins = [r for r in rs if r["to"] == C]; outs = [r for r in rs if r["from"] == C]
    print(f"[{a}-{b}] in {len(ins)} out {len(outs)}")
    for r in rs[:6] + (rs[-4:] if len(rs) > 10 else rs[6:]): print("   ", fmt(r))
print(bc.STATS)
