"""Judge 2, step 8: trigger max_blocks grid for hold 25 / 30 (mix and base scenarios, 50,000 bootstrap resamples, two seeds), and the
pulls of the replay's fills by T offset band (where the early pulls sit)."""
from j03_tables import *
if __name__ == "__main__":
    for mb in (100, 110, 120, 150, 200, 400):
        for name, rows in regimes(R, mb).items():
            if name.startswith("held"): continue
            for e in ("hold 25", "hold 30"):
                s = []
                for sc in ("2|2", "mix"):
                    v = [per_pool(r, e, sc) for r in rows]
                    lo1, hi1 = boot(v, 50000, 7); lo2, hi2 = boot(v, 50000, 99)
                    s.append(f"{sc}: {sum(v) / len(v):+.3f} [{lo1:+.3f}/{lo2:+.3f}, {hi1:+.3f}/{hi2:+.3f}]")
                print(f"mb {mb:3d} {name[:13]:13s} n {len(rows):3d} {e}: " + " | ".join(s))
    print("\nwhere the replay's pulls before landing + 60 blocks sit (hold 30 landing at buy+32): pools pulled within buy+92, by T band")
    for lo, hi in ((0, 100), (101, 150), (151, 250), (251, 400)):
        rr = [r for r in R if lo <= r["T"] <= hi]
        f = [r for r in rr if r["sc"]["2|2"]["fill"]]
        near = [(r["pid"][:10], r["sc"]["2|2"]["pull_after_buy"]) for r in f if r["sc"]["2|2"]["pull_after_buy"] is not None and r["sc"]["2|2"]["pull_after_buy"] <= 92]
        allp = [(r["pid"][:10], r["T"], (r["pull"] - r["T"]) if r["pull"] is not None else None) for r in rr if r["pull"] is not None and r["pull"] - r["T"] <= 94]
        print(f"   T {lo}-{hi}: pools {len(rr)}, fills {len(f)}; fills pulled within buy+92: {near}; any pool pulled within T+94: {allp}")
