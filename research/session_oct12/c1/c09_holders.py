"""Position-based or address-based? (offline, c05). Every non-dust (>= 0.001 ETH) outside buy in (T, T+100] and every one of ours: the buyer's
own sell in the pool (same tx sender or the same Swap sender for ours) and its block, i.e. whether it still held when the pull came; the router's
buying after that buy; pull - T. Also every wallet's pools ranked."""
from common import *
D = json.load(open(J("c05_pools.json"))); P = D["pools"]
TP = [p for p in P if p["T"] is not None]
OUT = ("recurring", "oneoff")
rows = []
for p in TP:
    for s in p["sw"]:
        if not s["buy"] or (s["bn"], s["li"]) <= tuple(p["Tpos"]): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        if s["off"] - p["T"] > 100: continue
        if not ((s["cls"] in OUT and s["eth"] >= 0.001) or s["cls"] == "ours"): continue
        who = s.get("from"); sells = [x for x in p["sw"] if not x["buy"] and x.get("from") == who and (x["bn"], x["li"]) > (s["bn"], s["li"])]
        sold = sells[0]["off"] if sells else None
        rb_after = [x for x in p["sw"] if x["buy"] and x["cls"] == "router" and x["off"] > s["off"] and (p["pull"] is None or x["off"] < p["pull"])]
        rows.append((p["ts"], p["pid"][:12], p["T"], s["off"] - p["T"], round(s["eth"], 5), s["cls"], who[:10], None if sold is None else sold - s["off"],
                     None if p["pull"] is None else p["pull"] - s["off"], None if p["pull"] is None else p["pull"] - p["T"], len(rb_after),
                     (rb_after[0]["off"] - s["off"]) if rb_after else None, round(sum(x["eth"] for x in rb_after if x["off"] <= s["off"] + 60), 3)))
print("ts             pool          T   buy@T+  ETH      class      buyer      sold@buy+ pull@buy+ pull@T+ router-buys-after first@buy+ routerETH(buy..+60)")
for r in sorted(rows):
    print(f"{utc(r[0])} {r[1]} {r[2]:4d} {r[3]:5d} {r[4]:.5f} {r[5]:10s} {r[6]} {str(r[7]):>8s} {str(r[8]):>8s} {str(r[9]):>7s} {r[10]:5d} {str(r[11]):>6s} {r[12]:.3f}")
held = [r for r in rows if r[5] != "ours" and (r[7] is None or (r[8] is not None and r[7] > r[8]) or r[7] > 62)]
print(f"\noutsiders (non-dust, buy in T..T+100): {sum(1 for r in rows if r[5] != 'ours')}; still holding 62 blocks later (or at the pull): {len(held)};"
      f" of those pulled within 62 of the buy {sum(1 for r in held if r[8] is not None and r[8] <= 62)}, within 120 {sum(1 for r in held if r[8] is not None and r[8] <= 120)}, within 200 {sum(1 for r in held if r[8] is not None and r[8] <= 200)}")
quick = [r for r in rows if r[5] != "ours" and r not in held]
print(f"outsiders who sold within 62 blocks: {len(quick)}; pulled within 62 {sum(1 for r in quick if r[8] is not None and r[8] <= 62)}, within 120 {sum(1 for r in quick if r[8] is not None and r[8] <= 120)}, within 200 {sum(1 for r in quick if r[8] is not None and r[8] <= 200)}")
