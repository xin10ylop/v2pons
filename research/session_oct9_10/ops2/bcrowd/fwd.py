"""first outgoing tx(s) of an address scanning forward chunk by chunk from block a (max n blocks). usage: fwd.py addr a n [want]"""
import sys
from libb import *
import json
b = json.load(open('/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/b_list.json')); lab = {w: '[B]' for w in b['B']}; lab.update({w: '[A]' for w in b['A']})
addr = sys.argv[1].lower(); a = int(sys.argv[2]); n = int(sys.argv[3]); want = int(sys.argv[4]) if len(sys.argv) > 4 else 1
got = 0
for c in range(a // 250, (a + n) // 250 + 1):
    s = max(a, c * 250); e = min(a + n - 1, c * 250 + 249)
    for r in touching([addr], s, e):
        print(fmt(r, lab), flush=True)
        if r["from"] == addr: got += 1
    if got >= want: break
print("scanned to", e, bc.STATS, flush=True)
