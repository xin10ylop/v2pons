"""Scan full blocks forward (or backward with a negative max) from a block, printing every tx from / to / naming an address; stops once the
address's tx with nonce >= stop_nonce is seen (forward) or after max blocks."""
from common import *
w, a, mx = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3])
stop = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
step = 200; wa = w[2:]; seen = 0
rng = range(a, a + mx, step) if mx > 0 else range(a, a + mx, -step)
for s in rng:
    ns = list(range(s, s + step)) if mx > 0 else list(range(s - step + 1, s + 1))
    bl = get_blocks(ns)
    done = False
    for n in sorted(bl):
        for t in bl[n]["txs"]:
            if t["f"] == w or t["to"] == w or wa in t["inp"][10:]:
                print(n, utc(bl[n]["ts"]), "from" if t["f"] == w else "to" if t["to"] == w else "names", t["f"], "->", t["to"], int(t["v"]) / 1e18, "nonce", t["nonce"], t["sel"], t["len"], t["h"], flush=True)
                if t["f"] == w and t["nonce"] >= stop: done = True
    if done: break
print("scanned to", ns[-1], rpc.STATS)
