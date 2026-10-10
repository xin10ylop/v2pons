"""plain ETH transfers of 6 B wallets in every cached block today (cache only, no RPC); counterparty roles from the B loop."""
import json, collections, sys
from libb import *
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from sets import Asys, A, B
import importlib.util
spec = importlib.util.spec_from_file_location("cross_sets", O + "cross.py")
W6 = ["0x4c45af684de8293effd3ed9654e906a7cf81ae0e", "0x6f832efb80edfaac5b71bafbbd8d6e5af09bea3a", "0xf9c0562a734e1a3847b2753a8afc1e34ac8b913f",
      "0x46e6386b84c3fbd07f8b271e42de418205a4102e", "0xc8f7e6941eff578a8aaf1c15a2a51680726e59db", "0x983b53843811d0e7688808457f4110583a6332b7"]
rows = touching(W6, 83900000, 84147499, cached_only=True)
plain = [r for r in rows if r["eth"] > 0 and r["sel"] in ("0x", "")]
print("cached B-wallet txs", len(rows), "plain value", len(plain))
# counterparties and what else they did (fan in / fan out size) in the cache
cps = collections.defaultdict(list)
for r in plain: cps[r["to"] if r["from"] in W6 else r["from"]].append(r)
for cp, rs in sorted(cps.items(), key=lambda kv: kv[1][0]["bn"]):
    allr = touching([cp], rs[0]["bn"] - 60, rs[0]["bn"] + 120, cached_only=True)
    nB_in = len({r["from"] for r in allr if r["to"] == cp and r["from"] in B}); nB_out = len({r["to"] for r in allr if r["from"] == cp and r["to"] in B})
    nA = len({r["from"] for r in allr if r["from"] in A} | {r["to"] for r in allr if r["to"] in A})
    other = [(r["from"][:10], r["to"][:10], round(r["eth"], 4), r["nonce"]) for r in allr if r["from"] not in B and r["to"] not in B]
    d = "W->cp" if rs[0]["from"] in W6 else "cp->W"
    print(rs[0]["utc"], rs[0]["bn"], d, cp, "| W6 txs", len(rs), "%.4f ETH" % sum(r["eth"] for r in rs), "| cp: B in", nB_in, "B out", nB_out, "A", nA, "| other:", other[:3])
