"""every pool creation over 7 days on the v4 PoolManager and the five V2/V3 factories (arb1, address-filtered, 250k-block chunks)"""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384; B7 = 511699412; B24 = 513600845
PM = "0x360e68faccca8ca495c1b759fd9eee466db9fb32"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
SRC = {"v4": (PM, [T_INIT]), "uniV2": ("0xf1d7cc64fb4452f05c498126312ebe29f30fbcf9", None), "uniV3": ("0x1f98431c8ad98523631ae4a59f267346ea31f984", None),
       "camelotV2": ("0x6eccab422d763ac031210895c81787e87b43a652", None), "camelotV3": ("0x1a3c9b1d2f0529d97f2afc5136cc23e58f1fd35b", None),
       "sushiV2": ("0xc35dadb65012ec5796536bd9864ed8773abc74c4", None), "sushiV3": ("0x1af415a1eba07a4986a52b6f2e7de7003d82231e", None)}
out = {}
for k, (a, tp) in SRC.items():
    rows = []; x = B7
    while x <= HEAD:
        y = min(HEAD, x + 249_999); flt = {"address": a, "fromBlock": hex(x), "toBlock": hex(y)}
        if tp: flt["topics"] = tp
        r = rpc(U, "eth_getLogs", [flt])
        if "result" not in r: raise SystemExit(f"{k} {x}-{y} {r}")
        rows += [{"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "topics": l["topics"], "data": l["data"], "addr": l["address"].lower()} for l in r["result"]]
        x = y + 1
    out[k] = rows; print(k, "logs 7d", len(rows), "in last 24h", sum(1 for r in rows if r["bn"] >= B24))
json.dump({"head": HEAD, "b7": B7, "b24": B24, "logs": out}, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/cache/launch_logs_7d.json", "w"))
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
