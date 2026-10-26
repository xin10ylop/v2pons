#!/usr/bin/env python3
"""run_days.py CHAIN FIRST_DAY LAST_DAY [PARALLEL] [HOURS]: census.py then roundtrips.py for each UTC day (or each HOURS-long slice),
into out/CHAIN_YYYYMMDD_HH.json and out/rt_CHAIN_YYYYMMDD_HH.json, skipping slices already done. Logs to out/run_CHAIN.log."""
import sys, os, subprocess, datetime as dt, concurrent.futures as cf

ch, d0, d1 = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3])
par = int(sys.argv[4]) if len(sys.argv) > 4 else 3
hours = int(sys.argv[5]) if len(sys.argv) > 5 else 24
here = os.path.dirname(os.path.abspath(__file__)); log = open(os.path.join(here, f"out/run_{ch}.log"), "a")
slices = []
d = d0
while d <= d1:
    for h in range(0, 24, hours):
        s = dt.datetime(d.year, d.month, d.day, h); e = s + dt.timedelta(hours=hours)
        slices.append((s, e))
    d += dt.timedelta(days=1)


def one(se):
    s, e = se; tag = f"{ch}_{s:%Y%m%d_%H}"
    c, r = os.path.join(here, f"out/{tag}.json"), os.path.join(here, f"out/rt_{tag}.json")
    for cmd, f in ((["python3", "census.py", ch, f"{s:%Y-%m-%d %H:%M}", f"{e:%Y-%m-%d %H:%M}", c], c), (["python3", "roundtrips.py", c, r], r)):
        if os.path.exists(f):
            continue
        p = subprocess.run(cmd, cwd=here, capture_output=True, text=True, timeout=7200)
        log.write(f"== {tag} {cmd[1]} rc {p.returncode}\n{p.stdout[-6000:]}{p.stderr[-1500:]}\n"); log.flush()
        if p.returncode:
            return tag, "failed " + cmd[1]
    return tag, "ok"


with cf.ThreadPoolExecutor(par) as ex:
    for tag, st in ex.map(one, slices):
        print(tag, st, flush=True)
