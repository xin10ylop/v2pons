"""The launch wallets' own transactions: 346 of 349 launch at deploy nonce + 2 (deploy the token, approve the PositionManager, launch); the 3
with one more transaction between could hide a reverted launch (the feed shows a reverted transaction; the engine would fire on it and its
buy would revert NoPool). For those 3, and for 5 ordinary ones: the token's deploy block (its mint Transfer from 0x0), the blocks to the
launch, and every transaction the wallet sent in between (full blocks, filtered by sender) with its receipt. Writes s10_launch_gaps.out."""
from common import *
import rpc
L = json.load(open(J("s01_launches.json")))["launches"]
odd = [x for x in L if x["deployed_by_launcher_nonce"] is not None and x["nonce"] - x["deployed_by_launcher_nonce"] != 2]
norm = [x for x in L if x["deployed_by_launcher_nonce"] is not None and x["nonce"] - x["deployed_by_launcher_nonce"] == 2][-5:]
gaps = []
for x in odd + norm:
    tr = rpc.call("eth_getLogs", [{"address": x["token"], "topics": [T_TR, "0x" + word(0)], "fromBlock": hex(x["lb"] - 30000), "toBlock": hex(x["lb"])}])
    if not tr: print(x["token"], "no mint Transfer within 30,000 blocks before the launch"); continue
    db = int(tr[0]["blockNumber"], 16); gaps.append(x["lb"] - db)
    mine = []
    if x in odd:
        for a in range(db, x["lb"] + 1, 20):
            for b in rpc.batch("eth_getBlockByNumber", [[hex(k), True] for k in range(a, min(a + 20, x["lb"] + 1))]):
                mine += [t for t in b["transactions"] if t["from"].lower() == x["from"]]
        recs = rpc.batch("eth_getTransactionReceipt", [[t["hash"]] for t in mine])
        desc = [(int(t["nonce"], 16), int(t["blockNumber"], 16) - db, (t["to"] or "create")[:10], t["input"][:10], (len(t["input"]) - 2) // 2, int(r["status"], 16)) for t, r in zip(mine, recs)]
    print(f"{'ODD ' if x in odd else 'norm'} {x['from']} token {x['token'][:12]} deploy block {db} -> launch {x['lb']} (+{x['lb'] - db} blocks, {(x['lb'] - db) / 9.7:.1f} s)"
          + (f"; its txs (nonce, + blocks, to, selector, bytes, status): {desc}" if x in odd else ""))
print(f"deploy -> launch blocks: {sorted(gaps)}")
print(rpc.STATS)
