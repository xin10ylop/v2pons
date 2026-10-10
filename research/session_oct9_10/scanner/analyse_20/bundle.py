"""pool 0x5601033f (family 0x1eef016f): the launch wallet's buy at +95 and the four wallets' buys at +96/+97 carry the SAME deadline
(router 0x65050a9b word 4 = launch ts + 100 s) and minOut 1: one operator's bundle. Where else do these wallets (and the router) appear in
the census (any pool's first-8 swaps or first pulls, any launch)?"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools(); T = load_txs()
TX = json.load(open(os.path.join(HERE, "hookfee_txs.json")))
W5601 = {"0xf343067ad6ed9a1fdca41b6594fbc8372315f0a9", "0x3943af23e503dcf59f8e3c072786fc244bfc272e", "0x28e2d2e263865d0cead2f3086a7e3ba5d26e5a23",
         "0x78e2edc4802e1b23216e333ce4f789b296a5aa3e", "0xa91c9b36ad20914b3317503d80e43713f8851548", "0xc31105e1231a15ce709d85fc4359d63e64c3c512",
         "0x254eff45135ab7e0ffc5a8d4c913f89dd3e6166d", "0x202802a0130876c9bd6df126593c119cb88644fe"}
seen = collections.defaultdict(list)
for h, t in T.items():
    if t["from"] in W5601: seen[t["from"]].append((t["bn"], t["to"], t["selector"], t["value_eth"], t["nonce"]))
for w in W5601: print(w, len(seen[w]), seen[w][:6])
launch_by = collections.Counter(p["launch_from"] for p in P.values() if p["launch_from"] in W5601); print("launches by these wallets", launch_by)
# router 0x65050a9b usage across the census first-8 swaps: how many pools, which families, and the deadline - launch_ts gap
R = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"
use = [t for t in T.values() if t["to"] == R]
print("router 0x65050a9b txs in census", len(use), "value>0", sum(1 for t in use if t["value_wei"]), "selectors", collections.Counter(t["selector"] for t in use).most_common(4),
      "value_eth top", collections.Counter(t["value_eth"] for t in use).most_common(8))
