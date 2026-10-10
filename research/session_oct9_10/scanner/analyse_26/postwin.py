"""F4b (and F4a for the pull timing): ModifyLiquidity logs after the census window (launch + 3000 .. head) for each pool, and F4b Swap logs in
launch+3000..launch+12000 to look for sells through routers other than the crowd's (can an outsider sell?). Cached in cache/postwin.json"""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from load import *
OUT = "cache/postwin.json"
C = json.load(open(OUT)) if os.path.exists(OUT) else {}
P = load_pools()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
F4 = [p for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1]
head = int(rpc("eth_blockNumber", []), 16)
if "ml" not in C:
    pids = [p["pid"] for p in F4]; lo = min(p["launch_block"] for p in F4) + 3000; res = []
    for i in range(0, len(pids), 20):
        res += logs({"address": PM, "topics": [T_ML, pids[i:i + 20]]}, lo, head)
    C["ml"] = [{"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "dl": sgn(W(l["data"], 2)), "sender": "0x" + l["topics"][2][-40:], "tx": l["transactionHash"]} for l in res]
    C["head"] = head
if "f4b_swaps" not in C:
    res = []
    for p in F4:
        if p["hooks_zero"]: continue
        res += logs({"address": PM, "topics": [T_SWAP, p["pid"]]}, p["launch_block"] + 3001, min(head, p["launch_block"] + 12000))
    C["f4b_swaps"] = [{"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "sender": "0x" + l["topics"][2][-40:], "a0": sgn(W(l["data"], 0)) if W(l["data"], 0) < (1 << 255) else sgn(W(l["data"], 0)), "tx": l["transactionHash"]} for l in res]
json.dump(C, open(OUT, "w"))
print("head", C["head"], "ml logs", len(C["ml"]), "f4b swaps", len(C["f4b_swaps"]))
