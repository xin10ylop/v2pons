"""Post-census pools: when does the bot's buying come after its first buy? Buys >= 0.01 ETH by T + 20/60/100/200/400 (Swap logs to
T+400, cached), and the same for the census by day; the follow trade at holds 60/100/200/300 on the fresh pools (pulls included)."""
import rpc, pickle
from sim import *
from eth_utils import keccak
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
cuts = (20, 60, 100, 200, 400)
def tl(sw, T): return [sum(x[4] for x in sw if T < x[0] <= T + c and x[3] and x[4] >= 10**16) / 1e18 for c in cuts]
byday = C.defaultdict(list)
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid]); byday[day_of(rows[pid]["launch_ts"])].append(tl(P.sw, tb[0]))
print("ETH of buys >= 0.01 after the trigger, by T+" + "/".join(map(str, cuts)) + " (median over pools; share of pools with any by T+60)")
for d in sorted(byday):
    xs = byday[d]; print(f"  census d{d}: n {len(xs)} medians {[round(pct([x[i] for x in xs], 0.5), 3) for i in range(len(cuts))]} any by T+60 {sum(1 for x in xs if x[1] > 0)/len(xs):.0%}")
FR = json.load(open(os.path.join(V, "fresh_replay.json"))); F = {x["pid"]: x for x in json.load(open(os.path.join(V, "fresh.json")))["c1"]}
cache = os.path.join(V, "fresh_logs400.json"); LG = json.load(open(cache)) if os.path.exists(cache) else {}
head = int(rpc.call("eth_blockNumber", []), 16)
xs = []; trades = C.defaultdict(list)
for o in FR:
    if not o["trig"]: continue
    if o["pid"] not in LG:
        LG[o["pid"]] = rpc.call("eth_getLogs", [{"fromBlock": hex(o["lb"]), "toBlock": hex(min(head, o["trig"] + 400)), "address": PM, "topics": [[T_SWAP, T_ML], o["pid"]]}])
    ev = []
    for l in sorted(LG[o["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); d = l["data"]
        if l["topics"][0] == T_SWAP: ev.append(["s", bn, 0, li, o["pid"], "", sgn(W(d, 0)), sgn(W(d, 1)), W(d, 2), W(d, 3), 0, 100, l["transactionHash"]])
        else: ev.append(["m", bn, 0, li, o["pid"], "", sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), "", l["transactionHash"]])
    r = {"quote_side": 0, "dex": "v4", "launch_block": o["lb"], "fee": 100, "tick0": F[o["pid"]]["tick"], "sqrt_p0": F[o["pid"]]["sqrt"], "pool": o["pid"], "launch_ts": 0}
    P = Pool(r, {"kind": "v4", "ev": ev}); x = tl(P.sw, o["trig"]); xs.append(x)
    line = f"  fresh {o['pid'][:12]} trig +{o['trig'] - o['lb']} ETH by cuts {[round(v, 3) for v in x]} pull {('T+' + str(P.first_pull - o['trig'])) if P.first_pull else '-'}"
    for H in (60, 100, 200, 300):
        a = o["trig"] + 2
        if a + H <= min(head, o["trig"] + 400):
            rr = P.replay(a, a + H, int(0.0058e18)); v = -1.0 if rr["pulled_le"] else rr["ret"]; trades[H].append(v); line += f" H{H} {v:+.3f}"
    print(line)
json.dump(LG, open(cache, "w"))
print(f"  fresh: n {len(xs)} medians {[round(pct([x[i] for x in xs], 0.5), 3) for i in range(len(cuts))]} any by T+60 {sum(1 for x in xs if x[1] > 0)/len(xs):.0%}")
for H, v in sorted(trades.items()): print(f"  fresh trade T+2 hold {H}: n {len(v)} mean {sum(v)/len(v):+.4f} med {pct(v,0.5):+.4f} win {sum(1 for y in v if y > 0)}/{len(v)} lost {sum(1 for y in v if y == -1)}")
print(rpc.STATS)
