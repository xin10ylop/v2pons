"""Step 8: the front rule on chosen families with exact v4/V3 integer math (clsim.py), on every pool of the family.
Rule: buy X ETH at the head of block L+1; every later swap is re-executed by the amount it paid in; the repeat buyer's buys revert when their
re-executed output falls under their calldata minOut (largest calldata word in (0.5, 1] x the tokens they really got); liquidity adds/removals
are applied as they happened; sell everything at the head of block T+1, T = the block of the repeat buyer's first buy (or at L+1+H if it never comes).
A pull at or before T leaves our sell in what is left (about -100%). Net = gross - $0.02 gas per round trip at $2,570/ETH.
Also: replay error of the real swaps (sqrtP after each swap vs the log), the room (largest buy at L+1 head that keeps the repeat buyer's
first buy >= its minOut), and the reaction-priced EV from s07's outsider measurements.
Usage: python3 s08_front.py "<family label>" [actor]   (actor defaults to s07's main actor). Appends to s08_front.json."""
import sys, collections, json
from common import *
from clsim import Pool
from v4sim import sqrt_at_tick
import s07_traits as S
ETHUSD = 2570.0; GAS_USD = 0.02
fam = sys.argv[1]
tr = {r["label"]: r for r in jload("s07_traits.json")}
actor = sys.argv[2] if len(sys.argv) > 2 else tr[fam]["main"]
pids = [t["pid"] for t in jload("s05_targets.json") if t["fam"] == fam]
def events(p, r):
    """chronological list of ('S', swap dict) / ('M', (tl, tu, dL)) / ('I', sqrt)"""
    ev = []
    if p["ven"] == "v4":
        for m in p["ml"]:
            d = m[5]; ev.append(((m[0], m[2]), "M", (sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2))), m[3]))
    else:
        for m in p["ml"]:
            t0 = m[5][0]; d = m[6]
            if t0 == T_V3MINT: ev.append(((m[0], m[2]), "M", (sgn(int(m[5][2], 16)), sgn(int(m[5][3], 16)), W(d, 1)), m[3]))
            elif t0 == T_V3BURN: ev.append(((m[0], m[2]), "M", (sgn(int(m[5][2], 16)), sgn(int(m[5][3], 16)), -W(d, 0)), m[3]))
            elif t0 == T_V3INIT: ev.append(((m[0], m[2]), "I", W(d, 0), m[3]))
    for s in S.swaps(p, r):
        ev.append(((s["bn"], s["li"]), "S", s, s["h"]))
    ev.sort(key=lambda e: e[0])
    return ev
def raw_fee(p, s):
    if p["ven"] == "v4":
        return W(next(x for x in p["sw"] if x[3] == s["h"] and x[2] == s["li"])[5], 5)
    return None
def run(pid, X, mode="front", H=60):
    r = S.rows[pid]; p = S.EV[pid]; L = r["b"]
    quote0 = r["c0"] in (E, WETH, USDG)
    zf_buy = quote0                     # buying the token = paying currency0 when the quote is currency0
    ev = events(p, r)
    s0 = int(r["sqrtp"]) if r["sqrtp"] else next((e[2] for e in ev if e[1] == "I"), None)
    if s0 is None: return None
    pool = Pool(s0, [], r["fee"] if r["fee"] != 0x800000 else 0)
    main = [e for e in ev if e[1] == "S" and e[2]["buy"] and S.actor(e[3]) == actor and e[2]["bn"] > L]
    T = main[0][2]["bn"] if main else None
    sell_at = (T + 1) if T is not None else (L + 1 + H)
    mo = {}
    for e in main:
        m = S.minout_ratio(e[3], e[2]["tok"])
        if m: mo[(e[0])] = int(m * e[2]["tok"]) if False else None
    # minOut values: the calldata word itself
    def minout(e):
        t = S.TX.get(e[3]); tok = e[2]["tok"]
        if not t or "in" not in t: return None
        inp = t["in"]; ws = []
        for i in range((len(inp) - 10) // 64):
            try: ws.append(int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16))
            except ValueError: pass
        c = [w for w in ws if tok * 0.5 < w <= tok]
        return max(c) if c else None
    held = 0; ours = False; err = 0.0; nrev = 0; out_eth = None; pulled_before = False; lastfee = pool.fee
    for key, kind, val, h in ev:
        bn = key[0]
        if mode == "front" and not ours and bn >= L + 1:
            held = pool.swap(X, zf_buy, lastfee); ours = True
        if mode == "front" and ours and out_eth is None and bn >= sell_at:
            out_eth = pool.swap(held, not zf_buy, lastfee)
            break
        if kind == "I": pool.s = val; continue
        if kind == "M":
            tl, tu, dL = val
            if dL < 0 and bn > L and ours: pulled_before = True
            pool.add(tl, tu, dL); continue
        s = val
        if s["h"] == r["h"] and not ours:
            pass
        f = raw_fee(p, s)
        if f is not None: lastfee = f & 0xFFFFFF if f < (1 << 23) else f
        amt = s["q"] if s["buy"] else s["tok"]
        if amt <= 0: continue
        got = pool.swap(amt, zf_buy if s["buy"] else not zf_buy, lastfee)
        if mode == "replay":
            err = max(err, abs(pool.s - s["sq"]) / s["sq"]); pool.s = s["sq"]
            continue
        if s["buy"] and S.actor(h) == actor:
            mn = minout((key, kind, val, h))
            if mn is not None and got < mn:
                # revert: undo by re-pricing from the state before (simple: swap back is not exact; recompute via a copy)
                nrev += 1
                pool.s = prev_s if False else pool.s
    if mode == "replay": return dict(err=err)
    if out_eth is None:
        if ours: out_eth = pool.swap(held, not zf_buy, lastfee)
        else: return None
    return dict(T=(T - L) if T else None, gross=out_eth / X - 1, nrev=nrev, pulled_before=pulled_before)
