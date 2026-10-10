"""Where the launch wallets' money comes from and goes: token creator, deployer nonce/balance now, and the deployer's transactions
in the blocks right after its pull (full blocks scanned) for 4 pulled fresh pools; the funding tx in the blocks before the token's creation."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import rpc, batch, logs
D = os.path.join(HERE, "fresh"); fr = json.load(open(os.path.join(D, "fresh.json"))); TX = json.load(open(os.path.join(D, "txs.json")))
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
fam = fr["fam"]
deps = [c["from"] for c in fam]
res = batch([("eth_getTransactionCount", [d, "latest"]) for d in deps] + [("eth_getBalance", [d, "latest"]) for d in deps])
n = len(deps)
print("deployer nonce now", collections.Counter(int(res[i], 16) for i in range(n)), "balance now ETH", sorted(round(int(res[n + i], 16) / 1e18, 5) for i in range(n))[-6:])
# pulls of fresh pools
pulls = {}
for e in fr["events"]:
    if e["topics"][0] != T_TRANSFER and int(e["data"][2 + 128: 2 + 192], 16) >= (1 << 255):
        pulls.setdefault(e["topics"][1], (int(e["blockNumber"], 16), e["transactionHash"]))
out = {"sweeps": [], "funding": []}
cache = os.path.join(D, "blocks.json"); BK = json.load(open(cache)) if os.path.exists(cache) else {}
def blocks(a, b):
    need = [x for x in range(a, b + 1) if str(x) not in BK]
    for i in range(0, len(need), 50):
        r = batch([("eth_getBlockByNumber", [hex(x), True]) for x in need[i:i + 50]])
        for x, blk in zip(need[i:i + 50], r):
            BK[str(x)] = [{"h": t["hash"], "from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "sel": t["input"][2:10], "nonce": int(t["nonce"], 16)} for t in blk["transactions"]]
    json.dump(BK, open(cache, "w"))
    return [(x, t) for x in range(a, b + 1) for t in BK[str(x)]]
for c in fam[:6]:
    if c["pid"] not in pulls: continue
    pb, ph = pulls[c["pid"]]
    tx = [(x, t) for x, t in blocks(pb, pb + 40) if t["from"] == c["from"] or t["to"] == c["from"]]
    print("pool", c["pid"][:12], "dep", c["from"][:10], "pull block", pb, "dep txs after pull:", [(x - pb, t["to"][:10], round(t["value"] / 1e18, 5), t["sel"], t["nonce"]) for x, t in tx])
    out["sweeps"].append({"pid": c["pid"], "dep": c["from"], "after_pull": [(x - pb, t["to"], t["value"] / 1e18, t["sel"], t["nonce"]) for x, t in tx]})
# token creation and funding for 4 deployers
for c in fam[:4]:
    lg = logs({"address": c["token"], "topics": [T_TRANSFER, "0x" + "0" * 64]}, c["bn"] - 20000, c["bn"])
    if not lg: print("no mint log for", c["token"]); continue
    cb = int(lg[0]["blockNumber"], 16); ct = rpc("eth_getTransactionByHash", [lg[0]["transactionHash"]])
    print("token", c["token"][:10], "minted at init-", c["bn"] - cb, "by tx from", ct["from"].lower()[:10], "(dep", c["from"][:10], ") nonce", int(ct["nonce"], 16), "to", (ct["to"] or "create"))
    tx = [(x, t) for x, t in blocks(cb - 150, cb) if t["to"] == c["from"]]
    print("   funding txs to the deployer in the 150 blocks before:", [(x - cb, t["from"], round(t["value"] / 1e18, 5), t["sel"], t["nonce"]) for x, t in tx])
    out["funding"].append({"dep": c["from"], "token_mint_block": cb, "mint_from": ct["from"].lower(), "funding": [(x - cb, t["from"], t["value"] / 1e18, t["sel"]) for x, t in tx]})
json.dump(out, open(os.path.join(HERE, "money.json"), "w"), indent=1)
