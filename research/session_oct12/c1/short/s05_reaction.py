"""Could the operator simply react faster? (offline, s02_pools.json). Every position held into the pull: our 5 fills and every outside buy of
>= 0.001 ETH (recurring or one-off wallets) whose buyer had not sold before the pull, in a pool pulled within 600 blocks of that buy. For each:
the lag from the buy to the router's last buy before the pull (the router 'stopping'; negative: it had already stopped) and to the pull, also
measured from T+2 (our entry) and from the launch. Plus the earliest pulls of all usable triggered pools, from T and from the launch."""
from groups import *
import collections
D = load(); P = D["pools"]
ev = []
for p in P:
    if p["pull"] is None: continue
    pb = p["pullpos"]
    rb = [s for s in p["sw"] if s["buy"] and s["cls"] == "router" and (s["bn"], s["li"]) < tuple(pb)]
    last_rb = rb[-1] if rb else None
    seen = set()
    for s in p["sw"]:
        if (s["bn"], s["li"]) >= tuple(pb): break
        if not s["buy"]: continue
        who = s.get("from")
        if s["cls"] == "ours": who = "ours"
        elif not (s["cls"] in OUT and s["eth"] >= 0.001): continue
        if (who, p["pid"]) in seen: continue
        sold = any(not x["buy"] and (x.get("from") == s.get("from") or (who == "ours" and x["cls"] == "ours")) and (s["bn"], s["li"]) < (x["bn"], x["li"]) < tuple(pb) for x in p["sw"])
        if sold: continue
        seen.add((who, p["pid"]))
        lagp = pb[0] - s["bn"]
        if lagp > 600: continue
        ev.append({"pid": p["pid"][:10], "ts": p["ts"], "who": who[:10], "eth": round(s["eth"], 5), "buy_T": None if p["T"] is None else s["off"] - p["T"], "buy_L": s["off"],
                   "stop_lag": None if last_rb is None else last_rb["bn"] - s["bn"], "pull_lag": lagp, "pull_T": None if p["T"] is None else p["pull"] - p["T"],
                   "pull_L": p["pull"], "stop_to_pull": None if last_rb is None else pb[0] - last_rb["bn"], "router_buys_after": sum(1 for x in rb if (x["bn"], x["li"]) > (s["bn"], s["li"]))})
ev.sort(key=lambda e: e["pull_lag"])
print(f"positions of >= 0.001 ETH (or ours) held into a pull that came within 600 blocks of the buy: {len(ev)}")
print("  when (UTC)      pool       buyer      ETH      buy@T+  buy@L+ | router's last buy @buy+  pull @buy+  pull @T+  pull @L+  last-buy->pull  router buys after")
for e in ev:
    print(f"  {utc(e['ts'])} {e['pid']} {e['who']:10s} {e['eth']:.5f} {str(e['buy_T']):>7s} {e['buy_L']:6d} | {str(e['stop_lag']):>22s} {e['pull_lag']:11d} {str(e['pull_T']):>9s} {e['pull_L']:9d} {str(e['stop_to_pull']):>15s} {e['router_buys_after']:6d}")
def mn(k, f=lambda e: True):
    v = [e[k] for e in ev if f(e) and e[k] is not None]; return (min(v), sorted(v)[len(v) // 2], len(v)) if v else None
post = lambda e: e["buy_T"] is not None and e["buy_T"] >= 0
print(f"\nshortest lag, holder's buy -> pull: all {mn('pull_lag')}, bought at or after T {mn('pull_lag', post)}, ours {mn('pull_lag', lambda e: e['who'] == 'ours')}  (min, median, n)")
print(f"router's last buy relative to the holder's buy (where the router bought after it): {mn('stop_lag', lambda e: e['stop_lag'] is not None and e['stop_lag'] > 0)}; "
      f"router already stopped before the buy in {sum(1 for e in ev if e['stop_lag'] is not None and e['stop_lag'] <= 0)} of {len(ev)}")
print(f"router's last buy -> pull: {mn('stop_to_pull')}")
# the earliest pulls of all usable triggered pools (any reason)
U = [p for p in P if usable(p, D) is None or usable(p, D) == "pulled by T+2"]
pt = sorted((p["pull"] - p["T"], p["pull"], utc(p["ts"]), p["pid"][:10], classify(p)[0]) for p in P if p["T"] is not None and p["pull"] is not None)
print("\nthe 12 earliest pulls after T of all triggered pools (pull@T+, pull@L+, launch, pool, group):")
for x in pt[:12]: print("  ", x)
pl = sorted(p["pull"] for p in P if p["T"] is not None and p["pull"] is not None)
print(f"pull offsets from the launch, triggered pools: min {pl[0]}, p5 {pl[len(pl) // 20]}, p10 {pl[len(pl) // 10]}; pulls before launch+133: {sum(1 for x in pl if x < 133)}")
print("T offsets from the launch, triggered pools p10/50/90:", [sorted(p["T"] for p in P if p["T"] is not None)[int(q * sum(1 for p in P if p["T"] is not None))] for q in (.1, .5, .9)])
json.dump(ev, open(S("s05_reaction.json"), "w"))
