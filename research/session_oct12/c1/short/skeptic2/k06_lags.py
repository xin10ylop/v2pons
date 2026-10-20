"""Skeptic 2: the margin the short hold relies on, re-measured independently (offline, s02_pools.json data): every position of >= 0.001 ETH
(an outside wallet's, or ours) still held when its pool was pulled, bought at or after the engine's real trigger and no later than T+150
(a T+2-like entry, not a late buy on top of the normal pull): the lag from the buy to the router's last buy and to the pull. The hold's sell
lands at buy + hold + 1..3; it beats the reaction when that is under the pull."""
from sk import *
import k02_exec as KX
ev = []
for p in KX.P:
    if p["pullpos"] is None: continue
    pb = tuple(p["pullpos"])
    t = next((s for s in p["sw"] if s["buy"] and s.get("to") == ROUTER and (KX.seen_amount(s) or 0) >= KX.MIN_TRIG), None)
    if t is None: continue
    rb = [s for s in p["sw"] if s["buy"] and s.get("to") == ROUTER and (s["bn"], s["li"]) < pb]
    seen = set()
    for s in p["sw"]:
        if (s["bn"], s["li"]) >= pb: break
        if not s["buy"] or s["eth"] < 0.001 or s["cls"] not in ("recurring", "oneoff", "ours"): continue
        who = "ours" if s["cls"] == "ours" else s.get("from")
        if who in seen: continue
        if any(not x["buy"] and (x.get("from") == s.get("from") or (who == "ours" and x["cls"] == "ours")) and (s["bn"], s["li"]) < (x["bn"], x["li"]) < pb for x in p["sw"]): continue
        seen.add(who)
        off = s["off"] - t["off"]
        if off < 0 or off > 150: continue
        after = [x for x in rb if (x["bn"], x["li"]) > (s["bn"], s["li"])]
        ev.append((pb[0] - s["bn"], (after[-1]["bn"] - s["bn"]) if after else None, off, who[:10], p["pid"][:10], utc(p["ts"]), round(s["eth"], 4), t["off"], p["pull"]))
ev.sort()
print(f"held positions bought T+0..T+150 (the engine's trigger), pulled while held: {len(ev)}")
print("  pull@buy+  router's last buy@buy+  buy@T+  who        pool       launch          ETH     T   pull@L+")
for e in ev[:20]: print(f"  {e[0]:9d}  {str(e[1]):>21s}  {e[2]:6d}  {e[3]:10s} {e[4]} {e[5]} {e[6]:.4f} {e[7]:4d} {e[8]:5d}")
lag = [e[0] for e in ev]
for h in (20, 25, 30, 35, 40, 60):
    print(f"  hold {h}: the sell lands by buy+{h + 3}; positions pulled at or before that: {sum(1 for x in lag if x <= h + 3)} of {len(lag)}"
          f" (at buy+{h + 1}, lag 1: {sum(1 for x in lag if x <= h + 1)})")
