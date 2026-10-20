import sys, json, statistics as st, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); BM = load_blocks_meta()
bf = [v[1] for v in BM.values()]
print("basefee p10/50/90", sorted(bf)[len(bf)//10], st.median(bf), sorted(bf)[9*len(bf)//10])
v = [p for p in P.values() if p["known"] == "vbot-v2.433"]; a = [p for p in P.values() if p["known"] == "operator-A"]
print(len(v), len(a))
E = load_events(set(p["pid"] for p in v[:400] + v[-400:]))
cnt = collections.Counter()
for pid, e in E.items():
    for s in e["swaps"]: cnt[s["sender"]] += 1
print(cnt.most_common(10))
T = load_txs()
c2 = collections.Counter((t["to"], t["selector"]) for t in T.values() if "swap" in t.get("kind", []))
print(c2.most_common(20))
print(collections.Counter(p["fee"] for p in a).most_common(), collections.Counter(p["launch_to"] for p in a).most_common(5))
