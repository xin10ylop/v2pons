"""Per B launch: launch/pull tx details, swaps by group (A, B, fresh, outsider, us, ...), ETH in/out before the pull, after."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
from chain import rpc, batch
pools, head = load_all(); cw = annotate(pools)
d = json.load(open("b_list.json")); fam = d["fam"]; B7 = set(d["B7"])
def grp(x):
    if x["cls"] in ("us", "dust", "?"): return x["cls"]
    if x["from"] in fam: return fam[x["from"]]
    return "outsider"
out = {}
for p in pools:
    if p["pid"] not in B7: continue
    pb = p["pull"]
    print("=" * 100); print(utc(p["ts"]), p["pid"][:10], "fee", p["fee"], "b0", p["b0"], "deployer", p["deployer"], "token", p["m"].get("token"), "launch to", p["launch"].get("to") if p["launch"] else None)
    print("  mls:", [(m["bn"] - p["b0"], m["dl"], m["from"], m["to"], m["sel"], m["sender"]) for m in p["mls"]][:6])
    agg = collections.defaultdict(lambda: collections.Counter())
    for x in p["sw"]:
        g = grp(x); ph = "pre" if before_pull(p, x) else "post"
        a = agg[(g, ph)]
        if x["a0"] < 0: a["buys"] += 1; a["in"] += -x["a0"] / 1e18
        else: a["sells"] += 1; a["out"] += x["a0"] / 1e18
        a["wallets"] = 0
    wal = collections.defaultdict(set)
    for x in p["sw"]: wal[(grp(x), "pre" if before_pull(p, x) else "post")].add(x["from"])
    tot = 0
    for k in sorted(agg):
        a = agg[k]; net = a["in"] - a["out"]; 
        if k[1] == "pre": tot += net
        print(f"  {k[0]:9s} {k[1]:4s} wallets {len(wal[k]):3d} buys {a['buys']:4d} in {a['in']:8.4f} sells {a['sells']:4d} out {a['out']:8.4f} net_in {net:8.4f}")
    print(f"  net ETH into pool before pull (all swaps): {tot:.4f}; pull at +{pb['bn'] - p['b0'] if pb else None} by {pb['from'] if pb else None} tx {pb['tx'] if pb else None}")
    outs = [x["from"] for x in p["sw"] if grp(x) == "outsider"]
    print("  outsider wallets:", collections.Counter(outs).most_common(12))
    out[p["pid"]] = {"ts": p["ts"], "b0": p["b0"], "deployer": p["deployer"], "pull": pb, "token": p["m"].get("token"), "net_pre": tot,
                     "agg": {f"{k[0]}|{k[1]}": dict(v, wallets=len(wal[k])) for k, v in agg.items()}, "outsiders": collections.Counter(outs)}
json.dump(out, open("b_launches.json", "w"), indent=1, default=str)
