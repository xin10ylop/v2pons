"""Step 8: the front rule on chosen families with exact v4/V3 integer math (clsim.py), on every pool of the family.
Rule: buy X ETH at the head of block L+1; every later swap is re-executed by the amount it paid in (exact input); the repeat buyer's buys
revert when their re-executed output falls under their calldata minOut (largest calldata word in (0.5, 1] x the tokens they really got);
liquidity adds/removals are applied as they happened; sell everything at the head of block T+1, T = the block of the repeat buyer's first buy
(or at L+1+H when it never comes). A pull at or before T leaves our sell in what is left. Net = gross - $0.02 gas a round trip at $2,570/ETH.
Also: the replay check (sqrtP after each real swap vs its log), the room (largest buy at the L+1 head that keeps the repeat buyer's first buy
at or above its minOut), and variants for the operator's reaction: the repeat buyer skips the pool; the pool is pulled LAG blocks after our buy.
Usage: python3 s08_front.py "<family label>" [actor]. Writes s08_front_<n>.json and prints a summary."""
import sys, os, collections, json, copy, hashlib
from common import *
from clsim import Pool
import s07_traits as S
ETHUSD = 2570.0; GAS_USD = 0.02
OURS = "0x2abb5653"   # our relay contract (excluded from every replay)
def events(p, r):
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
    fees = {}
    if p["ven"] == "v4":
        for x in p["sw"]: fees[(x[0], x[2])] = W(x[5], 5)
    for s in S.swaps(p, r):
        s["fee"] = fees.get((s["bn"], s["li"]))
        ev.append(((s["bn"], s["li"]), "S", s, s["h"]))
    ev.sort(key=lambda e: e[0])
    return ev
def minout(h, tok):
    t = S.TX.get(h)
    if not t or "in" not in t: return None
    inp = t["in"]; ws = []
    for i in range((len(inp) - 10) // 64):
        try: ws.append(int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16))
        except ValueError: pass
    c = [w for w in ws if tok * 0.5 < w <= tok]
    return max(c) if c else None
class Sim:
    def __init__(self, pid, actor):
        self.r = r = S.rows[pid]; self.p = p = S.EV[pid]; self.L = r["b"]; self.actor = actor
        self.ev = events(p, r)
        self.s0 = int(r["sqrtp"]) if r["sqrtp"] else next((e[2] for e in self.ev if e[1] == "I"), None)
        self.t0 = r["tick"] if r.get("tick") is not None else None
        self.zb = r["c0"] in (E, WETH, USDG)        # buying the token pays currency0
        self.basefee = r["fee"] if r["fee"] < 0x800000 else 0
        main = [e for e in self.ev if e[1] == "S" and e[2]["buy"] and S.actor(e[3]) == actor and e[2]["bn"] > self.L]
        self.T = main[0][2]["bn"] if main else None
        self.main_first = main[0] if main else None
        ad = [e for e in self.ev if e[1] == "M" and e[2][2] > 0]
        self.A = ad[0][0][0] if ad else self.L
        pl = [e for e in self.ev if e[1] == "M" and e[2][2] < 0]
        self.pull = pl[0][0][0] if pl else None
    def replay_err(self):
        pool = Pool(self.s0, [], self.basefee, self.t0); err = 0.0; n = 0
        for key, kind, val, h in self.ev:
            if kind == "I": pool.s = val; pool.tick = None; from clsim import tick_at; pool.tick = tick_at(val); continue
            if kind == "M": pool.add(*val); continue
            s = val; amt = s["q"] if s["buy"] else s["tok"]
            if amt <= 0 or s["bn"] > self.L + 400: continue
            pool.swap(amt, self.zb if s["buy"] else not self.zb, s["fee"] if s["fee"] is not None else self.basefee)
            err = max(err, abs(pool.s - s["sq"]) / s["sq"]); n += 1
        return err, n
    def front(self, X, H=60, skip_main=False, pull_lag=None, entry=1, sell_off=None):
        """returns dict(gross, out, T, nrev, sold_at) or None"""
        L = self.L; pool = Pool(self.s0, [], self.basefee, self.t0); lastfee = self.basefee
        B = max(L, self.A) + entry          # our buy: head of the block after the launch (or after the first liquidity add)
        sell_at = (self.T + 1) if (self.T is not None and not skip_main and self.T >= B) else (B + H)
        if sell_off is not None: sell_at = L + sell_off
        held = None; nrev = 0; out = None; pulled = False
        forced_pull = (B + pull_lag) if pull_lag is not None else None
        for key, kind, val, h in self.ev:
            bn = key[0]
            if held is None and bn >= B:
                held = pool.swap(X, self.zb, lastfee)
                if held <= 0: return None
            if held is not None and forced_pull is not None and bn >= forced_pull and not pulled:
                pool.net = {}; pulled = True
            if held is not None and bn >= sell_at:
                out = pool.swap(held, not self.zb, lastfee); break
            if kind == "I":
                from clsim import tick_at; pool.s = val; pool.tick = tick_at(val); continue
            if kind == "M":
                if held is None or not pulled: pool.add(*val)
                continue
            s = val
            if s["fee"] is not None: lastfee = s["fee"]
            amt = s["q"] if s["buy"] else s["tok"]
            if amt <= 0: continue
            if S.actor(h).startswith(OURS): continue      # our own relay's trades are replaced by the simulated one
            is_main = s["buy"] and S.actor(h) == self.actor
            if is_main and skip_main and held is not None: continue
            if held is not None and is_main:
                snap = pool.snap()
                got = pool.swap(amt, self.zb, lastfee)
                mn = minout(h, s["tok"])
                if mn is not None and got < mn:
                    pool.restore(snap); nrev += 1
                continue
            pool.swap(amt, self.zb if s["buy"] else not self.zb, lastfee)
        if held is None: return None
        if out is None: out = pool.swap(held, not self.zb, lastfee)
        return dict(gross=out / X - 1, T=(self.T - L) if self.T else None, nrev=nrev, pull=(self.pull - L) if self.pull else None)
    def room(self, lo=0, hi=None):
        """largest X (wei) at the L+1 head that keeps the repeat buyer's first buy at or above its minOut"""
        if not self.main_first: return None
        mn = minout(self.main_first[3], self.main_first[2]["tok"])
        if mn is None: return None
        def ok(X):
            r = self.front(X)
            return r is not None and r["nrev"] == 0
        hi = hi or 10 ** 19
        if ok(hi): return hi
        lo = 10 ** 12
        if not ok(lo): return 0
        for _ in range(40):
            mid = (lo + hi) // 2
            if ok(mid): lo = mid
            else: hi = mid
            if hi - lo < 10 ** 13: break
        return lo
