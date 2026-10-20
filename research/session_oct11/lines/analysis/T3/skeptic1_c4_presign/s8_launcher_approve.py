"""Stage 8: in the oldest slice the pool's launcher calls approve (095ea7b3) on the PositionManager at T-4 in most pools (s5_generic_oldest).
Where is that approve relative to L and T in each slice? ERC-721 Approval logs of the PositionManager with owner = the launcher, L..L+120.
usage: s8_launcher_approve.py <slice>"""
import sys, pickle, collections
from lib import *
name = sys.argv[1]; D = pickle.load(open(f"parsed_{name}.pkl", "rb")); P = sorted([p for p in D["pools"]], key=lambda p: p["L"])
T_APPROVAL = "0x" + keccak(text="Approval(address,address,uint256)").hex()
kv = KV(f"appr_{name}")
for i in range(0, len(P), 25):
    g = P[i:i + 25]; key = f"{g[0]['L']}-{g[-1]['L']}"
    if key in kv.d: continue
    tops = ["0x" + "0" * 24 + p["launcher"][2:] for p in g]
    kv.put(key, logs({"address": POSM, "topics": [T_APPROVAL, tops]}, g[0]["L"], g[-1]["L"] + 120)); kv.flush()
allg = [l for v in kv.d.values() for l in v]
by = collections.defaultdict(list)
for l in allg: by["0x" + l["topics"][1][-40:]].append(l)
offL, offT, lead = collections.Counter(), collections.Counter(), []
none = 0
for p in P:
    ls = [l for l in by.get(p["launcher"], []) if p["L"] <= int(l["blockNumber"], 16) <= p["L"] + 120]
    if not ls: none += 1; continue
    b = int(ls[0]["blockNumber"], 16); offL[b - p["L"]] += 1
    if p["T"] is not None: offT[p["Tbn"] - b] += 1; lead.append(p["Tbn"] - b)
    p["appr"] = b - p["L"]; p["approved"] = "0x" + ls[0]["topics"][2][-40:]
print(f"{name}: pools {len(P)}; launcher approve on the PositionManager found in {len(P) - none} (none in {none})")
print("   approve - L (blocks):", sorted(offL.items()))
print("   T - approve (blocks):", sorted(offT.items()))
if lead: print(f"   T - approve p10/50/90 {pct(lead,.1)}/{pct(lead,.5)}/{pct(lead,.9)}; within 1..4: {sum(1 for x in lead if 1 <= x <= 4)} of {len(lead)}; "
              f"approved spender: {collections.Counter(p.get('approved','')[:10] for p in P if p.get('approved')).most_common(3)}")
