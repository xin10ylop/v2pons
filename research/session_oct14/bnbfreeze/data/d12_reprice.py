"""d12: the line's rule re-priced with the freeze, on every 1/10/25-BNB pool launched in the last 2 days (L >= head - 384,000 and
L + 260 <= head). Exact PancakeSwap V2 replay as the engine's (src/bnb_engine.py on_event/fire/sell): our $5 buy is the first tx of block
L+K on the reserves after block L+K-1; every swap, mint and burn from block L+K to L+259 is replayed on a copy with our buy in it (exact
input), and the tokens are sold at the start of block L+260; gas 370,000 x 0.1 gwei; $5 at the USDT/WBNB pair's price at L+K-1.
The freeze: the operator approve()s every stranger holder 4..67 blocks after its buy (d09/d10, 122 pre-dump freezes; median 25), and a
frozen holder recovers nothing. A hold of h blocks survives with the empirical probability S(h) = share of pre-dump freeze delays > h
(the 6 never-frozen strangers sold within 16 blocks, so they do not lengthen S). Also: the short holds that the data says are safe
(h <= 3: no freeze came sooner than 4 blocks), at every entry K, and the crowd's buying left after a later entry.
-> d12_reprice.json, d12_reprice.out"""
import json, os, sys, collections as C, statistics as ST
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
HEAD = 127552369; LS = [o for o in launches() if o["size"] in (1.0, 10.0, 25.0) and o["L"] >= HEAD - 384000 and o["L"] + 260 <= HEAD]
P = pairlogs(); TX = txs(); T10 = json.load(open(os.path.join(D, "d10_table.json"))); CROWD = set(T10["crowd"])
DEL = sorted(r["delay"] for r in T10["rows"] if r["before_dump"] and r["frozen"] and r["delay"] is not None and r["delay"] >= 0)
S = lambda h: sum(1 for d in DEL if d > h) / len(DEL)
USD_PAIR = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae"; GAS = 370000 * 10 ** 8; STAKE = 5.0
ev = C.defaultdict(list)
for r in P: ev[r[4]].append(r)
# swap tx -> recipient is crowd? (for the crowd's buying profile)
def price(b):
    r = rpc.call("eth_call", [{"to": USD_PAIR, "data": "0x0902f1ac"}, hex(b)])
    r0, r1 = int(r[2:66], 16), int(r[66:130], 16)
    return r0, r1                                                   # token0 USDT, token1 WBNB on this pair
px = {}
def stake_wei(b):
    k = b // 2000 * 2000
    if k not in px: px[k] = price(k)
    usd, bnb = px[k]
    return int(round(STAKE * 1e6)) * bnb * 10 ** 12 // (usd // 10 ** 12 * 10 ** 12 // 10 ** 12 if False else usd) if False else int(STAKE * 10 ** 18) * bnb // usd
def replay(o, K, X):
    """our buy first in block L+K, our sale first in block L+X; returns (q, tokens, back) or None (no reserves)"""
    rs = sorted(ev[o["pair"]], key=lambda r: (r[0], r[1], r[2])); side = o["side"]; L = o["L"]
    rq = rt = 0; i = 0
    while i < len(rs) and rs[i][0] < L + K:
        r = rs[i]
        if r[5] == "sync": rq, rt = (r[6], r[7]) if side == 0 else (r[7], r[6])
        i += 1
    if rq <= 0 or rt <= 0: return None
    q = stake_wei(L + K - 1); tok = amount_out(q, rq, rt); sq, st = rq + q, rt - tok
    while i < len(rs) and rs[i][0] < L + X:
        r = rs[i]; i += 1
        if r[5] == "swap":
            a0i, a1i, a0o, a1o = r[6:10]; qi, ti = (a0i, a1i) if side == 0 else (a1i, a0i); qo, to = (a0o, a1o) if side == 0 else (a1o, a0o)
            if qi > qo:
                a = qi - qo; out = amount_out(a, sq, st); sq += a; st -= out
            else:
                a = ti - to; out = amount_out(a, st, sq); sq -= out; st += a
        elif r[5] == "mint":
            mq, mt = (r[6], r[7]) if side == 0 else (r[7], r[6])
            if mq > 0 and mt > 0: tb = mq * st // sq; sq, st = (sq + mq, st + tb) if tb <= mt else (sq + mt * sq // st, st + mt)
        elif r[5] == "burn":
            pass                                                     # no burn before the dump in this family (d06: every dump is a sell)
    back = amount_out(tok, st, sq)
    return q, tok, back
out = {"n_pools": len(LS), "delays": DEL, "rules": {}}
print("pools (1/10/25 BNB, last 2 days):", len(LS), C.Counter(o["size"] for o in LS), "| freeze delays n", len(DEL), "S(3)=%.3f S(10)=%.3f S(25)=%.3f S(67)=%.3f S(210)=%.3f" % (S(3), S(10), S(25), S(67), S(210)))
# sanity: our own pool, K=52: tokens vs what our wallet received
ours = [o for o in LS if o["pair"] == "0x2de2620b04a0382390b18441cd033da7b798e57e"]
if ours:
    r = replay(ours[0], 52, 260); print("our pool K=52: replay tokens for $5", r[1] if r else None, "| our wallet received 26815492626516 for 0.006722 BNB (it was tx index 35 of its block)")
