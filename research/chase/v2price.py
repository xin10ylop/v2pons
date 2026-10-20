#!/usr/bin/env python3
"""v2price.py base_v2.json MARKER_WALLET [BLOCK_S=2]: the operator's V2 pairs (a marker buy by MARKER_WALLET in the creation block, or a
fresh creator with >= 3 ETH), their cadence, liquidity, pulls, fleet, the reaction to outsiders, and the paper early seat."""
import json, sys, statistics as st, collections, time
d = json.load(open(sys.argv[1])); M = sys.argv[2][2:].lower(); BT = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
pairs, txs = d["pairs"], d["txs"]; FEE = 0.003
def med(x): return round(st.median(x), 4) if x else None
def buys_sells(p):
    out = []
    for s in p["swaps"]:
        bn, li, a0i, a1i, a0o, a1o, h = s; eth_in, eth_out = (a0i, a0o) if p["weth_is0"] else (a1i, a1o); tok_in, tok_out = (a1i, a1o) if p["weth_is0"] else (a0i, a0o)
        t = txs.get(h); out.append({"bn": bn, "buy": eth_in > 0, "eth": (eth_in if eth_in > 0 else eth_out) / 1e18, "tok_in": tok_in, "tok_out": tok_out, "eth_in": eth_in, "eth_out": eth_out, "from": t[0] if t else None, "nonce": t[2] if t else None, "to": t[1] if t else None})
    return out
ops = {}
for pair, p in pairs.items():
    sw = buys_sells(p); p["_sw"] = sw
    marker = any(s["from"] == M and s["bn"] == p["bn"] for s in sw)
    if marker or (p.get("nonce") is not None and p["nonce"] <= 3 and p.get("eth_in", 0) >= 0.5): ops[pair] = p; p["_marker"] = marker
print(f"WETH pairs in window: {len(pairs)}; with a mint: {sum(1 for p in pairs.values() if p.get('eth_in'))}; operator pairs: {len(ops)} (marker in creation block: {sum(1 for p in ops.values() if p['_marker'])})")
if not ops: sys.exit()
wp = collections.defaultdict(set)
for pair, p in ops.items():
    for s in p["_sw"]:
        if s["from"]: wp[s["from"]].add(pair)
fleet = {w for w, ps in wp.items() if len(ps) >= 3}
rows = []
for pair, p in sorted(ops.items(), key=lambda kv: kv[1]["bn"]):
    sw = p["_sw"]; b0 = p["bn"]; burn = min([b[0] for b in p["burns"]], default=None)
    buys = [s for s in sw if s["buy"]]; fleet_buys = [s for s in buys if s["from"] in fleet]; outs = [s for s in buys if s["from"] and s["from"] not in fleet and s["from"] != M and (s["nonce"] or 0) > 2]
    # reserves path from the mint, then each swap in order
    R_eth, R_tok = (p["mints"][0][1], p["mints"][0][2]) if p["weth_is0"] else (p["mints"][0][2], p["mints"][0][1])
    path = [(b0, R_eth, R_tok)]
    for s in sorted(sw, key=lambda s: (s["bn"],)):
        R_eth += s["eth_in"] - s["eth_out"]; R_tok += s["tok_in"] - s["tok_out"]; path.append((s["bn"], R_eth, R_tok))
    def state(bn):
        prev = [x for x in path if x[0] <= bn]; return prev[-1][1], prev[-1][2]
    def ret(stake, entry_bn, exit_bn):
        if burn is not None and burn <= exit_bn: return -1.0
        re, rt = state(entry_bn); x = stake * (1 - FEE); tok = x * rt / (re + x); re2, rt2 = state(exit_bn)
        # our own buy moved the reserves; include it
        re2 += stake; rt2 -= tok; y = tok * (1 - FEE); return (y * re2 / (rt2 + y) - stake) / stake
    first_fleet = fleet_buys[0]["bn"] - b0 if fleet_buys else None
    r = {"bn": b0, "eth": round(p.get("eth_in", 0), 2), "creator_nonce": p.get("nonce"), "marker": p["_marker"], "burn": (burn - b0) if burn is not None else None, "nbuys": len(buys), "fleet_buys": len(fleet_buys), "fleet_eth": round(sum(s["eth"] for s in fleet_buys), 3), "first_fleet": first_fleet, "outsiders": len(outs), "out_eth": round(sum(s["eth"] for s in outs), 3), "first_out": (outs[0]["bn"] - b0) if outs else None, "sells": len([s for s in sw if not s["buy"]])}
    for stake in (0.02, 0.1, 0.5):
        r["A%g" % stake] = {k: ret(stake * 1e18, b0 + 1, b0 + k) for k in (5, 15, 30, 60, 120, 300)}
    rows.append(r)
json.dump(rows, open(sys.argv[1].replace(".json", "_priced.json"), "w"))
hours = (rows[-1]["bn"] - rows[0]["bn"]) * BT / 3600
print(f"operator pairs {len(rows)} over {hours:.1f} h ({len(rows)/max(hours,0.1):.1f}/h); first block {rows[0]['bn']}, last {rows[-1]['bn']}; creator nonces {collections.Counter(r['creator_nonce'] for r in rows).most_common(4)}")
print(f"liquidity ETH: median {med([r['eth'] for r in rows])}, min {min(r['eth'] for r in rows)}, max {max(r['eth'] for r in rows)}; last 10: {[r['eth'] for r in rows[-10:]]}")
pulls = [r["burn"] for r in rows if r["burn"] is not None]; print(f"pulled inside {900*BT/60:.0f} min: {len(pulls)}/{len(rows)}, offset blocks p10/50/90 {sorted(pulls)[len(pulls)//10] if pulls else None}/{med(pulls)}/{sorted(pulls)[len(pulls)*9//10] if pulls else None} (= {med(pulls)*BT if pulls else None} s)")
print(f"fleet: {len(fleet)} recurring wallets; buys per pair median {med([r['nbuys'] for r in rows])}, fleet buys median {med([r['fleet_buys'] for r in rows])} ({med([r['fleet_eth'] for r in rows])} ETH), first fleet buy at +{med([r['first_fleet'] for r in rows if r['first_fleet'] is not None])} blocks; sells per pair median {med([r['sells'] for r in rows])}")
oo = [r for r in rows if r["outsiders"]]; print(f"pairs with outsider buys: {len(oo)}/{len(rows)}, outsider ETH median {med([r['out_eth'] for r in oo])}; pull after first outsider buy (blocks): {sorted([(r['burn']-r['first_out']) for r in oo if r['burn'] is not None])[:30]}; outsider pairs not pulled in window: {sum(1 for r in oo if r['burn'] is None)}")
def summ(vals):
    v = [x for x in vals if x is not None]; return f"n={len(v)} mean {100*st.mean(v):+.1f}% median {100*st.median(v):+.1f}% win {100*sum(1 for x in v if x > 0)/len(v):.0f}% pulled {sum(1 for x in v if x <= -0.99)}" if v else "n=0"
for stake in (0.02, 0.1, 0.5):
    print(f"\n== early seat, buy at creation+1 with {stake} ETH, sell at creation+k blocks ({BT} s each)")
    for k in (5, 15, 30, 60, 120, 300): print(f"   k={k:>3} ({k*BT:>4.0f} s): {summ([r['A%g' % stake][k] for r in rows])}")
print("\nlast 8 operator pairs:")
for r in rows[-8:]: print("  ", {k: v for k, v in r.items() if not k.startswith("A")}, "A0.1@60:", None if r["A0.1"][60] is None else round(100*r["A0.1"][60], 1))
