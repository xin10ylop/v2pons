#!/usr/bin/env python3
"""copysim.py CHAIN KIND:ID DAY... : copy-trade one trader (snipers.py's group: contract:0x... or wallet:0x...) on the tapes of the days
given, on each pool's real reserve path.

Entry, for each of its round trips:
  slot  our buy lands in its block, right after its buy (the state after its swap)
  +1    our buy lands in the next block (the state at the end of its block); an entry in the pull's block or later is a loss
Our buy: STAKE native (env STAKES, comma list; default 0.002,0.01,0.05) at the pool's fee, against the reserves of that state.
Exit, our engineered sell of all our tokens:
  mirror      when it sells: right after its sell (slot) or at the end of its sell's block (+1)
  hold N      N seconds after our entry (the state at the end of the block before)
  tp X        the first block where selling returns +X% or more (we sell in the next block, at that block's end state), else when it sells,
              else at HOLD_MAX seconds
  cap N       mirror, but sell N seconds after our entry if it has not sold by then
With ENTRIES (env, a file in this folder from entries.py) the copy follows every entry the wallet made, sold or not, instead of only its
round trips; mirror then loses the stake on each entry it never sold.
A sell landing in the pull's block or later is -100% (the liquidity is gone); so is a buy in the pull's block. Gas per round trip:
GAS (default 0.000006 on Robinhood, 0.00002 on Base). Not modelled: our buy's impact on later trades, and the operator reacting to our buy
(followers.py looks at what happened to other wallets that bought right after this trader).

Prints, per stake and entry, each exit rule: trips, wins, losses to the pull, profit, return on stake, and profit per day.
Read-only (reads out/ only)."""
import os, sys, json, gzip, bisect, collections, math

STAKES = [float(x) for x in os.environ.get("STAKES", "0.002,0.01,0.05").split(",")]
HOLD_MAX = float(os.environ.get("HOLD_MAX", "120"))
ENTRIES = os.environ.get("ENTRIES")
RULES = [("mirror", None), ("hold", 3), ("hold", 10), ("hold", 30), ("hold", 60), ("tp", 0.05), ("tp", 0.10), ("tp", 0.20), ("tp", 0.40),
         ("cap", 30), ("cap", 60), ("cap", 120), ("cap", 180)]


def buy(x, y, s, f):
    return y - x * y / (x + s * (1 - f))


def sell(x, y, q, f):
    return x - x * y / (y + q * (1 - f))


class Pool:
    def __init__(self, p, bt):
        self.p, self.bt = p, bt; self.ev = p["ev"]; self.bns = [e[0] for e in self.ev]

    def end_of(self, bn):
        """the index of the last swap at or before block bn"""
        return bisect.bisect_right(self.bns, bn) - 1

    def state(self, i):
        e = self.ev[i]
        return (e[4], e[5]) if e[4] else None


def copy_trip(P, b, s, stake, entry, rule, gas):
    """one copy: (profit, outcome) with outcome 'win', 'loss', 'pulled' or None when there is no state to price"""
    p, ev, pull, f = P.p, P.ev, P.p["pull"], P.p["fee"]
    bb = ev[b][0]
    if entry == "slot":
        ie, eblk = b, bb
    else:
        ie, eblk = P.end_of(bb), bb + 1
    if eblk >= pull:
        return -stake - gas, "pulled"
    st0 = P.state(ie)
    if not st0:
        return None, None
    q = buy(*st0, stake, f)
    kind, par = rule
    their_sell = s if s is not None else len(ev)
    if kind == "cap" and s is not None and ev[s][0] + (entry != "slot") > eblk + max(1, math.ceil(par / P.bt)):
        kind = "hold"                                     # it holds past the cap: sell at the cap
    elif kind == "cap":
        kind = "mirror" if s is not None else "hold"
    if kind == "mirror":
        if s is None:                                     # it never sold: the pull takes us with it
            return -stake - gas, "pulled"
        sb = ev[s][0]
        ix, xblk = (s, sb) if entry == "slot" else (P.end_of(sb), sb + 1)
    elif kind == "hold":
        xblk = eblk + max(1, math.ceil(par / P.bt)); ix = P.end_of(xblk - 1)
    else:                                                 # tp: watch block ends after our entry
        cap = eblk + max(1, math.ceil(HOLD_MAX / P.bt)); ix, xblk = None, None
        k = ie + 1
        while k < len(ev) and ev[k][0] < cap:
            if ev[k][0] >= pull:
                break
            last = P.end_of(ev[k][0])
            stt = P.state(last)
            if stt and sell(*stt, q, f) >= stake * (1 + par):
                ix, xblk = last, ev[k][0] + 1; break
            if last >= their_sell:                        # it sold: follow it out next block
                ix, xblk = last, ev[last][0] + 1; break
            k = last + 1
        if ix is None:
            xblk = cap; ix = P.end_of(cap - 1)
    if xblk >= pull:
        return -stake - gas, "pulled"
    stx = P.state(ix)
    if not stx:
        return None, None
    out = sell(*stx, q, f) - stake - gas
    return out, ("win" if out > 0 else "loss")


def main(ch, key, days):
    here = os.path.dirname(os.path.abspath(__file__))
    kind, ident = key.split(":", 1)
    gas = float(os.environ.get("GAS", "0.000006" if ch == "rh" else "0.00002"))
    trips = []
    ent = collections.defaultdict(list)
    if ENTRIES:
        for x in json.load(open(os.path.join(here, ENTRIES))):
            ent[x["day"]].append(x)
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt"))
        pools = {}
        mine = ent[day] if ENTRIES else [t for t in d["trips"] if (kind == "contract" and t.get("via") == ident) or (kind == "wallet" and t.get("who") == ident)]
        for t in mine:
            P = pools.get(t["pool"]) or pools.setdefault(t["pool"], Pool(d["pools"][t["pool"]], d["bt"]))
            trips.append((day, P, t))
    print(f"{ch} {key}: {len(trips)} {'entries' if ENTRIES else 'round trips'} on {len({id(x[1]) for x in trips})} pools, days {days[0]}..{days[-1]}"
          + (f", {sum(t['s'] is None for _, _, t in trips)} never sold" if ENTRIES else f"; its own profit {sum(t['pnl'] for _, _, t in trips):+.4f}")
          + f" on a median stake {sorted(t['paid'] for _, _, t in trips)[len(trips) // 2] if trips else 0:.5f}")
    res = {}
    for stake in STAKES:
        for entry in ("slot", "+1"):
            print(f"  stake {stake:g}, entry {entry}:")
            for rule in RULES:
                agg = collections.Counter(); per = collections.defaultdict(float); pnl = 0.0; n = 0
                for day, P, t in trips:
                    v, o = copy_trip(P, t["b"], t["s"], stake, entry, rule, gas)
                    if o is None:
                        continue
                    n += 1; agg[o] += 1; pnl += v; per[day] += v
                name = f"{rule[0]} {rule[1] if rule[1] is not None else ''}".strip()
                res[f"{stake}|{entry}|{name}"] = {"n": n, **agg, "pnl": pnl, "per_day": dict(per)}
                print(f"    {name:9s} n {n:5d} won {agg['win']:5d} lost {agg['loss']:5d} pulled {agg['pulled']:4d} | pnl {pnl:+.4f} ({pnl / (n * stake) if n else 0:+.1%} a trip)"
                      f" | per day " + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(per.items())), flush=True)
    json.dump(res, open(os.path.join(here, f"out/copysim_{ch}_{ident[:10]}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
