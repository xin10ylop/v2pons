"""(3) outsiders who sold before the crowd: does the crowd wait for an outside holder to leave? For each outside holder (>= 0.0005 ETH,
not the + 1 bot) that sold half its tokens before the crowd's first real buy, at age e: the crowd within 30 / 60 blocks after e, observed
against expected from every pool at risk at age e (no crowd yet, not pulled). Then every early (+ 1..+ 20) non-bot holder listed
(r07_cases.txt)."""
from rlib import *
P = load(); BOT1 = "0x776e5a2a"
def at_risk(e, N):
    at = [p for p in P if (p["frb"] is None or p["frb"] > e) and (p["pull"] is None or p["pull"] > e) and p["end"] >= min(e + N, p["pull"] or 10 ** 9)]
    return sum(1 for p in at if p["frb"] is not None and p["frb"] <= e + N) / len(at) if at else None, len(at)
for lab, sel in (("not the +1 bot", lambda o: not o["w"].startswith(BOT1)), ("the +1 bot", lambda o: o["w"].startswith(BOT1))):
    for N in (10, 30, 60):
        O = 0; Ex = 0.0; n = 0; lags = []
        for p in P:
            for o in p["outs"]:
                if not sel(o) or o["exit_off"] is None: continue
                e = o["exit_off"]
                if (p["frb"] is not None and p["frb"] <= e) or (p["pull"] is not None and p["pull"] <= e): continue
                if p["end"] < min(e + N, p["pull"] or 10 ** 9): continue
                r, _ = at_risk(e, N)
                if r is None: continue
                n += 1; Ex += r; hit = p["frb"] is not None and p["frb"] <= e + N; O += hit
                if p["frb"] is not None: lags.append(p["frb"] - e)
        print(f"{lab:<16} exits before the crowd {n:>4}: crowd within {N:>2} blocks after the exit: observed {O} expected {Ex:.1f} (O/E {O / Ex if Ex else float('nan'):.2f})"
              + (f"; lag exit -> crowd p10/50/90 {pct(lags,.1)}/{pct(lags,.5)}/{pct(lags,.9)}" if N == 30 else ""))
# holders vs sellers: offsets
print("\nnon-bot outside buyers with a first buy at + 1..+ 20 (>= 0.0005 ETH): held at the crowd / sold before / pool pulled first")
rows = []
for p in P:
    for o in p["outs"]:
        if o["w"].startswith(BOT1) or not 1 <= o["first_off"] <= 20: continue
        st = "held" if o["held_at_crowd"] else "sold"
        if p["frb"] is None: st += "/no crowd"
        rows.append((p, o, st))
import collections
print(" ", collections.Counter(st for _, _, st in rows))
for st in sorted({st for _, _, st in rows}):
    g = [(p, o) for p, o, s in rows if s == st]
    fr = [p["frb"] for p, o in g if p["frb"] is not None]; pl = [p["pull"] - o["first_off"] for p, o in g if p["pull"] is not None]
    ex = [o["exit_off"] - o["first_off"] for p, o in g if o["exit_off"] is not None]
    pin = sum(1 for p, o in g if p["pull"] is not None and p["pull"] <= p["sell"])
    print(f"  {st:<16} n {len(g):>4}: frb p25/50/75 {pct(fr,.25)}/{pct(fr,.5)}/{pct(fr,.75)}; its hold (buy -> half sold) p25/50/75 {pct(ex,.25)}/{pct(ex,.5)}/{pct(ex,.75)};"
          f" pull - its buy p10/50 {pct(pl,.1)}/{pct(pl,.5)}; pulled <= our sell {pin}")
with open(J("r07_cases.txt"), "w") as f:
    f.write("launch UTC | pool | wallet | first buy off | ETH pre-crowd | exit off (half sold) | frb | wave ETH | pull | our sell | state | eth in / out\n")
    for p, o, st in sorted(rows, key=lambda r: r[0]["lb"]):
        f.write(f"{utc(p['ts'])} {p['pool'][:10]} {o['w'][:10]} +{o['first_off']} {o['eth_pre']:.5f} {o['exit_off']} frb {p['frb']} wave {p['wave']:.3f} pull {p['pull']} sell {p['sell']} {st} "
                f"{o['eth_in']:.5f}/{o['eth_out']:.5f}\n")
print("cases ->", J("r07_cases.txt"))
