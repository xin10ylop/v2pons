"""F4a trap test: what precedes each pull (the last 6 swaps before it) vs a baseline (6 swaps before live+700 in 40 unpulled pools)"""
import sys, os, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
C = json.load(open("cache/fetch2.json")); P = load_pools(); T = load_txs()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
F4a = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1 and p["hooks_zero"]]
E = load_events(set(F4a))
CROWD = {"0x410499a03705092ed02a231783d6e96332d84feb", "0xebe93d2f86639869af18b9fc77a3439092ee0e90", "0x628bd69ecbc135cdda02ffd6d6db918f5cd835ce",
         "0x055de4ce27753aab185eb4387851ea12b00bb341", "0xe394ba9ff1b3d7337e01f89537a5c4980af1e439"}
def cls(s):
    t = C["tx"].get(s["tx"]) or T.get(s["tx"])
    if not t: return "?"
    if t["to"] in CROWD and t["selector"] == "7169b574": return "crowd-buy" if s["a0"] < 0 else "crowd-sell"
    if t["to"] == "0x4f881c6afe5ced5e4469b15269fd0c1390f089c6": return "tester-" + ("buy" if s["a0"] < 0 else "sell")
    if t["from"] == "0xe71a69f434a719cd5afa411568b69716aab3b84a": return "dust"
    return "other-" + ("buy" if s["a0"] < 0 else "sell") + ":" + (t["to"] or "")[:10] + ":" + t["selector"]
pre = collections.Counter(); base = collections.Counter(); last = collections.Counter(); gaps = []
outs_pre = []
for pid in F4a:
    e = E[pid]; lb = e["adds"][0]["bn"]
    if e["pulls"]:
        pb = e["pulls"][0]["bn"]; prev = [s for s in e["swaps"] if s["bn"] <= pb][-6:]
        for s in prev: pre[cls(s).split(":")[0]] += 1
        if prev: last[cls(prev[-1])] += 1; gaps.append(pb - prev[-1]["bn"])
        o = [s for s in prev if cls(s).startswith("other-buy")]
        if o: outs_pre.append((pid[:10], pb - lb, [(pb - s["bn"], round(-s["a0"] / 1e18, 5), cls(s)) for s in o]))
    else:
        prev = [s for s in e["swaps"] if s["bn"] <= lb + 700][-6:]
        if any(s["tx"] in C["tx"] or s["tx"] in T for s in prev):
            for s in prev: base[cls(s).split(":")[0]] += 1
print("6 swaps before each pull (57 pools):", pre.most_common())
print("baseline 6 swaps before live+700 (unpulled pools):", base.most_common())
print("the swap just before the pull:", last.most_common(6))
print("blocks from the last swap to the pull p10/50/90:", sorted(gaps)[len(gaps) // 10], sorted(gaps)[len(gaps) // 2], sorted(gaps)[9 * len(gaps) // 10])
print("pools whose last 6 swaps before the pull include an outside buy:", len(outs_pre))
for r in outs_pre[:15]: print("  ", r)
# other buyers by router over all fetched txs
oth = collections.Counter()
for h, t in C["tx"].items():
    if t["to"] not in CROWD and t["to"] != "0x4f881c6afe5ced5e4469b15269fd0c1390f089c6": oth[(t["to"][:10], t["selector"], t["from"][:10])] += 1
print("non-crowd txs among fetched swaps:", oth.most_common(12))
