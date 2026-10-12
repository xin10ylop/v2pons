"""transactions of each line pool's swaps, up to its first Burn (or launch + 3000): every swap up to 30 blocks after the crowd's first real
buy (a crowd-shaped call buying >= 0.005 ETH; until that buy is known, 30 blocks after the first buy >= 0.005 ETH by anyone), every sell
(token into the pool) up to the pull except the crowd's (Swap sender the UR, recipient a crowd contract seen in a crowd-shaped call), and the first Burn's: from, to, selector, calldata length, value, nonce, gas (input kept when
<= 1,000 bytes) -> r03_txs_cache.jsonl (resumable; run it until it fetches nothing: each pass extends to the crowd's buy found so far)."""
from common import *
import rpc
from wcommon import compact
L = json.load(open(J("r01_launches.json")))
E = {x["pool"]: x for x in jl(J("r02_events_cache.jsonl"))}
T = {t["hash"]: t for t in jl(J("r03_txs_cache.jsonl"))}
CROWD_TO = {t["to"] for t in T.values() if (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR}   # the crowd's contracts seen so far
want = set()
for x in L:
    e = E.get(x["pool"])
    if not e: continue
    qs = x["qs"]; anyb = crowd = None
    ev = [c for c in (compact(l) for l in sorted(e["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))) if c]
    for c in ev:
        if c[0] == "b":
            if c[8] > 0: want.add(c[-1]); break
            continue
        if c[0] != "s": continue
        dq = c[7] if qs == 0 else c[8]; t = T.get(c[12])
        if dq >= 5 * 10 ** 15:
            if anyb is None: anyb = c[1]
            if crowd is None and t and (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR: crowd = c[1]
        lim = (crowd + 30) if crowd is not None else (anyb + 30) if anyb is not None else None
        crowd_sell = dq < 0 and c[5] == UR and c[6] in CROWD_TO      # the crowd sells through the UR to its own contract: no need to fetch
        if lim is None or c[1] <= lim or (dq < 0 and not crowd_sell): want.add(c[12])
todo = sorted(want - set(T))
print(f"txs wanted {len(want)}, cached {len(T)}, to fetch {len(todo)}", flush=True)
f = open(J("r03_txs_cache.jsonl"), "a")
for i in range(0, len(todo), 200):
    ch = todo[i:i + 200]
    rs = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=20)
    for h, t in zip(ch, rs):
        if not t: print("missing", h); continue
        inp = t["input"]; n = (len(inp) - 2) // 2
        f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": inp[2:10], "len": n, "value": int(t["value"], 16),
                            "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
                            "input": inp if n <= 1000 else None}) + "\n")
    f.flush()
    if i % 4000 == 0: print(i, rpc.STATS, flush=True)
print("done", len(todo), rpc.STATS)
