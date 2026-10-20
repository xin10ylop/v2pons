"""Task 4: the decoys on the 2.4333 line in the last 3 h: wallets, sizes, offsets, ETH ahead of the bot per pool (p50/p90), whether a 0.002 ETH
front at the head of L+2 would still let the bot's buy fill (its calldata minOut, v4math replay), the decoy wallets' nonce and their funding
(one hop: the transaction that sent them ETH, scanning back <= 2,000 blocks from their buy, sampled)."""
import pickle, collections, json, sys
from common import *
from rpc import batch
import v4math
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]; head_ts = D["head_ts"]
G = [p for p in P if p["line"] == "2.433" and p["ts"] >= head_ts - 3 * 3600]
print(f"2.433 launches in the last 3 h: {len(G)} ({utc(min(p['ts'] for p in G))} .. {utc(max(p['ts'] for p in G))}), ours in {sum(1 for p in G if p['ours'])}, with a bot buy {sum(1 for p in G if p['T'] is not None)}")
ahead_rows = []; wal = collections.defaultdict(list)
for p in sorted(G, key=lambda p: p["lb"]):
    T = p["T"]; ib = next((i for i, s in enumerate(p["sw"]) if s["who"] == "bot"), len(p["sw"]))
    ah = [s for s in p["sw"][:ib] if s["buy"] and s["who"] != "ours"]
    for s in ah: wal[s["eoa"]].append((p["pid"], s["off"], s["q"] / 1e18, s["to"], s["nonce"], s["bn"], s["tx"]))
    ahead_rows.append((p, ah, sum(s["q"] for s in ah) / 1e18))
    print(f"  {utc(p['ts'])} fee {p['fee']} ours {int(p['ours'])} T {T} ahead {sum(s['q'] for s in ah)/1e18:.5f}: " + ", ".join(f"+{s['off']} {s['q']/1e18:.5f} {s['eoa'][:10]}(n{s['nonce']}) via {s['to'][:10]}" for s in ah) + f" | pull {p['pull']}")
for sub, rows in (("all", ahead_rows), ("untouched", [r for r in ahead_rows if not r[0]["ours"]]),
                  ("from 16:28", [r for r in ahead_rows if r[0]["ts"] >= DECOY_FILL]), ("untouched from 16:28", [r for r in ahead_rows if r[0]["ts"] >= DECOY_FILL and not r[0]["ours"]])):
    v = [r[2] for r in rows]
    if v: print(f"ETH ahead of the bot per pool ({sub}, n {len(v)}): p50 {pct(v,.5):.5f} p90 {pct(v,.9):.5f} max {max(v):.5f}")
print("\nwallets buying ahead of the bot (last 3 h): wallet, pools, offsets, sizes, via, nonce at the buy")
for w, v in sorted(wal.items(), key=lambda kv: -len(kv[1])):
    print(f"  {w} pools {len(set(x[0] for x in v))} offs {collections.Counter(x[1] for x in v).most_common(4)} sizes {collections.Counter(round(x[2],6) for x in v).most_common(3)} via {collections.Counter(x[3][:10] for x in v).most_common(2)} nonce {sorted(set(x[4] for x in v))[:6]}")
# would a 0.002 ETH front at the head of L+2 pass the bot's minOut? (untouched pools with a bot buy carrying minOut)
print("\nthe bot's first buy: fill = output / minOut, as it happened and with an extra q ETH bought at the head of L+2")
for q in (0.0, 0.002, 0.0024, 0.0058):
    fills = []
    for p, ah, tot in ahead_rows:
        if p["ours"] or p["T"] is None: continue
        bot = next(s for s in p["sw"] if s["who"] == "bot")
        if not bot["minout"]: continue
        sp, L = p["sp0"], p["L0"]; B = 2
        done = False
        for s in p["sw"]:
            if not done and s["off"] >= B and q > 0:
                sp = buy_state(sp, L, int(q * 1e18), p["fee"]); done = True
            if s is bot: break
            if s["L"] > 0: L = s["L"]
            sp = buy_state(sp, L, s["q"], p["fee"]) if s["buy"] else sell_state(sp, L, s["t"], p["fee"])
        if not done and q > 0: sp = buy_state(sp, L, int(q * 1e18), p["fee"])
        out = v4math.buy_out_int(sp, L, bot["q"], p["fee"])
        fills.append((out / bot["minout"], p["ts"] >= DECOY_FILL))
    for sub in ("all", "from 16:28"):
        v = [f for f, late in fills if sub == "all" or late]
        if v: print(f"  extra {q:<6} ({sub:10s}) n {len(v):3d} fill min {min(v):.4f} p10 {pct(v,.1):.4f} p50 {pct(v,.5):.4f}; reverts (fill < 1) {sum(1 for x in v if x < 1)}")
# funding of fresh decoy wallets: scan back from the buy's block, 20 blocks a batch, <= 2,000 blocks
fresh = [(w, v) for w, v in wal.items() if all((x[4] or 0) <= 2 for x in v) and len(set(x[0] for x in v)) <= 2 and any(0.0049 <= x[2] <= 0.0050 for x in v)]
print(f"\nfresh 0.00495 decoy wallets (nonce <= 2 at their buys, <= 2 pools): {len(fresh)}; funding scan for the latest NFUND (argv, default 3)")
fund = []
NFUND = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for w, v in sorted(fresh, key=lambda kv: -kv[1][0][5])[:NFUND]:
    b0 = min(x[5] for x in v); found = None; scanned = 0
    for hi in range(b0, b0 - 2000, -20):
        bl = list(range(hi, hi - 20, -1)); scanned += 20
        res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in bl])
        for b, blk in zip(bl, res):
            for t in (blk or {}).get("transactions", []):
                if t["hash"] in [x[6] for x in v]: continue
                if (t.get("to") or "").lower() == w or (w[2:] in (t.get("input") or "").lower() and (t.get("from") or "").lower() != w):
                    found = {"block": b, "before_buy": b0 - b, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value_eth": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "nonce_funder": int(t["nonce"], 16), "tx": t["hash"]}
                    break
            if found: break
        if found: break
    fund.append((w, found, scanned))
    print(f"  {w} first buy block {b0}: " + (f"funded {found['before_buy']} blocks before by {found['from']} (nonce {found['nonce_funder']}) via {found['to'][:10]} sel {found['sel']} value {found['value_eth']:.6f}" if found else f"no funding tx found in {scanned} blocks"), flush=True)
json.dump([{"wallet": w, "funding": f, "scanned": s} for w, f, s in fund], open("r15_funding.json", "w"), indent=1)
