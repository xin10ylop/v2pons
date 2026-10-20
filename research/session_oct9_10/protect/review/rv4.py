"""Chain re-check: (a) the 16:13 copy-pool outsider buy -> pull lag; (b) the fingerprint of today's trigger txs, read raw from the chain."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
from chain import rpc, logs, PM
pools, head = load_all(); cw = annotate(pools)
P = {p["pid"][:10]: p for p in pools}
p = P["0x75d98983"]
ev = logs({"address": PM, "topics": [T_SWAP, p["pid"]]}, p["b0"], p["b0"] + 1500) + logs({"address": PM, "topics": [T_ML, p["pid"]]}, p["b0"], p["b0"] + 1500)
pull = min((int(l["blockNumber"], 16), int(l["transactionIndex"], 16)) for l in ev if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
tx = rpc("eth_getTransactionByHash", ["0x" + "0" * 0 + next(x["tx"] for x in p["sw"] if (x["from"] or "").startswith("0x6d5a7ef9")).replace("0x", "")]) if False else None
ob = [x for x in p["sw"] if (x["from"] or "").startswith("0x6d5a7ef9")]
print("copy 0x75d98983 launch", p["b0"], "outsider buy blocks", [(x["bn"], x["bn"] - p["b0"], -x["a0"] / 1e18) for x in ob], "pull", pull, "lag", pull[0] - ob[0]["bn"])
swaps_near = [(int(l["blockNumber"], 16) - ob[0]["bn"], l["topics"][2][-40:][:8]) for l in ev if l["topics"][0] == T_SWAP and abs(int(l["blockNumber"], 16) - ob[0]["bn"]) <= 30]
print("swaps within 30 blocks of it (rel block, sender):", swaps_near)
# (b) trigger fingerprints straight from the chain for today's live trades
for pid in ("0x2a928e99", "0x2749b5d1", "0x43c1ce10", "0x12c952fa"):
    q = P[pid]; t = next(x for x in q["sw"] if x["a0"] <= -REAL and 6 <= x["bn"] - q["b0"] <= 150 and x["cls"] != "us")
    r = rpc("eth_getTransactionByHash", [t["tx"]])
    inp = r["input"]
    print(pid, "type", int(r["type"], 16), "prio", int(r.get("maxPriorityFeePerGas", "0x0"), 16), "gas", int(r["gas"], 16), "len", len(inp) // 2 - 1, "to", r["to"],
          "sel", inp[:10], "deadline_max", inp[2 + 8 + 64 * 2: 2 + 8 + 64 * 3] == "f" * 64, "nonce", int(r["nonce"], 16), "from", r["from"][:10], "value", int(r["value"], 16) / 1e18)
