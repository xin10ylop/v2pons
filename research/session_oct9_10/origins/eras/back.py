"""follow money backwards: for addr, scan back from block `bn` in 200-block chunks (max `lim` blocks) for value transfers INTO it; follow the largest
   inbound for up to `hops` hops. usage: back.py addr bn [lim] [hops]"""
from B import *
a, bn = sys.argv[1].lower(), int(sys.argv[2]); lim = int(sys.argv[3]) if len(sys.argv) > 3 else 3000; hops = int(sys.argv[4]) if len(sys.argv) > 4 else 3
for h in range(hops):
    found = []; c = (bn // CH) * CH
    while not found and c >= bn - lim:
        rr = [q for q in chunk(c) if q[0] <= bn]
        found = [q for q in rr if q[4] == a and int(q[5]) > 0]
        outs_ = [q for q in rr if q[3] == a]
        c -= CH
    if not found: print(f"hop {h}: {a}: no inbound value within {lim} blocks before {bn}"); break
    for q in found: print(f"hop {h}:", fmt(q))
    big = max(found, key=lambda q: int(q[5]))
    tot = sum(int(q[5]) for q in found) / 1e18
    print(f"   -> {len(found)} inbound to {a[:10]} in that chunk, total {tot:.4f}; following largest from {big[3]} (sender nonce {big[6]})", flush=True)
    a, bn = big[3], big[0]
