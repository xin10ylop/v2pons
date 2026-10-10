"""Skeptic f2276/100: the recipients the collector's multisend (c76bd193(address[], uint256[])) pays for the 8 traced pulls, and each
recipient's state now (code, balance, nonce); is any of them the app router or a crowd wallet?"""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain import rpc, batch
HERE = os.path.dirname(os.path.abspath(__file__))
f3 = json.load(open(os.path.join(HERE, "f3_money.json")))
hs = [r["after"][1][4] for r in f3 if isinstance(r["after"], list) and len(r["after"]) > 1]
txs = batch([("eth_getTransactionByHash", [h]) for h in hs])
rec = collections.Counter()
for t in txs:
    inp = t["input"]; n = int(inp[10 + 64 * 2: 10 + 64 * 3], 16)
    addrs = ["0x" + inp[10 + 64 * (3 + i) + 24: 10 + 64 * (4 + i)] for i in range(n)]
    amts = [int(inp[10 + 64 * (4 + n + i): 10 + 64 * (5 + n + i)], 16) / 1e18 for i in range(n)]
    print(t["hash"][:12], "value", int(t["value"], 16) / 1e18, list(zip(addrs, amts)))
    for a in addrs: rec[a] += 1
crowd = set(json.load(open(os.path.join(HERE, "a3_flows.json")))["crowd_wallets"])
for a, n in rec.items():
    c = rpc("eth_getCode", [a, "latest"]); b = int(rpc("eth_getBalance", [a, "latest"]), 16) / 1e18; nn = int(rpc("eth_getTransactionCount", [a, "latest"]), 16)
    print("recipient", a, "times", n, "code bytes", (len(c) - 2) // 2, "balance", b, "nonce", nn, "is app router", a == "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6", "is crowd wallet", a in crowd)
json.dump({"recipients": dict(rec)}, open(os.path.join(HERE, "f5_recipients.json"), "w"))
