"""The crowd's buy calls as the feed shows them (value 0): the amount word, the min-out word, the path (WETH, fee 100, token) and the
recipient, checked against the pool's Swap event for every real buy fetched in w05 (8 h) and w03 (census picks)."""
import json, sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3dec import WETH
D = json.load(open("w05_recent_8h.json"))
LAYOUT = {("3593564c", 484): 9, ("a0193551", 452): 8, ("49f74a5d", 452): 8}       # word of amountIn (arguments after the selector)
def parse(inp):
    b = bytes.fromhex(inp[2:]); sel = b[:4].hex(); k = (sel, len(b))
    if k not in LAYOUT: return None
    aw = LAYOUT[k]; W = lambda i: int.from_bytes(b[4 + 32 * i: 4 + 32 * (i + 1)], "big")
    path = b[4 + 32 * (aw + 4): 4 + 32 * (aw + 4) + 43]
    return {"amount": W(aw), "min_out": W(aw + 1), "recipient": "0x" + b[4 + 32 * (aw - 1) + 12: 4 + 32 * aw].hex(), "path_len": W(aw + 3),
            "tin": path[:20].hex(), "fee": int.from_bytes(path[20:23], "big"), "tout": path[23:43].hex()}
stats = Counter(); ex = []
swap_amt = {}
for x in D["line"]:
    qs = 0 if x["token0"] == "0x" + WETH else 1; tok = (x["token1"] if qs == 0 else x["token0"])[2:]
    for l in x["logs"]:
        if l["topics"][0][2:10] != "c42079f9": continue
        d = l["data"]; a = int(d[2 + 64 * qs: 2 + 64 * (qs + 1)], 16); a = a - (1 << 256) if a >> 255 else a
        swap_amt[l["transactionHash"]] = (a, tok, "0x" + l["topics"][2][-40:])
for h, t in D["buy_txs"].items():
    if not t: continue
    p = parse(t["input"]); stats["fetched"] += 1
    if p is None: stats["other shape " + t["input"][:10] + "/" + str((len(t["input"]) - 2) // 2)] += 1; continue
    stats["crowd shape"] += 1; a, tok, rcpt = swap_amt.get(h, (None, None, None))
    stats[f"value {'0' if int(t['value'], 16) == 0 else '>0'}"] += 1
    stats["amount == swap WETH in" if a == p["amount"] else "amount != swap"] += 1
    stats[f"min_out {'0' if p['min_out'] == 0 else '>0'}"] += 1
    stats["path WETH->token, fee 100" if (p["tin"], p["fee"], p["tout"]) == (WETH, 100, tok) else "path other"] += 1
    stats["recipient = tx sender" if p["recipient"] == t["from"].lower() else "recipient other"] += 1
    stats[f"gas limit {int(t['gas'], 16)}"] += 1; stats[f"prio {'= gasPrice' if t.get('maxPriorityFeePerGas') == t.get('maxFeePerGas') else 'other'}"] += 1
    if len(ex) < 1: ex.append((h, t["to"], p))
for k, v in sorted(stats.items(), key=lambda kv: -kv[1]): print(f"  {v:>4}  {k}")
print("example", ex)
mm = []
for h, t in D["buy_txs"].items():
    if not t: continue
    p = parse(t["input"])
    if p is None: continue
    a, tok, rcpt = swap_amt.get(h, (None, None, None))
    if a != p["amount"]: mm.append((h[:12], t["to"][:10], t["input"][:10], p["amount"], a, None if a is None else round(a / p["amount"], 6)))
print("mismatches (tx, to, sel, calldata amount, swap WETH in, ratio):", len(mm)); [print("  ", m) for m in mm[:8]]
from collections import Counter as Cn
print(Cn((m[1], m[2], m[5]) for m in mm).most_common(8))
