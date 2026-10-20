import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
from chain import batch
pools, head = load_all(); cw = annotate(pools)
print("non-crowd buys 0.0001-0.0002 and >=0.0002 (who, eth, value, to, len, off, lag):")
rows = []
for p in pools:
    pb = p["pull"]["bn"] if p["pull"] else None
    for x in p["sw"]:
        if x["a0"] < 0 and x["cls"] in ("outsider", "dust", "?") and before_pull(p, x) and -x["a0"] >= 1e14:
            f = x["fp"] or {}
            rows.append((p, x))
            print(f"  {utc(p['ts'])} {p['kind']} {p['pid'][:10]} {x['from'][:10] if x['from'] else None} {-x['a0']/1e18:.6f} value {(x['value'] or 0)/1e18:.6f} to {(x['to'] or '')[:10]} len {f.get('len')} off +{x['bn']-p['b0']} lag {(pb - x['bn']) if pb else None}")
# who was the 1124-byte type-0 UR tx
for p in pools:
    for x in p["sw"]:
        f = x["fp"] or {}
        if x["a0"] < 0 and x["cls"] == "outsider" and f.get("len") == 1124:
            print("1124-byte outsider:", utc(p["ts"]), p["pid"][:10], x["from"], f, -x["a0"]/1e18, "nonce", x["nonce"])
# value-0 contract buys >= 0.0002: does the calldata carry the pool's token address?
v0 = [(p, x) for p, x in rows if -x["a0"] >= 2e14 and not x["value"]]
txs = batch([("eth_getTransactionByHash", [x["tx"]]) for p, x in v0])
for (p, x), t in zip(v0, txs):
    tok = (p["m"].get("token") or "").lower().replace("0x", "")
    inp = t["input"].lower()
    print(f"value-0 buy {utc(p['ts'])} {p['pid'][:10]} from {t['from'][:10]} to {t['to'][:10]} len {len(inp)//2-1} token in calldata: {tok in inp} sel {inp[:10]}")
