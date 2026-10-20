"""Does the engine's trigger_word (src/flip_engine.py, copied verbatim below) take any of the crowd's SELLS for buys? Every fetched
transaction behind a swap of an r01 pool (r03 cache) that has one of the three call shapes and value 0 is passed through it with the
pool's token, and compared with the swap's direction on the chain. Also: ETH-value calls carrying the token (ingest_tx's buy) that were
sells on the chain."""
from common import *
import collections
X = json.load(open(J("r01_launches.json"))); ev = jl(J("r02_events_cache.jsonl")); TX = {t["hash"]: t for t in jl(J("r03_txs_cache.jsonl"))}
P = {x["pool"]: x for x in X if x["qs"] == 0}
WETH_BYTES = bytes.fromhex(WETH[2:])
def trigger_word(shapes, data, token_bytes, fee=100):      # the engine's, any_to and token_anywhere (the v3crowd family's trigger)
    sel = data[:4].hex(); vw = shapes.get((sel, len(data)), shapes.get((sel, 0)))
    if vw is None: return None
    tok = token_bytes; path = WETH_BYTES + fee.to_bytes(3, "big"); i = data.find(tok)
    while i >= 0:
        if ((i - 4) % 32 == 12 and data[i - 12:i] == bytes(12)) or ((i - 4) % 32 == 23 and data[i - 23:i] == path):
            return vw
        i = data.find(tok, i + 1)
    return None
c = collections.Counter(); ex = []
for e in ev:
    x = P.get(e["a"])
    if x is None or e["t"][0] != T_SW: continue
    t = TX.get(e["tx"])
    if t is None or len(t["input"]) >= 2 + 8000: continue
    a0 = sgn(W(e["d"], 0)); data = bytes.fromhex(t["input"][2:]); tok = bytes.fromhex(x["token"][2:])
    if t["value"] == 0 and (t["sel"], t["n"]) in CROWD_SHAPES:
        vw = trigger_word(CROWD_SHAPES, data, tok)
        side = "buy" if a0 > 0 else "sell"
        c[(side, t["to"][:10], t["sel"], vw is not None)] += 1
        if vw is not None and a0 < 0 and len(ex) < 6:
            ex.append((e["tx"], e["bn"] - x["lb"], t["to"], t["sel"], int(t["input"][2 + 8 + 64 * vw: 2 + 8 + 64 * (vw + 1)], 16) / 1e18, a0 / 1e18))
    elif t["value"] > 0 and tok in data and a0 < 0:
        c[("ETH-value call that SOLD", t["to"][:10], t["sel"], True)] += 1
for k, v in sorted(c.items(), key=lambda kv: -kv[1]): print(k, v)
print("sells the engine reads as buys (tx, offset, to, sel, the engine's amount, the swap's WETH):"); [print("  ", e) for e in ex]
