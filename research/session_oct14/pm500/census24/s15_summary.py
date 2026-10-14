"""Step 15: per-pool summary (parameter set, ETH and tokens added, the range, the pull, fleet and outside flows) and per-hour counts."""
import collections, datetime, statistics
from common import *
from v4sim import sqrt_at_tick, Q96
pools = load_pools()
def amounts(s, tl, tu, L):
    sa, sb = sqrt_at_tick(tl), sqrt_at_tick(tu)
    if s <= sa: return L * (sb - sa) * Q96 // (sa * sb), 0
    if s >= sb: return 0, L * (sb - sa) // Q96
    return L * (sb - s) * Q96 // (s * sb), L * (s - sa) // Q96
rows = []
for p in pools:
    e0, t0 = amounts(p["sqrt0"], p["tl"], p["tu"], p["liq"])
    last = [s for s in p["swaps"]]
    s_end = last[-1]["sqrt"] if last else p["sqrt0"]
    e1, t1 = amounts(s_end, p["tl"], p["tu"], p["liq"])
    fl = [s for s in p["swaps"] if s["k"] == "fleet"]; ot = [s for s in p["swaps"] if s["k"] in ("other", "r57", "sentinel")]
    fnet = sum(-s["a0"] for s in fl) / 1e18; onet = sum(-s["a0"] for s in ot) / 1e18
    obig = [s for s in p["swaps"] if s["k"] == "other" and s["a0"] < 0 and -s["a0"] >= 3e14]
    rows.append(dict(pid=p["pid"], L=p["L"], hour=datetime.datetime.fromtimestamp(p["ts"], datetime.UTC).strftime("%m-%d %H"), tick0=p["tick0"],
                     range=f"{p['tl']}..{p['tu']}", liq=p["liq"], add_eth=p.get("add_value", 0) / 1e18, add_eth_calc=e0 / 1e18, add_tok=t0 / 1e18,
                     add_off=p["add_off"], T=p["T"], pull=p.get("pull_off"), pull_by_launcher=p.get("pull_from") == p["launcher"],
                     eth_at_pull=e1 / 1e18, fleet_net_in=fnet, outside_net_in=onet, outside_buy=bool(obig),
                     first_out=(obig[0]["o"] if obig else None)))
jdump(rows, "s15_pools.json")
print("parameter sets (tick0, range, L, ETH added, tokens added):")
for k, n in collections.Counter((r["tick0"], r["range"], r["liq"], r["add_eth"], round(r["add_tok"] / 1e9, 3)) for r in rows).most_common():
    print("  ", k, "tokens (bn)", n)
print("ETH value sent with the add vs needed:", collections.Counter((r["add_eth"], round(r["add_eth_calc"], 4)) for r in rows).most_common())
print("pulled by the launcher:", sum(r["pull_by_launcher"] for r in rows), "of", sum(r["pull"] is not None for r in rows))
pl = sorted(r["pull"] for r in rows if r["pull"] is not None)
print("pull offset p10/50/90", pl[len(pl)//10], pl[len(pl)//2], pl[9*len(pl)//10], "min", pl[:3], "max", pl[-1])
for grp, sel in (("with an outside buy >= 0.0003", [r for r in rows if r["outside_buy"]]), ("without", [r for r in rows if not r["outside_buy"]])):
    pl = sorted(r["pull"] for r in sel if r["pull"] is not None)
    print(f"  {grp}: {len(sel)} pools, pull offset p10/50/90 {pl[len(pl)//10]}/{pl[len(pl)//2]}/{pl[9*len(pl)//10]}")
print("outside net ETH in per pool (sum):", round(sum(r["outside_net_in"] for r in rows), 4), "| fleet net ETH in (sum):", round(sum(r["fleet_net_in"] for r in rows), 3))
print("\nper hour: launches, with fleet T, pools with an outside buy >= 0.0003 ETH, median fleet ETH by +600 (s08)")
fp = {x["pid"]: x for x in jload("s08_fleet_pools.json")}
for h in sorted({r["hour"] for r in rows}):
    sel = [r for r in rows if r["hour"] == h]
    e6 = sorted(fp[r["pid"]]["ein600"] for r in sel)
    print(f"  {h}: {len(sel)} launches, T {sum(r['T'] is not None for r in sel)}, outside {sum(r['outside_buy'] for r in sel)}, fleet ETH by +600 median {e6[len(e6)//2]:.3f}")
