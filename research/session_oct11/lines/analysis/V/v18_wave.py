"""The wave after the trigger, census vs post-census: per pool, ETH bought (buys >= 0.01 ETH; non-bot buys are 0.4 of 592 ETH in these
windows, v14) in [T+2, T+62), the number of such buys, and pools with none. Census by 6-hour slice over the last 48 h; post-census pools
re-read from the chain (Swap logs only, cached in fresh_logs.json)."""
import rpc, pickle, datetime
from sim import *
from eth_utils import keccak
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
def wave(sw, T):
    b = [x for x in sw if T + 2 <= x[0] < T + 62 and x[3] and x[4] >= 10**16]
    return len(b), sum(x[4] for x in b) / 1e18
def show(name, ws):
    if not ws: print(f"{name}: none"); return
    print(f"{name}: pools {len(ws)} | buys>=0.01 per pool p10/50/90 {p3([w[0] for w in ws])} | ETH p10/50/90 {p3([w[1] for w in ws])} | pools with no such buy {sum(1 for w in ws if w[0] == 0)} ({sum(1 for w in ws if w[0] == 0)/len(ws):.0%})")
byday = C.defaultdict(list); slices = C.defaultdict(list)
t_end = T0 + 7 * 86400
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid]); w = wave(P.sw, tb[0]); ts = rows[pid]["launch_ts"]
    byday[day_of(ts)].append(w)
    if ts >= t_end - 48 * 3600: slices[int((ts - (t_end - 48 * 3600)) // (6 * 3600))].append(w)
for d in sorted(byday): show(f"census d{d}", byday[d])
for s in sorted(slices): show(f"census last-48h slice {s} ({datetime.datetime.utcfromtimestamp(t_end - 48*3600 + s*6*3600).strftime('%m-%d %H:%M')}+6h)", slices[s])
# post-census
FR = json.load(open(os.path.join(V, "fresh_replay.json"))); F = {x["pid"]: x for x in json.load(open(os.path.join(V, "fresh.json")))["c1"]}
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
cache = os.path.join(V, "fresh_logs.json"); LG = json.load(open(cache)) if os.path.exists(cache) else {}
ws = []
for o in FR:
    if not o["trig"]: continue
    if o["pid"] not in LG:
        LG[o["pid"]] = rpc.call("eth_getLogs", [{"fromBlock": hex(o["trig"]), "toBlock": hex(o["trig"] + 62), "address": PM, "topics": [T_SWAP, o["pid"]]}])
    sw = []
    for l in LG[o["pid"]]:
        a0 = sgn(W(l["data"], 0)); sw.append((int(l["blockNumber"], 16), 0, 0, a0 < 0, abs(a0)))
    w = wave(sw, o["trig"]); ws.append(w)
    print(f"  fresh {o['pid'][:12]} trig +{o['trig'] - o['lb']}: wave buys {w[0]} ETH {w[1]:.3f} trade {o.get('ret')}")
json.dump(LG, open(cache, "w"))
show("post-census (Oct 11 13:52 -> head)", ws)
