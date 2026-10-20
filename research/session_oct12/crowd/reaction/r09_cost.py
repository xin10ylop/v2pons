"""(5) what the measured cases cost a $5 trade: the rule's return per group (r05_groups.json; analyst C's replay at 0.0012 ETH, buy + 2,
sell min(trigger + 20, + 80)) with bootstrap CIs; the pull-inside-the-hold rate with Wilson and exact upper bounds; and the scenarios:
no reaction (the group's own mean), 'the crowd stops when we hold' (sell at + 80 into no wave), and 'pulled inside the hold' at the
measured upper bound. ETH_USD from the environment (r10_ethusd.out); gas per round trip GAS_USD."""
from rlib import *
ETH_USD = float(os.environ.get("ETH_USD", "2527")); GAS = float(os.environ.get("GAS_USD", "0.022")); STAKE = 5.0
BOT1 = "0x776e5a2a"
G = json.load(open(J("r05_groups.json")))
SINCE = os.environ.get("SINCE")          # e.g. 2026-10-08: only launches from that UTC day on
if SINCE:
    import calendar
    G = [p for p in G if p["ts"] >= calendar.timegm(time.strptime(SINCE, "%Y-%m-%d"))]
    print(f"launches from {SINCE} UTC on: {len(G)} pools")
def grp(lab, ps):
    rs = [p["ret"] for p in ps if p["ret"] is not None]; n = len(ps)
    if not rs: print(f"  {lab}: none"); return
    m = sum(rs) / len(rs); lo, hi = boot_mean_ci(rs); pb = sum(1 for p in ps if p["pulled_hold"])
    nocrowd = [p["ret"] for p in ps if p["ret"] is not None and (p["trig"] is None or p["trig"] > 60)]
    wl, wh = wilson(pb, n); cu = cp_upper(pb, n)
    top = sorted(rs, reverse=True); k = max(1, len(rs) // 10); share = sum(top[:k]) / sum(rs) if sum(rs) > 0 else float("nan")
    print(f"  {lab:<44} n {n:>4}  mean {m*100:+6.2f}% (95% {lo*100:+.2f}..{hi*100:+.2f})  median {pct(rs,.5)*100:+.2f}%  top10% share {share:.0%}  "
          f"$ per $5 trade {m*STAKE-GAS:+.3f} ({lo*STAKE-GAS:+.3f}..{hi*STAKE-GAS:+.3f})  pulled<=sell {pb}/{n} (Wilson {wl:.1%}-{wh:.1%}, exact 95% upper {cu:.1%})"
          f"  no trigger by +60: {len(nocrowd)} mean {sum(nocrowd)/max(1,len(nocrowd))*100:+.2f}%")
    return m, cu
print(f"ETH ${ETH_USD:,.0f}: $5 = {STAKE/ETH_USD:.5f} ETH; gas per round trip ${GAS}")
none = [p for p in G if not p["outs"]]
early = lambda p, f: [o for o in p["outs"] if 1 <= o["first_off"] <= 10 and f(o)]
grp("all pools", G)
grp("no outside buyer before the crowd", none)
grp("+1..+10 non-bot holder", [p for p in G if early(p, lambda o: not o["w"].startswith(BOT1) and o["held_at_crowd"])])
grp("+1..+10 non-bot holder >= 0.001 ETH", [p for p in G if early(p, lambda o: not o["w"].startswith(BOT1) and o["held_at_crowd"] and o["eth_pre"] >= 0.001)])
grp("+1 bot holding (no other early buyer)", [p for p in G if early(p, lambda o: o["w"].startswith(BOT1)) and not early(p, lambda o: not o["w"].startswith(BOT1))])
grp("any non-bot outside buyer before the crowd", [p for p in G if any(not o["w"].startswith(BOT1) for o in p["outs"])])
# scenarios for one $5 trade (stake STAKE/ETH_USD ETH), from the measured groups
print("\nscenarios per $5 trade:")
allr = [p["ret"] for p in G if p["ret"] is not None]
nocrowd = [p["ret"] for p in G if p["ret"] is not None and (p["trig"] is None or p["trig"] > 80)]
m_all = sum(allr) / len(allr); m_nc = sum(nocrowd) / max(1, len(nocrowd))
print(f"  no reaction (all pools, the dry-run's situation): {m_all*100:+.2f}% -> ${m_all*STAKE-GAS:+.3f}")
print(f"  'the crowd never comes while we hold' (every trade sells at + 80 into no wave; measured on pools with no trigger by + 80): {m_nc*100:+.3f}% -> ${m_nc*STAKE-GAS:+.3f}")
for lab, k, n in (("pulled inside the hold, all pools", sum(1 for p in G if p["pulled_hold"]), len(G)),):
    print(f"  {lab}: {k}/{n}; exact one-sided 95% upper {cp_upper(k, n):.2%} -> expected cost at that rate ${cp_upper(k, n)*STAKE:.3f} a trade")
# the reaction at the cap: in the pools with no crowd trigger by + 60 (our sell is the cap's, at + 80), the pull's offset when an outside
# holder of our size sits in the pool from + 1..+ 10 (as we would) against pools with no outside holder at all; what a sell landing m
# blocks after + 80 would lose
print("\nthe cap's margin: pools with no trigger by + 60 (our sell = the cap's, lands + 80 when on time)")
cap = [p for p in G if (p["trig"] is None or p["trig"] > 60) and (p["end"] >= 120 or p["pull"] is not None)]
def hold80(p, f): return [o for o in p["outs"] if f(o) and o["first_off"] <= 78 and (o["exit_off"] is None or o["exit_off"] > 80)]
share_cap = len([p for p in G if p["trig"] is None or p["trig"] > 60]) / len(G)
for lab, f in (("non-bot holder >= 0.001 ETH in since +1..+10 (our analog)", lambda o: not o["w"].startswith(BOT1) and o["first_off"] <= 10 and o["eth_pre"] >= 0.001),
               ("non-bot holder in since +1..+10", lambda o: not o["w"].startswith(BOT1) and o["first_off"] <= 10),
               ("non-bot holder >= 0.001 ETH (any entry by +78)", lambda o: not o["w"].startswith(BOT1) and o["eth_pre"] >= 0.001),
               ("any outside holder", lambda o: True)):
    a = [p for p in cap if hold80(p, f)]; b = [p for p in cap if not hold80(p, lambda o: True)]
    row = []
    for m in (0, 2, 3, 5, 10, 20):
        ka = sum(1 for p in a if p["pull"] is not None and p["pull"] <= 80 + m); kb = sum(1 for p in b if p["pull"] is not None and p["pull"] <= 80 + m)
        row.append(f"+{80+m}: {ka}/{len(a)} ({ka/max(1,len(a)):.1%}, up {cp_upper(ka, len(a)):.1%}) vs {kb}/{len(b)}; ${share_cap * ka / max(1, len(a)) * STAKE:.3f} (up ${share_cap * cp_upper(ka, len(a)) * STAKE:.3f})")
    print(f"  {lab}:\n     " + "\n     ".join(row))
print(f"  (share of trades whose sell is the cap's: {share_cap:.0%}; $ = that share x the pull rate x $5, a trade's expected loss to the reaction for a sell landing at that block)")
