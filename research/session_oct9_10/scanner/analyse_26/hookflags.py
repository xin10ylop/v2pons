import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
NAMES = ["afterRemoveLiqRetDelta", "afterAddLiqRetDelta", "afterSwapRetDelta", "beforeSwapRetDelta", "afterDonate", "beforeDonate", "afterSwap", "beforeSwap",
         "afterRemoveLiq", "beforeRemoveLiq", "afterAddLiq", "beforeAddLiq", "afterInit", "beforeInit"]
def flags(h):
    v = int(h, 16) & 0x3fff
    return [NAMES[i] for i in range(14) if v >> i & 1]
F4 = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and not p["hooks_zero"]]
c = collections.Counter((p["fee"], p["tick_spacing"], tuple(flags(p["hooks"]))) for p in F4)
for k, n in c.most_common(): print(n, k)
# does the chain-wide dust bot buy in hooked pools elsewhere in the census?
E = load_events(set(p["pid"] for p in P.values() if not p["hooks_zero"]))
T = load_txs()
hz = collections.Counter()
for p in P.values():
    if p["hooks_zero"]: continue
    e = E.get(p["pid"])
    if not e: continue
    dust = any((T.get(s["tx"]) or {}).get("from") == "0xe71a69f434a719cd5afa411568b69716aab3b84a" for s in e["swaps"][:8])
    hz[(tuple(flags(p["hooks"])), dust, bool(e["swaps"]))] += 1
for k, n in sorted(hz.items(), key=lambda x: -x[1])[:20]: print(n, k)
