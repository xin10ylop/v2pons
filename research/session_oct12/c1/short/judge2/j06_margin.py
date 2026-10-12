"""Judge 2, step 6 (our own 3 fills that sold before their pull are counted too, flagged): the margin from each exit's landing block to every known reaction pull.

Reaction pulls (the reaction clock): every position of >= 0.001 ETH (ours or an outsider's) still held when its pool was pulled, the pull
within 600 blocks of the buy, in the 208 cached pools (Oct 11 01:00 - Oct 12 14:14) and the 15 launches since 13:30 (j04, to 14:58).
Lag = pull block - buy block. A buy made after T + 150 is flagged "late" (it lands on a pull already on its schedule: the analyst's 3- and
23-block cases). Our exit lands at buy + H + lag (lag 1-2 seen, 3 stress), or buy + (tp send) + lag.
The pool-age clock: the earliest pull of a pool with a trigger, counted from its launch, against our landing at launch + T + 2 + H + lag.
And per filled replay trade (j02, max_blocks 400, T+2): the pull's distance from the landing block."""
from j05_shape_cmp import *

if __name__ == "__main__":
    R = json.load(open(JD("j02_sim.json")))["rows"]
    pools = [(p, "cache") for p in P] + [(build(x), "j04") for x in L4 if x["pid"] not in {q["pid"] for q in P}]
    rx = []
    for p, src in pools:
        if p["pullpos"] is None: continue
        pb = p["pullpos"][0]
        trig = engine_copy_L(p, p.get("L") or LIQ) if p["launch_sqrtP"] in (SQRTP, NEW_SP) else None
        T = trig[1]["off"] if trig else None
        for s in p["sw"]:
            if not (s["buy"] and s["cls"] in ("recurring", "oneoff", "ours") and s["eth"] >= 0.001): continue
            if (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
            sold_first = any((not y["buy"]) and y.get("from") == s.get("from") and (y["bn"], y["li"]) > (s["bn"], s["li"]) and (y["bn"], y["li"]) < tuple(p["pullpos"]) for y in p["sw"])
            if sold_first and s["cls"] != "ours": continue                     # ours: our sell landed first (buy+61/62), the pull still came 84-115 after our buy
            lag = pb - s["bn"]
            if lag > 600: continue
            rx.append({"pid": p["pid"][:10], "who": "OURS" if s["cls"] == "ours" else s["from"][:10], "eth": s["eth"], "lag": lag, "buy_T": None if T is None else s["off"] - T,
                       "pull_launch": p["pull"], "T": T, "late": T is not None and s["off"] - T > 150, "ts": p["ts"], "sold_first": sold_first})
    rx.sort(key=lambda r: r["lag"])
    print(f"(1) positions >= 0.001 ETH held into a pull within 600 blocks of the buy: {len(rx)} (in {len({r['pid'] for r in rx})} pools)")
    for r in rx[:30]:
        print(f"   lag {r['lag']:4d}  {r['who']:10s} {r['eth']:.4f} ETH  bought T{'' if r['buy_T'] is None else '%+d' % r['buy_T']:>6s}  pool {r['pid']} (T +{r['T']}, pulled at launch +{r['pull_launch']}){'  LATE' if r['late'] else ''}{'  (we sold first)' if r['sold_first'] else ''}  {utc(r['ts'])}")
    early = [r for r in rx if not r["late"]]
    print(f"   ... positions bought by T+150 (not late): {len(early)}; their 10 shortest lags: {[r['lag'] for r in early[:10]]}")
    # (2) the exits' landing against them
    print("\n(2) exit landing (blocks after our buy) and the margin to the fastest reaction on a position bought by T+150 (lag %d)" % early[0]["lag"])
    fast = early[0]["lag"]
    for H in (20, 25, 30, 35):
        for lag in (1, 2, 3):
            land = H + lag; hit = sum(r["lag"] <= land for r in early)
            print(f"   hold {H} lag {lag}: lands buy+{land}; margin to the fastest {fast - land:+d} blocks; reaction pulls at or before it: {hit} of {len(early)}")
    print("   tp 4%/6% cap 30: lands at the tp buy + lag, at most buy+31..33 (as hold 30); cap 40: at most buy+41..43, past the fastest (36)")
    # (3) the pool-age clock
    trig_pulls = []
    for p, src in pools:
        if p["launch_sqrtP"] not in (SQRTP, NEW_SP) or p["pull"] is None: continue
        trig = engine_copy_L(p, p.get("L") or LIQ)
        if trig is None: continue
        trig_pulls.append((p["pull"], trig[1]["off"], p["pid"][:10]))
    trig_pulls.sort()
    print(f"\n(3) pool-age clock: the earliest pulls of pools with an engine trigger (launch offset, T): {trig_pulls[:8]}")
    for mb in (100, 400):
        for H in (25, 30):
            print(f"   max_blocks {mb}, hold {H}: our sell lands by launch + {mb + 2 + H + 2} (T+2 buy, lag 2) / + {mb + 3 + H + 3} (T+3, lag 3)")
    t100 = [x for x in trig_pulls if x[1] <= 100]
    print(f"   pools with T <= 100: earliest pulls {t100[:6]}")
    # (4) per filled trade in the replay: the pull's distance from our landing
    print("\n(4) replay (j02, T+2): pull minus landing, smallest 8, per exit and max_blocks")
    for mb in (400, 100):
        for e in ("hold 20", "hold 25", "hold 30", "hold 35", "tp 4% cap 30", "tp 4% cap 40"):
            ds = []
            for r in R:
                if r["T"] > mb: continue
                x = r["sc"]["2|2"]
                if not x["fill"] or x["pull_after_buy"] is None: continue
                ds.append((x["pull_after_buy"] - x["res"][e][3], r["pid"][:10]))
            ds.sort()
            print(f"   max_blocks {mb} {e:13s}: fills with a pull {len(ds)}; pull - landing: {[d for d, _ in ds[:8]]}  (smallest in {ds[0][1]})")
    json.dump(rx, open(JD("j06_margin.json"), "w"))
