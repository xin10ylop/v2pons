"""our relay's swaps since Oct 8 00:00 (cheap getLogs) -> the pools our bot traded live; map to census rows"""
import sys, os, json, pickle
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, logs, PM, T_SWAP, W, sgn
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
head = int(rpc("eth_blockNumber", []), 16)
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, 82878144, head)
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = {json.loads(l)["pid"]: json.loads(l) for l in open("../census.jsonl")}
out = []
for l in ls:
    pid = l["topics"][1]; r = R.get(pid, {})
    out.append({"bn": int(l["blockNumber"], 16), "pid": pid, "tx": l["transactionHash"], "a0": s128(W(l["data"], 0)), "fam": r.get("ours"), "b0": r.get("b0"), "to": r.get("to")})
json.dump({"head": head, "swaps": out}, open("live_relay.json", "w"), indent=1)
print("head", head, "relay swaps", len(out))
for x in out: print(x["bn"], x["pid"][:12], x["a0"] / 1e18, x["fam"], (x["bn"] - x["b0"]) if x["b0"] else None)