def q(xs, f):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None
def summary(rs, X):
    g = [x["gross"] for x in rs]
    gas = GAS_USD / (X / 1e18 * ETHUSD)
    if not g: return "n 0"
    return "n %d gross mean %+.2f%% median %+.2f%% p10 %+.2f%% min %+.2f%% pos %d/%d | net mean %+.2f%%" % (
        len(g), 100 * sum(g) / len(g), 100 * q(g, .5), 100 * q(g, .1), 100 * min(g), sum(1 for x in g if x > 0), len(g), 100 * (sum(g) / len(g) - gas))
if __name__ == "__main__":
    fam = sys.argv[1]
    tr = {r["label"]: r for r in jload("s07_traits.json")}
    actor = sys.argv[2] if len(sys.argv) > 2 else tr[fam]["main"]
    pids = [t["pid"] for t in jload("s05_targets.json") if t["fam"] == fam]
    X5 = int(5 / ETHUSD * 1e18)
    sims = []
    for pid in pids:
        try:
            sm = Sim(pid, actor)
            if sm.s0: sims.append(sm)
        except Exception as e: print("skip", pid[:12], e)
    print("== %s | actor %s | pools %d (repeat buyer present in %d)" % (fam, actor, len(sims), sum(1 for s in sims if s.T)))
    errs = [s.replay_err() for s in sims]
    print("replay check: max rel sqrtP error p50 %.2e p90 %.2e max %.2e over %d swaps" % (q([e for e, n in errs], .5), q([e for e, n in errs], .9), max(e for e, n in errs), sum(n for e, n in errs)))
    good = [s for s, (e, n) in zip(sims, errs) if e < 1e-6]
    print("pools with exact replay (err < 1e-6):", len(good), "of", len(sims))
    res = {}
    for name, kw in (("front L+1, sell T+1 (no reaction)", {}), ("front L+2, sell T+1", dict(entry=2)),
                     ("main skips the pool, sell L+1+60", dict(skip_main=True)), ("main skips, sell L+1+20", dict(skip_main=True, H=20)),
                     ("pulled 4 blocks after our buy", dict(pull_lag=4)), ("pulled 8 blocks after our buy", dict(pull_lag=8))):
        rs = [x for x in (s.front(X5, **kw) for s in good) if x]
        res[name] = rs
        print("  %-40s %s" % (name, summary(rs, X5)))
    for so in [int(x) for x in os.environ.get("SELL_OFFS", "").split(",") if x]:
        rs = [x for x in (s.front(X5, sell_off=so) for s in good) if x]
        res["sell at L+%d" % so] = rs
        print("  %-40s %s" % ("front L+1, sell at L+%d (no reaction)" % so, summary(rs, X5)))
        rs = [x for x in (s.front(X5, sell_off=so, skip_main=True) for s in good) if x]
        print("  %-40s %s" % ("  same, main skips the pool", summary(rs, X5)))
    rs = [x for x in (s.front(X5) for s in good if s.T) if x]
    print("  %-40s %s" % ("no reaction, pools where the buyer came", summary(rs, X5)))
    rooms = [s.room() for s in good[:60] if s.T]
    rooms = [x / 1e18 for x in rooms if x is not None]
    print("  room (ETH ahead of the repeat buyer's first buy) p10/50/90: %s/%s/%s over %d pools" % (q(rooms, .1), q(rooms, .5), q(rooms, .9), len(rooms)))
    nm = hashlib.md5(fam.encode()).hexdigest()[:6]
    jdump(dict(fam=fam, actor=actor, rooms=rooms, res={k: v for k, v in res.items()}), "s08_front_%s.json" % nm)
