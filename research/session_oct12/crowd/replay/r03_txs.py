"""Transactions behind the pools' swaps in [launch, launch + 200], every pool's Burns, and (pools whose crowd-shaped buy of >= 0.005 ETH is not in
those) the later buys of >= 0.005 WETH, in order, until the first crowd-shaped one. Incremental cache r03_txs_cache.jsonl: hash, from, to,
sel, n (calldata bytes), value, nonce, block, ti, gas limit, gas price, input (full up to 4 kB). Writes r03_txs.out."""
from common import *
import rpc, collections
EARLY = 200
X = json.load(open(J("r01_launches.json"))); P = {x["pool"]: x for x in X}
ev = jl(J("r02_events_cache.jsonl")); by = collections.defaultdict(list)
for e in ev: by[e["a"]].append(e)
C = J("r03_txs_cache.jsonl"); have = {t["hash"]: t for t in jl(C)}
def fetch(hs):
    todo = sorted(set(hs) - set(have))
    with open(C, "a") as f:
        for i in range(0, len(todo), 200):
            ch = todo[i:i + 200]
            for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch])):
                if t is None: print("missing", h); continue
                inp = t["input"]
                r = {"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": inp[2:10], "n": (len(inp) - 2) // 2, "value": int(t["value"], 16),
                     "nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "gas": int(t["gas"], 16),
                     "gp": int(t.get("gasPrice") or "0x0", 16), "input": inp[:2 + 8000]}
                have[h] = r; f.write(json.dumps(r) + "\n")
            f.flush(); print(f"  {min(i + 200, len(todo))}/{len(todo)} rpc {rpc.STATS}", flush=True)
need = set()
for p, x in P.items():
    for e in by[p]:
        if e["t"][0] == T_BU or e["bn"] - x["lb"] <= EARLY: need.add(e["tx"])
print(f"stage 1: {len(need)} txs, cached {len(need & set(have))}"); fetch(need)
def wq(e, qs): return sgn(W(e["d"], 0 if qs == 0 else 1))
def crowd_shaped(t): return (t["sel"], t["n"]) in CROWD_SHAPES and t["value"] == 0
for rnd in range(6):
    more = set(); open_pools = 0
    for p, x in P.items():
        buys = [e for e in by[p] if e["t"][0] == T_SW and wq(e, x["qs"]) >= 5 * 10 ** 15]
        found = False; k = 0
        for e in buys:
            t = have.get(e["tx"])
            if t is None:
                more.add(e["tx"]); k += 1
                if k >= 4: break
                continue
            if crowd_shaped(t): found = True; break
        if not found: open_pools += 1
    print(f"round {rnd}: pools without a crowd-shaped buy found yet {open_pools}; fetching {len(more)}")
    if not more: break
    fetch(more)
print("rpc", rpc.STATS)
