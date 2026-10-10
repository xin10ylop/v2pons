"""Skeptic f2276/100: the collector 0xf341c935 that every traced creator sends its pulled ETH to (selector c76bd193): its code size,
balance, events (last 100k blocks), one forwarding tx in full, and whether it is the app router or emits anything naming it."""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs
HERE = os.path.dirname(os.path.abspath(__file__))
C = "0xf341c935599822f1bc1ec29e27606724fbbf6595"; R = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
code = rpc("eth_getCode", [C, "latest"]); bal = int(rpc("eth_getBalance", [C, "latest"]), 16) / 1e18
print("collector code bytes", (len(code) - 2) // 2, "balance", bal, "nonce", int(rpc("eth_getTransactionCount", [C, "latest"]), 16))
head = int(rpc("eth_blockNumber", []), 16) - 5
lg = logs({"address": C}, head - 300_000, head)
print("collector logs, last 300k blocks:", len(lg), collections.Counter(l["topics"][0] for l in lg).most_common(5))
for l in lg[:3]: print("  ", l["blockNumber"], l["topics"], l["data"][:400])
f3 = json.load(open(os.path.join(HERE, "f3_money.json")))
h = f3[0]["after"][1][4]
t = rpc("eth_getTransactionByHash", [h]); r = rpc("eth_getTransactionReceipt", [h])
inp = t["input"]; print("forward tx", h, "value", int(t["value"], 16) / 1e18, "status", r["status"], "logs", len(r["logs"]))
for i in range((len(inp) - 10) // 64): print("   ", i, inp[10 + 64 * i: 10 + 64 * (i + 1)])
for l in r["logs"]: print("   log", l["address"], l["topics"], l["data"][:300])
# does R's code contain C's address, or C's code contain R's?
rc = rpc("eth_getCode", [R, "latest"])
print("router code mentions collector:", C[2:] in rc.lower(), "| collector code mentions router:", R[2:] in code.lower())
json.dump({"code_bytes": (len(code) - 2) // 2, "balance": bal, "n_logs_300k": len(lg)}, open(os.path.join(HERE, "f4_collector.json"), "w"))
