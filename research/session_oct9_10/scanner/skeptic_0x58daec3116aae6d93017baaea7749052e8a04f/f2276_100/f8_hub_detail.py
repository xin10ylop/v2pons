"""Skeptic f2276/100: the hub's router calls and its multisend recipients (the full calldata of the hub's txs re-read): are they the app's
crowd wallets (gas top-ups) or launchers?"""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import load_pools, load_txs
HUB = "0xbae538011874261e3fb4ca6aa03cacb2766c4d81"; ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
C = json.load(open(os.path.join(D, "hub_blocks.json")))
hs = [(int(b), t[4]) for b in C for t in C[b] if t[0] == HUB]
txs = batch([("eth_getTransactionByHash", [h]) for _, h in sorted(hs)])
P = load_pools(); launchers = set(p["launch_from"] for p in P.values() if p["family"].endswith("|2276|100|1|true"))
T = load_txs(); crowd_all = set(t["from"] for t in T.values() if t["to"] == ROUTER)
crowd_s = set(json.load(open(os.path.join(HERE, "a3_flows.json")))["crowd_wallets"]); crowd_all |= crowd_s
TX = {}
for line in open(os.path.join(D, "txs.jsonl")):
    t = json.loads(line)
    if t["to"] == ROUTER: crowd_all.add(t["from"])
print("known crowd wallets (census first-8 + sample)", len(crowd_all), "launchers", len(launchers))
for (b, h), t in zip(sorted(hs), txs):
    inp = t["input"]; v = int(t["value"], 16) / 1e18
    if t["to"] == ROUTER:
        print("block", b, "hub -> ROUTER value", v, "input", inp[:10], [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)])
        continue
    n = int(inp[10 + 64 * 2: 10 + 64 * 3], 16)
    addrs = ["0x" + inp[10 + 64 * (3 + i) + 24: 10 + 64 * (4 + i)] for i in range(n)]
    amts = [int(inp[10 + 64 * (4 + n + i): 10 + 64 * (5 + n + i)], 16) / 1e18 for i in range(n)]
    c = sum(1 for a in addrs if a in crowd_all); l = sum(1 for a in addrs if a in launchers)
    print("block", b, "hub multisend value", round(v, 5), "recipients", n, "crowd wallets", c, "launchers", l, "amount each q", sorted(amts)[::max(1, n // 5)][:6])
