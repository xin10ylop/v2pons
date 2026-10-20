"""One row per Initialize (s01 + s02): block, time, sender, to, selector, value, calldata length, currencies, fee, tick spacing, hooks, sqrtPriceX96,
the minted liquidity and range (the receipt's ModifyLiquidity on that pool), the mint's NFT recipient. Writes s03_launches_cache.jsonl."""
import json, bisect
from common import PM, POSM, T_ML, T_TRANSFER, W, sgn, p, load_jsonl
inits = load_jsonl("s01_inits_cache.jsonl")
txs = {r["h"]: r for r in load_jsonl("s02_tx_cache.jsonl")}
bl = sorted((r["b"], r["t"]) for r in load_jsonl("s01_blocks_cache.jsonl")); bb = [b for b, _ in bl]
def t_of(b):
    i = bisect.bisect_left(bb, b)
    if i < len(bb) and bb[i] == b: return bl[i][1]
    if i == 0: return bl[0][1]
    if i >= len(bb): return bl[-1][1]
    (b0, t0), (b1, t1) = bl[i - 1], bl[i]
    return t0 + (t1 - t0) * (b - b0) / (b1 - b0)
rows = []; miss = 0
for l in inits:
    tx = txs.get(l["transactionHash"])
    if not tx: miss += 1; continue
    d = l["data"]; pid = l["topics"][1]
    ml = [x for x in tx["logs"] if x["a"] == PM and x["t"][0] == T_ML and x["t"][1] == pid]
    mints = [(sgn(W(x["d"], 0)), sgn(W(x["d"], 1)), sgn(W(x["d"], 2)), "0x" + x["t"][2][-40:]) for x in ml]
    nft = [x for x in tx["logs"] if x["a"] == POSM and x["t"][0] == T_TRANSFER and len(x["t"]) == 4 and int(x["t"][1], 16) == 0]
    b = int(l["blockNumber"], 16)
    rows.append({"b": b, "t": round(t_of(b), 1), "li": int(l["logIndex"], 16), "h": l["transactionHash"], "pid": pid,
                 "from": tx["from"], "to": tx["to"], "sel": tx["input"][:10], "value": str(tx["value"]), "clen": (len(tx["input"]) - 2) // 2,
                 "nonce": tx["nonce"], "status": tx["status"], "gas": tx["gas"], "gp": tx["gp"], "idx": tx["idx"],
                 "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:], "fee": W(d, 0), "ts": sgn(W(d, 1)), "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3],
                 "sqrtp": str(W(d, 3)), "tick": sgn(W(d, 4)),
                 "mints": [[a, c, str(e), s] for a, c, e, s in mints], "liq": str(sum(e for _, _, e, _ in mints if e > 0)),
                 "lo": min((a for a, _, e, _ in mints if e > 0), default=None), "hi": max((c for _, c, e, _ in mints if e > 0), default=None),
                 "nft_to": ["0x" + x["t"][2][-40:] for x in nft], "nlogs": len(tx["logs"])})
rows.sort(key=lambda r: (r["b"], r["li"]))
open(p("s03_launches_cache.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))
print(len(rows), "launches;", miss, "without tx")