def stats(xs):
    xs = sorted(xs); n = len(xs)
    return {"n": n, "mean": sum(xs) / n, "median": xs[n // 2], "win": sum(1 for x in xs if x > 0) / n} if n else None
rows = {}
for K in (50, 60, 70, 80, 100, 120, 150, 180, 193, 200, 220, 240, 250, 257, 259):
    for size in (1.0, 10.0, 25.0, "all"):
        g = []; nt = []
        for o in LS:
            if size != "all" and o["size"] != size: continue
            r = replay(o, K, 260)
            if not r: continue
            q, tok, back = r; g.append((back - q) / q); nt.append((back - q - GAS) / q)
        sg, sn = stats(g), stats(nt); h = 260 - K; s = S(h)
        exp = [s * (1 + x) - 1 for x in nt]                         # frozen: -100% of the stake (the tokens never come back)
        rows[(K, size)] = {"K": K, "size": size, "hold": h, "gross": sg, "net_unfrozen": sn, "survive": s, "net_with_freeze_mean": sum(exp) / len(exp) if exp else None,
                           "usd_per_trade_with_freeze": STAKE * sum(exp) / len(exp) if exp else None}
        if size == "all" or K in (50, 257):
            print("K +%3d sell +260 hold %3d | %-4s n %3d | gross mean %+7.2f%% median %+7.2f%% | net (no freeze) mean %+7.2f%% win %3.0f%% | S(hold) %.3f -> net with the freeze %+7.2f%% ($%+.3f a trade)" % (
                K, h, size, sn["n"], 100 * sg["mean"], 100 * sg["median"], 100 * sn["mean"], 100 * sn["win"], s, 100 * rows[(K, size)]["net_with_freeze_mean"], rows[(K, size)]["usd_per_trade_with_freeze"]))
out["rules"] = {f"{k[0]}|{k[1]}": v for k, v in rows.items()}
# the short holds the data calls safe (h <= 3), every entry K from +40 to +1000: the best K per tier
print("short holds (sell h blocks after the buy, before any freeze seen): best entry per tier and h, mean net over the pools")
best = {}
for size in (1.0, 10.0, 25.0):
    pools = [o for o in LS if o["size"] == size]
    for h in (1, 2, 3):
        res = []
        for K in range(40, 1000, 5):
            nt = []
            for o in pools:
                r = replay(o, K, K + h)
                if r: nt.append((r[2] - r[0] - GAS) / r[0])
            if nt: res.append((sum(nt) / len(nt), K, sum(1 for x in nt if x > 0) / len(nt), len(nt)))
        res.sort(reverse=True); best[(size, h)] = res[:3]
        print("  size %4s h %d: best K %s" % (size, h, ["+%d mean %+.3f%% win %.0f%% n %d" % (K, 100 * m, 100 * w, n) for m, K, w, n in res[:3]]))
out["short_holds"] = {f"{k[0]}|{k[1]}": v for k, v in best.items()}
# the crowd's buying left after an entry at K (before +260 and before the dump), share of the crowd's BNB per tier
print("crowd buying by offset (BNB bought by the 120 crowd wallets, 1/10/25 pools of the last 2 days):")
cb = C.defaultdict(lambda: C.Counter())
for o in LS:
    side = o["side"]
    for r in ev[o["pair"]]:
        if r[5] != "swap": continue
        a0i, a1i, a0o, a1o = r[6:10]; qi = a0i if side == 0 else a1i; qo = a0o if side == 0 else a1o
        if qi > qo and r[11] in CROWD:
            cb[o["size"]][r[0] - o["L"]] += (qi - qo) / 1e18
prof = {}
for size in (1.0, 10.0, 25.0):
    c = cb[size]; tot260 = sum(v for k, v in c.items() if k < 260); first = min(c) if c else None
    prof[size] = {"first_crowd_off_min": first, "share_after": {K: (sum(v for k, v in c.items() if K <= k < 260) / tot260 if tot260 else None) for K in (50, 60, 70, 80, 100, 150, 200, 250)},
                  "bnb_before_260": tot260, "bnb_260_to_dump": sum(v for k, v in c.items() if k >= 260)}
    print("  size %4s: first crowd buy at +%s; crowd BNB before +260 %.2f (260..dump %.2f); share of it at or after +K:" % (size, first, tot260, prof[size]["bnb_260_to_dump"]),
          " ".join("+%d %.0f%%" % (K, 100 * v) for K, v in prof[size]["share_after"].items()))
out["crowd_profile"] = prof
json.dump(out, open(os.path.join(D, "d12_reprice.json"), "w"), indent=0, default=str)
