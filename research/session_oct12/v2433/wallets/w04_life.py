"""One launch wallet's life from full blocks: every tx from it, to it, or naming it in calldata, in [L-back, L+fwd] plus the pull window."""
from common import *
w, L, pid = sys.argv[1].lower(), int(sys.argv[2]), sys.argv[3]
back = int(sys.argv[4]) if len(sys.argv) > 4 else 1200
ml = rpc.logs({"address": PM, "topics": [T_ML, pid]}, L, L + 30000)
pulls = [int(m["blockNumber"], 16) for m in ml if sgn(W(m["data"], 2)) < 0]
print("ML", [(int(m["blockNumber"], 16) - L, sgn(W(m["data"], 2))) for m in ml][:6])
rng = list(range(L - back, L + 30))
if pulls: rng += list(range(pulls[0] - 5, pulls[0] + 120))
bl = get_blocks(rng)
wa = w[2:]
for n in sorted(bl):
    for t in bl[n]["txs"]:
        if t["f"] == w or t["to"] == w or wa in t["inp"][10:]:
            print(n - L, bl[n]["ts"], utc(bl[n]["ts"]), "from" if t["f"] == w else "to" if t["to"] == w else "names", t["f"][:12], "->", t["to"][:12], int(t["v"]) / 1e18, "nonce", t["nonce"], t["sel"], t["len"], t["h"][:14])
print(rpc.STATS)
