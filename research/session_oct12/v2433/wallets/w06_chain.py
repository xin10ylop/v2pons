"""The last 150 v2.433 launches before the stop: per launch its pool's pull (ModifyLiquidity < 0), then full blocks [P, P+220] after the
pull and [L-220, L] before the launch, keeping every tx from / to a launch wallet (funding in, sweep out). Output w06_chain.json."""
from common import *
import collections
ini = {r["tx"]: r for r in jl(J("w01_inits_cache.jsonl"))}
ltx = [t for t in jl(J("w02_ltx_cache.jsonl")) if int(t["v"]) == V2433 and t["to"] == POSM and t["len"] == 1444]
ltx.sort(key=lambda t: t["b"])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
sel = ltx[-N:]
L = [{"L": t["b"], "w": t["f"], "nonce": t["nonce"], "tx": t["h"], "pid": ini[t["h"]]["pid"], "fee": ini[t["h"]]["fee"]} for t in sel]
print(len(L), "launches", L[0]["L"], "..", L[-1]["L"])
h, th = head()
# pulls: one getLogs per 30 pools over [first L, head]
pid2 = {x["pid"]: x for x in L}
for i in range(0, len(L), 30):
    ch = [x["pid"] for x in L[i:i + 30]]
    for a in range(L[i]["L"], h + 1, 100000):
        for m in rpc.logs({"address": PM, "topics": [T_ML, ch]}, a, min(a + 99999, h)):
            x = pid2[m["topics"][1]]; dl = sgn(W(m["data"], 2)); b = int(m["blockNumber"], 16)
            if dl < 0 and x.get("P") is None: x["P"] = b; x["pull_tx"] = m["transactionHash"]
            if dl > 0: x["mint_L"] = dl
print("pulled", sum(1 for x in L if x.get("P")), "of", len(L))
W_ = {x["w"] for x in L}
want = set()
for x in L:
    want |= set(range(x["L"] - 220, x["L"] + 1))
    if x.get("P"): want |= set(range(x["P"], x["P"] + 221))
want = sorted(want); print("blocks to read", len(want))
bl = {}
for i in range(0, len(want), 1000):
    bl.update(get_blocks(want[i:i + 1000])); print("read", i + 1000, rpc.STATS, flush=True)
ev = []
for n in sorted(bl):
    for t in bl[n]["txs"]:
        if t["f"] in W_ or t["to"] in W_:
            ev.append({"b": n, "ts": bl[n]["ts"], "f": t["f"], "to": t["to"], "v": t["v"], "nonce": t["nonce"], "sel": t["sel"], "len": t["len"], "h": t["h"]})
json.dump({"launches": L, "events": ev, "head": h, "head_ts": th}, open(J("w06_chain.json"), "w"))
print("events", len(ev), rpc.STATS)
