"""sanity-check the Camelot factories: are they live (allPairsLength / recent logs anywhere)?"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384
camV2 = "0x6eccab422d763ac031210895c81787e87b43a652"; camV3 = "0x1a3c9b1d2f0529d97f2afc5136cc23e58f1fd35b"
# camelot V2 allPairsLength() 0x574f2ba3
for lbl, a, sel in [("camV2 allPairsLength", camV2, "0x574f2ba3")]:
    r = rpc(U, "eth_call", [{"to": a, "data": sel}, "latest"]); v = int(r["result"],16) if isinstance(r.get("result"),str) else r; print(lbl, v)
# any logs at all on these addresses in the last 50k blocks (any event)
for lbl, a in [("camV2", camV2), ("camV3", camV3)]:
    r = rpc(U, "eth_getLogs", [{"address": a, "fromBlock": hex(HEAD-50000), "toBlock": hex(HEAD)}])
    n = len(r.get("result",[])) if isinstance(r,dict) else 0
    tc = collections.Counter(l["topics"][0][:10] for l in r.get("result",[])) if n else {}
    print(lbl, "logs in 50k blocks:", n, dict(tc))
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
