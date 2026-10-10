"""Skeptic f2276/100: the hub 0xbae53801 (EOA, nonce 3,067) that the funded launcher sent 14.2 ETH to: its transactions in the 3,000
blocks after it received them (to, value, selector), and how many of its recipients are the app router, crowd wallets or launchers."""
import sys, os, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import load_pools, load_txs
HUB = "0xbae538011874261e3fb4ca6aa03cacb2766c4d81"; ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
A = 84_326_143 - 1500; B = 84_326_143 + 3000
cp = os.path.join(D, "hub_blocks.json")
C = json.load(open(cp)) if os.path.exists(cp) else {}
need = [b for b in range(A, B) if str(b) not in C]
for j in range(0, len(need), 50):
    res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in need[j:j + 50]])
    for b, blk in zip(need[j:j + 50], res):
        C[str(b)] = [[t["from"], t["to"], int(t["value"], 16), t["input"][:10], t["hash"], int(t["nonce"], 16), len(t["input"]) // 2 - 1, t["input"][:300]]
                     for t in (blk or {}).get("transactions", []) if t["from"] == HUB or (t["to"] or "") == HUB]
    time.sleep(0.15)
json.dump(C, open(cp, "w"))
crowd = set(json.load(open(os.path.join(HERE, "a3_flows.json")))["crowd_wallets"])
P = load_pools(); launchers = set(p["launch_from"] for p in P.values() if p["family"].endswith("|2276|100|1|true"))
T = load_txs(); crowd_all = set(t["from"] for t in T.values() if t["to"] == ROUTER) | crowd
outs = collections.Counter(); ins = collections.Counter(); kinds = collections.Counter(); vals = []
for b in sorted(C, key=int):
    for t in C[b]:
        if t[0] == HUB:
            k = "router" if t[1] == ROUTER else ("crowd wallet" if t[1] in crowd_all else ("launcher" if t[1] in launchers else "other"))
            kinds[(k, t[3], t[6])] += 1; outs[t[1]] += 1; vals.append(t[2] / 1e18)
        else: ins[(t[0], t[3])] += 1
print("hub txs out in window:", sum(outs.values()), "distinct recipients", len(outs))
for k, v in kinds.most_common(10): print("   ", k, v)
print("value out quantiles", sorted(vals)[::max(1, len(vals) // 10)][:12])
print("txs INTO the hub (from, sel):", ins.most_common(10))
ex = [t for b in sorted(C, key=int) for t in C[b] if t[0] == HUB][:3]
for t in ex: print("  example", t[1], t[2] / 1e18, t[3], t[6], t[7][:200])
json.dump({"kinds": [[list(k), v] for k, v in kinds.most_common()], "ins": [[list(k), v] for k, v in ins.most_common()]}, open(os.path.join(HERE, "f7_hub.json"), "w"), indent=1)
