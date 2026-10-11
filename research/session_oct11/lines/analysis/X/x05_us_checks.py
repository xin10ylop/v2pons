"""Question 3, direct checks on our two addresses, Oct 10 00:00 UTC .. head:
(a) every ERC-20 Transfer log to or from our wallet or relay; anything not from/to the PoolManager is someone else's transfer to us;
(b) every transaction in the line pools' records (swaps to launch + 400, all liquidity calls) whose calldata carries our wallet or relay
    and that we did not send (x02 already flags swaps: mentions_us);
(c) a systematic sample of our trades (every 10th): every transaction in the blocks from our buy's block - 1 to our sell's block + 3
    (reverted ones included), looking for any transaction to our addresses or carrying them that we did not send, and listing the order of
    our buy against the other buyers of that pool's token in those blocks. -> x05_us_checks.json"""
import json, pickle, collections
from rpc import call, batch, logs, STATS
from xcommon import *
meta = json.load(open("x01_meta.json")); start, head = meta["start"], meta["head"]
res = {}
tl = []
for who in (OURS, RELAY):
    for pos in (1, 2):
        topics = [T_TRANSFER, None, None]; topics[pos] = pad(who)
        for a in range(start, head + 1, 100000):
            for x in logs({"topics": topics}, a, min(a + 99999, head)):
                tl.append({"who": who, "dir": "from" if pos == 1 else "to", "token": x["address"].lower(), "from": "0x" + x["topics"][1][-40:], "to": "0x" + x["topics"][2][-40:],
                           "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"], "amt": int(x["data"], 16) if x["data"] not in ("0x", "") else 0})
c = collections.Counter((t["who"][:10], t["dir"], "PM" if PM in (t["from"], t["to"]) else "other") for t in tl)
print("Transfer logs touching our addresses:", dict(c))
odd = [t for t in tl if PM not in (t["from"], t["to"])]
print("  not via the PoolManager:", len(odd))
for t in odd[:30]: print("   ", t)
res["transfers_counts"] = {str(k): v for k, v in c.items()}; res["transfers_odd"] = odd
D = pickle.load(open("x02_pools.pkl", "rb"))
men = [(p["pid"], s["off"], s["eoa"], s["to"], s["sel"], s["who"]) for p in D["pools"] for s in p["sw"] if s.get("mentions_us") and s["who"] != "ours"]
print("pool swaps by others whose calldata carries our wallet or relay:", len(men), men[:10])
res["swaps_mentioning_us"] = men
tx = {}
for l in open("txcache.jsonl"):
    x = json.loads(l); tx[x["hash"]] = x
mlm = [(p["pid"], m["off"], m["eoa"], m["to"], m["sel"]) for p in D["pools"] for m in p["ml"] if (OURS[2:] in ((tx.get(m["tx"]) or {}).get("input") or "").lower() or RELAY[2:] in ((tx.get(m["tx"]) or {}).get("input") or "").lower())]
print("liquidity calls whose calldata carries our wallet or relay:", len(mlm), mlm[:10])
res["ml_mentioning_us"] = mlm
trades = [t for t in json.load(open("x02_trades.json")) if t["line"] != "other" and t["buy_bn"] and t["sell_bn"]]
samp = trades[::10]
P = {p["pid"]: p for p in D["pools"]}
found, order = [], []
for t in samp:
    p = P[t["pid"]]; tokhex = p["token"][2:].lower()
    bl = list(range(t["buy_bn"] - 1, t["sell_bn"] + 4))
    blks = batch("eth_getBlockByNumber", [[hex(b), True] for b in bl], 10)
    seq = []
    for b, blk in zip(bl, blks):
        for x in (blk or {}).get("transactions", []):
            frm = x["from"].lower(); to = (x.get("to") or "").lower(); inp = (x.get("input") or "").lower()
            if frm != OURS and (to in (OURS, RELAY) or OURS[2:] in inp or RELAY[2:] in inp):
                found.append({"pid": t["pid"], "bn": b, "from": frm, "to": to, "sel": inp[:10], "hash": x["hash"]})
            if tokhex in inp or frm == OURS:
                seq.append((b - p["lb"], int(x["transactionIndex"], 16), "US" if frm == OURS else frm[:10], to[:10], inp[2:10], int(x["value"], 16) / 1e18, int(x["nonce"], 16)))
    order.append({"pid": t["pid"], "ts": p["ts"], "seq": seq})
print(f"sampled trades {len(samp)}; blocks read {sum(t['sell_bn'] - t['buy_bn'] + 5 for t in samp)}; transactions by others to or carrying our addresses: {len(found)}")
for f in found[:20]: print("   ", f)
res["sample_found"] = found; res["sample_order"] = order
json.dump(res, open("x05_us_checks.json", "w"), indent=0)
print("posts", STATS)
