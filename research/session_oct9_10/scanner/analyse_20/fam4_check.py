"""family 0x2cf3de56|aad1232c: its one swap (launch wallet, +2501, 0.00099 ETH via 0x05ac4ff6 / 440aeb19): calldata words, receipt
(hook cut: trader tokens vs the Swap's a1), and the launch tx's calldata words (what the 1,252-byte aad1232c call carries)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common20 import *
from chain import batch
P = load_pools(); T = load_txs(); F = load_families()
K = json.load(open(os.path.join(HERE, "keys.json")))
pids = F[K[3]]["pids"]; E = load_events(set(pids))
CACHE = os.path.join(HERE, "fam4_rcpts.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
sw = [(pid, s) for pid in pids for s in (E.get(pid) or {}).get("swaps", [])]
want = [s["tx"] for pid, s in sw] + [P[pids[1]]["launch_tx"]]
miss = [h for h in want if h not in R]
if miss: R.update(zip(miss, batch([("eth_getTransactionReceipt", [h]) for h in miss]))); json.dump(R, open(CACHE, "w"))
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
for pid, s in sw:
    t = T[s["tx"]]; p = P[pid]; r = R[s["tx"]]
    inp = t.get("input") or t["input512"]
    print("swap", pid[:12], "+%d" % (s["bn"] - p["launch_block"]), "a0", s["a0"], "a1", s["a1"], "fee", s["fee"], "value", t["value_wei"], "to", t["to"], "sel", t["selector"], "clen", t["calldata_len"])
    for i in range((len(inp) - 10) // 64): print("   w%d" % i, inp[10 + 64 * i: 74 + 64 * i])
    trs = [("0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:], int(l["data"], 16)) for l in r["logs"] if l["topics"] and l["topics"][0] == TRANSFER and l["address"].lower() == p["token"]]
    print("   token transfers", trs, "trader got / a1", sum(v for a, b, v in trs if b == t["from"]) / s["a1"])
    print("   logs", [(l["address"][:10], l["topics"][0][:10]) for l in r["logs"]])
    sp, L = Pool(p, E[pid], T, M := load_blocks_meta()).launch_state()
    print("   launch-state quote for a0:", v4math.buy_out_int(int(sp), L, -s["a0"], s["fee"]), "a1", s["a1"])
lt = T[P[pids[1]]["launch_tx"]]; inp = lt.get("input") or lt["input512"]
print("launch tx", lt["hash"], "value", lt["value_wei"])
for i in range((len(inp) - 10) // 64): print("   w%d" % i, inp[10 + 64 * i: 74 + 64 * i])
