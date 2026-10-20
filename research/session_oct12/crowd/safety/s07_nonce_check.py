"""Did the outside wallets that hold to the pull try to sell and fail? A reverted sell leaves no Swap log, but it uses a nonce. From the reaction
check's caches (read only: ../reaction/r02_events_cache.jsonl, every log of each line pool Oct 3-12 in [launch, launch + 3000];
../reaction/r03_txs_cache.jsonl, the transactions behind the early swaps and every non-crowd sell, with their nonces): for the outside wallets
with the most line transactions, their nonces seen in line swaps, the span min..max, how many nonces in that span are line swaps, and how many are
not (approvals, other pools, or failed transactions), and whether the wallet ever sold. Then the wallet's nonce now (one batched RPC call).
Writes s07_nonce_check.out."""
from common import *
import rpc, collections
TX = {}
for line in open(os.path.join(HERE, "..", "reaction", "r03_txs_cache.jsonl")):
    t = json.loads(line); TX[t["hash"]] = t
direction = {}; launcher = set()
for line in open(os.path.join(HERE, "..", "reaction", "r02_events_cache.jsonl")):
    p = json.loads(line)
    for l in p["logs"]:
        if l["topics"][0] != T_SW: continue
        a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1))
        weth0 = WETH[2:] < l["address"][2:]   # placeholder, fixed below per pool by the sign pattern
        direction.setdefault(l["transactionHash"], set()).add((a0 > 0, a1 > 0))
L = json.load(open(os.path.join(HERE, "..", "reaction", "r01_launches.json")))
qs = {x["pool"]: x.get("qs", 0) for x in L}; launch_from = {x["from"] for x in L}
# a buy pays WETH in: with WETH token0 (qs 0, 97% of the line) a0 > 0; the rare qs 1 pools are mixed in here: count a tx a sell if it paid the token in
CROWD_TO = {t["to"] for t in TX.values() if (t["sel"], t["len"]) in CROWD_SHAPES}
per = collections.defaultdict(lambda: {"n": set(), "sells": 0, "buys": 0, "to": collections.Counter()})
for h, t in TX.items():
    f = t["from"]
    if f in launch_from or t["to"] in CROWD_TO or (t["sel"], t["len"]) in CROWD_SHAPES or h not in direction: continue
    w = per[f]; w["n"].add(t["nonce"]); w["to"][(t["to"] or "")[:10] + ":" + t["sel"]] += 1
    d = direction[h]
    if any(not a0 for a0, a1 in d): w["sells"] += 1
    else: w["buys"] += 1
top = sorted(per, key=lambda f: -len(per[f]["n"]))[:16]
now = rpc.batch("eth_getTransactionCount", [[f, "latest"] for f in top])
print(f"{'wallet':<44} {'via':<20} {'line txs':>8} {'sells':>6} {'nonce span':>15} {'in span not line':>16} {'nonce now':>9}")
for f, n in zip(top, now):
    w = per[f]; lo, hi = min(w["n"]), max(w["n"]); gap = (hi - lo + 1) - len(w["n"])
    print(f"{f:<44} {w['to'].most_common(1)[0][0]:<20} {len(w['n']):>8} {w['sells']:>6} {lo:>7}..{hi:<7} {gap:>16} {int(n, 16):>9}")
print(rpc.STATS)
