#!/usr/bin/env python3
"""solsize.py DAYS LO HI OUT.json: census.py on a budget, for one pool size. Every Raydium CPMM / AMM v4 creation of the last DAYS is parsed
(one getTransaction each), and only the pools whose SOL side is LO-HI SOL get the creator profile (signature count, first funder) and the
pull check (LP-mint moves after creation, SOL vault now). Built for the public endpoints, which refuse census.py's full run: one shared gap
of GAP seconds (env, default 0.8) between calls. Output in census.py's format, so lines.py / linescan.py read it. Read-only."""
import json, os, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C

C.GAP = float(os.environ.get("GAP", "0.8"))
if not C.HELIUS:                                   # api.mainnet-beta refuses getTransaction at this pace; publicnode serves it
    C.U = ["https://solana-rpc.publicnode.com"]
_rpc = C.rpc


def _patient(m, p):
    """publicnode refuses in bursts (403) for a minute or two: wait it out instead of skipping the item"""
    for k in range(12):
        try:
            return _rpc(m, p)
        except RuntimeError:
            time.sleep(30)
    return _rpc(m, p)


C.rpc = _patient


def main(days, lo, hi, out):
    t0 = int(time.time() - days * 86400); recs = []
    for kind, (prog, fee) in C.PROG.items():
        sigs = [s["signature"] for s in C.sigs_since(fee, t0) if not s["err"]]
        print(f"{kind}: {len(sigs)} creations in {days:g} days", flush=True)
        with cf.ThreadPoolExecutor(2) as ex:
            for n, r in enumerate(ex.map(lambda s: C.safe(C.parse, "parse")(kind, s), sigs)):
                if r:
                    recs.append(r)
                if n % 100 == 0:
                    print(f"  {kind} parsed {n}/{len(sigs)}", flush=True)
    sized = [r for r in recs if r.get("sol") and lo <= r["sol"] <= hi]
    print(f"pools with a SOL side: {sum(1 for r in recs if r.get('sol'))} of {len(recs)}; {len(sized)} of {lo:g}-{hi:g} SOL", flush=True)
    for r in sized:
        r.update((C.safe(C.creator_profile, "creator")(r["creator"]) or (None, {}))[1])
        sp = C.safe(C.pull_info, "pull")(r)
        if sp:
            r.update(sp[1])
    json.dump({"t0": t0, "days": days, "lo": lo, "hi": hi, "pools": recs, "failed": dict(C.FAILED)}, open(out, "w"))
    print("lookups that kept failing (items skipped):", dict(C.FAILED) or "none", flush=True)
    print("done ->", out, flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
