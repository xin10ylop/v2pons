"""d04: every buy in every pool of d01 (a Transfer of the token from the pair inside a tx with a Swap on that pair that takes WBNB in),
with its offset from the launch block, the tx's sender, target, selector, gas price, the Swap's sender (the contract that called the
pair) and recipient; then the crowd (recipients that buy in many pools through the router's 7ff36ab5 with tx.from == the recipient) and
everyone else; and for each (token, buyer) every later movement of the token out of the buyer (sell to the pair or any transfer).
-> d04_buyers.json (per buy rows), d04_buyers.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *
LS = launches(); T = transfers(); P = pairlogs(); TX = txs()
byp = {o["pair"]: o for o in LS}; byt = {o["token"]: o for o in LS}
launch_tx = set(o["tx"] for o in LS)
sw = C.defaultdict(list); burn_tx = set()
for r in P:
    if r[5] == "swap": sw[(r[3], r[4])].append(r)
    if r[5] == "burn": burn_tx.add((r[3], r[4]))
T.sort(key=lambda r: (r[0], r[1], r[2]))
buys = []; outs = C.defaultdict(list); ins = C.defaultdict(list)
for r in T:
    blk, txi, li, h, tok, fr, to, v = r
    o = byt.get(tok)
    if not o or h in launch_tx: continue
    pair = o["pair"]
    if fr == pair and to != pair:
        s = sw.get((h, pair))
        if (h, pair) in burn_tx and not s: kind = "burn_out"
        else:
            kind = "buy"
        if kind == "buy" and s:
            # the WBNB side in/out of this swap
            q_in = sum((x[6] if o["side"] == 0 else x[7]) for x in s); q_out = sum((x[8] if o["side"] == 0 else x[9]) for x in s)
            t = TX.get(h) or [None] * 9
            buys.append({"pool": pair, "token": tok, "L": o["L"], "size": o["size"], "code": o["code"]["size"], "blk": blk, "off": blk - o["L"], "txi": txi, "tx": h,
                         "buyer": to, "amt": v, "bnb_in": (q_in - q_out) / 1e18, "swap_sender": s[0][10], "swap_to": s[0][11],
                         "tx_from": t[0], "tx_to": t[1], "sel": t[2], "gp": t[3], "nonce": t[4], "value": (t[5] or 0) / 1e18, "txtype": t[8]})
            continue
    if fr != pair and fr not in DEAD:
        outs[(tok, fr)].append({"blk": blk, "to": to, "v": v, "tx": h, "kind": "sell" if to == pair else "transfer", "sel": (TX.get(h) or [None, None, None])[2],
                                "tx_from": (TX.get(h) or [None])[0], "tx_to": (TX.get(h) or [None, None])[1]})
    if to != pair:
        ins[(tok, to)].append({"blk": blk, "from": fr, "v": v, "tx": h})
print("buys", len(buys), "pools with buys", len(set(b["pool"] for b in buys)), "of", len(LS))
# the crowd: recipients whose buys are router 7ff36ab5 with tx.from == recipient, in many pools
pools_by = C.defaultdict(set); shape = C.defaultdict(C.Counter)
for b in buys:
    pools_by[b["buyer"]].add(b["pool"])
    shape[b["buyer"]][(b["tx_to"] == ROUTER, b["sel"], b["tx_from"] == b["buyer"])] += 1
npools = len(LS)
dist = C.Counter(min(len(v), 600) // 25 * 25 for v in pools_by.values())
print("buyers", len(pools_by), "pools per buyer (bucket of 25):", sorted(dist.items()))
for a, v in sorted(pools_by.items(), key=lambda kv: -len(kv[1]))[:60]:
    print("  ", a, len(v), dict(shape[a]))
json.dump({"buys": buys, "outs": {f"{k[0]}|{k[1]}": v for k, v in outs.items()}, "ins": {f"{k[0]}|{k[1]}": v for k, v in ins.items()}},
          open(os.path.join(CACHE, "d04_buyers_cache.json"), "w"))
