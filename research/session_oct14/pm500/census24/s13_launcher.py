"""Step 13: the launcher's own transactions and its funding, for a sample of launches spread over the day: every transaction from or
to the launcher in full blocks [L-B, A+2] and [pull-2, pull+60] (B grows until the funding transfer is found, up to 6,000 blocks)."""
import sys, collections
from common import *
pools = load_pools()
idx = [0, 1, 2, 30, 31, 60, 61, 90, 91, 120, 121, 126]
out = []
def scan(a, b, who):
    hits = []
    for s in range(a, b + 1, 200):
        e = min(b, s + 199)
        blocks = rpc.batch("eth_getBlockByNumber", [[hex(x), True] for x in range(s, e + 1)], n=25)
        for blk in blocks:
            for t in blk["transactions"]:
                f = t["from"].lower(); to = (t.get("to") or "").lower()
                if f == who or to == who:
                    hits.append(dict(bn=int(t["blockNumber"], 16), h=t["hash"], f=f, to=to, n=int(t["nonce"], 16), v=int(t["value"], 16),
                                     sel=t["input"][:10], il=(len(t["input"]) - 2) // 2))
    return hits
for i in idx:
    p = pools[i]; w = p["launcher"]; L = p["L"]
    hits = scan(p["L"] - 300, p["add_bn"] + 2, w)
    B = 300
    while not any(h["to"] == w and h["v"] > 0 for h in hits) and B < 6000:
        hits = scan(L - 2 * B, L - B - 1, w) + hits; B *= 2
    if "pull_bn" in p: hits += scan(p["pull_bn"] - 2, p["pull_bn"] + 60, w)
    hits.sort(key=lambda h: (h["bn"], h["n"]))
    print(f"=== launch L {L} launcher {w} add +{p['add_off']} pull +{p.get('pull_off')}")
    for h in hits:
        print(f"   {h['bn']-L:+6d} {'OUT' if h['f']==w else 'IN '} nonce {h['n']:3d} from {h['f'][:10]} to {h['to'][:10]} value {h['v']/1e18:.6f} sel {h['sel']} len {h['il']}")
    out.append(dict(L=L, launcher=w, txs=hits))
    sys.stdout.flush()
jdump(out, "s13_launcher.json")
print(rpc.STATS)
