"""Step 6: check the integer simulator (v4sim.Pool) against every real swap up to the pull: start from the launch price and the
position added, apply each swap by its input, compare the output and the sqrt price with the event."""
from common import *
from v4sim import Pool
pools = load_pools()
fees = {(r['bn'], r['li']): swap_fields(r)['fee'] for r in load_events() if r['t'] == 'S'}
n = ok_out = ok_sqrt = 0; worst = 0; bad = []
for p in pools:
    if "add_bn" not in p: continue
    pool = Pool(p["sqrt0"], (p["tl"], p["tu"], p["liq"]), 500)
    for s in p["swaps"]:
        if s["bn"] < p["add_bn"]: continue
        pool.fee = fees[(s["bn"], s["li"])]
        if s["a0"] < 0:
            out = pool.buy(-s["a0"]); real = s["a1"]
        else:
            out = pool.sell(-s["a1"]); real = s["a0"]
        n += 1
        if out == real: ok_out += 1
        else:
            e = abs(out - real) / max(1, real); worst = max(worst, e)
            if e > 1e-9: bad.append((p["pid"][:10], s["o"], out, real))
        if pool.sqrt == s["sqrt"]: ok_sqrt += 1
        pool.sqrt = s["sqrt"]                  # resync on the event's state
        assert s["liq"] == p["liq"] or s["liq"] == 0, (s["liq"], p["liq"])
print(f"swaps {n}: exact output {ok_out} ({ok_out/n:.4%}), exact sqrt {ok_sqrt} ({ok_sqrt/n:.4%}), worst rel err {worst:.2e} (swap fee from each event: LP 500 ppm, 625 once a 125-pip protocol fee is switched on), >1e-9: {len(bad)}")
print(bad[:10])
