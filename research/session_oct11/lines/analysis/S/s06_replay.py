"""S06: replay of the line on its launches of the last 6 / 24 / 48 h with analyst C's V3 simulator (C/replay.py: V3Sim, replay(); buy at the
head of block L+a after every event of blocks < L+a, re-simulate every later swap by amount, sell all at the head of L+b; a pull (Burn with
L > 0) in a block <= L+b = -100%; gas $0.02 per round trip; ETH = $2570 as in REPORT_C).
Rules (m = the mint's offset, o = the launcher's own first buy's offset, any size, o50 = its first own buy >= 0.045 ETH):
  census   a = m+2, sell 1 block after the first buy >= 0.005 ETH at/after a, cap +60 (REPORT_C's rule, for reference)
  (a)      a = m+2, b = min(o+1, 200)        (a,k3) b = min(o+3, 200)      (a,0.05) b = min(o50+1, 200)
  (b)      a = o-2, b = o+1 (oracle: uses the real o)   (b,fix) a = m+106, b = min(o+1, 200) when o >= m+106 (else no trade)
  (c)      a = m+2, b = 160 / 200
Also: the simulator check (the launcher's own first buy re-simulated by amount from the synced state vs the real token output)."""
import sys, os, time, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from scommon import *
from s04_shapes import line_shape
from replay import replay, V3Sim, ETH_USD, GAS_USD
D, R = load(); S1 = json.load(open(os.path.join(OUT, "s01_launches.json"))); TH = S1["t_head"]
LR = [r for r in R if line_shape(r)]
QS = {"$15": 0.0058, "$5": 0.00195}
def obj(r): return {"lb": r["lb"], "ev": r["ev"], "ev_to": r["ev_to"]}
def row(r): return {"dex": "v3", "quote_side": r["qs"], "fee": r["fee"]}
def plans(r):
    m = r["mints"][0]["off"]; o = r["own1"]["off"] if r["own1"] else None
    o50 = next((s["off"] for s in r["own"] if s["eth"] >= 0.045), None)
    a = m + 2
    rb = next((s["off"] for s in r["swaps"] if s["dir"] == "B" and s["eth"] >= 0.005 and s["off"] >= a), None)
    P = {"census (frb+1, cap 60)": (a, min(rb + 1, 60) if rb is not None else 60),
         "(a) own+1 cap 200": (a, min(o + 1, 200) if o is not None and o >= a else 200),
         "(a,k3) own+3 cap 200": (a, min(o + 3, 200) if o is not None and o >= a else 200),
         "(a,0.05) own>=0.045 +1 cap 200": (a, min(o50 + 1, 200) if o50 is not None and o50 >= a else 200),
         "(b) oracle own-2 -> own+1": (o - 2, o + 1) if o is not None else None,
         "(b,fix) m+106 -> own+1 cap 200": (m + 106, min(o + 1, 200)) if o is not None and o >= m + 106 else None,
         "(c) fixed +160": (a, 160), "(c) fixed +200": (a, 200)}
    return P
def sim_check(r):
    o = r["own1"]
    if not o: return None
    sim = V3Sim(r["qs"], r["fee"])
    for e in r["ev"]:
        if e is o["e"]: break
        sim.apply(e)
    out = sim.buy(int(round(o["eth"] * 1e18)))
    return out / o["tok"] - 1
WIN = [("last 6 h", lambda r: TH - r["ts"] <= 6 * 3600), ("last 24 h", lambda r: TH - r["ts"] <= 24 * 3600), ("last 48 h", lambda r: TH - r["ts"] <= 48 * 3600),
       ("late timing (own buy >= +100, n=4)", lambda r: r["own1"] and r["own1"]["off"] >= 100),
       ("48 h, own first buy 0.05", lambda r: TH - r["ts"] <= 48 * 3600 and r["own1"] and r["own1"]["eth"] >= 0.045),
       ("48 h, own first buy < 0.05", lambda r: TH - r["ts"] <= 48 * 3600 and r["own1"] and r["own1"]["eth"] < 0.045)]
if __name__ == "__main__":
    out = []
    def P(s=""): out.append(s)
    chk = [x for x in (sim_check(r) for r in LR) if x is not None]
    P(f"simulator check, the launcher's own first buy re-simulated by amount: n {len(chk)}, |rel. error| max {max(abs(x) for x in chk):.2e}")
    res = {}
    for r in LR:
        for name, ab in plans(r).items():
            if ab is None: continue
            for ql, q in QS.items():
                x = replay(row(r), obj(r), ab[0], ab[1], q)
                if x["ok"]: res[(r["pool"], name, ql)] = dict(x, a=ab[0], b=ab[1])
    names = list(plans(LR[-1]).keys())
    for wl, wf in WIN:
        xs = [r for r in LR if wf(r)]
        days = {"last 6 h": 0.25, "last 24 h": 1.0, "last 48 h": 2.0}.get(wl, 2.0 if wl.startswith("48") else None)
        P(f"\n=== {wl}: {len(xs)} launches" + (f" ({len(xs) / days:.1f}/day)" if days else ""))
        for name in names:
            for ql in QS:
                ys = [res[(r["pool"], name, ql)] for r in xs if (r["pool"], name, ql) in res]
                if not ys: continue
                rets = [y["ret"] for y in ys]; usd = [y["usd"] for y in ys]
                pdays = f" $/day {st.mean(usd) * len(ys) / days:+.2f}" if days else ""
                P(f"  {name:34s} {ql:3s}: n {len(ys)}/{len(xs)} mean {st.mean(rets) * 100:+.1f}% med {st.median(rets) * 100:+.1f}% win {sum(v > 0 for v in rets) / len(rets):.2f} "
                  f"worst {min(rets) * 100:+.1f}% pulled {sum(y['pulled'] for y in ys)} $/trade {st.mean(usd):+.3f}{pdays}  hold a..b med {st.median([y['a'] for y in ys]):.0f}..{st.median([y['b'] for y in ys]):.0f}")
    P("\n=== per launch, last 30 h (ret % at $15 / $5; pulled flag)")
    for r in LR:
        if TH - r["ts"] > 30 * 3600: continue
        s = f"  {r['lb']} {time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))} own1 {('%.3f@+%d' % (r['own1']['eth'], r['own1']['off'])) if r['own1'] else '-'} mint +{r['mints'][0]['off']}:"
        for name in names:
            a = res.get((r["pool"], name, "$15")); b = res.get((r["pool"], name, "$5"))
            if a: s += f" | {name.split(' ')[0]}{name.split(' ')[1] if name.startswith('(c)') else ''} [{a['a']},{a['b']}) {a['ret'] * 100:+.1f}/{b['ret'] * 100:+.1f}{' PULLED' if a['pulled'] else ''}"
        P(s)
    open(os.path.join(OUT, "s06_replay.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
