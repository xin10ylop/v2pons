#!/usr/bin/env python3
"""coverage.py: what the hunt read, per chain: the days, the native pools created, the pools pulled within 2 h, the round trips found and the
early ones, and the lines front.py tested. Read-only (reads out/ only)."""
import os, glob, json

here = os.path.dirname(os.path.abspath(__file__))
for ch in ("rh", "base"):
    cs = sorted(glob.glob(os.path.join(here, f"out/{ch}_2*_00.json")))
    created = pulled = 0
    for f in cs:
        r = json.load(open(f))["chains"][ch]; created += r["n_created"]; pulled += len(r["rugs"])
    rts = sorted(glob.glob(os.path.join(here, f"out/rt_{ch}_2*_00.json")))
    trips = early = 0
    for f in rts:
        d = json.load(open(f)); trips += d["n_trips"]; early += len(d["early"])
    fr = sorted(glob.glob(os.path.join(here, f"out/front_{ch}_2*_00.json")))
    lines = sum(len(json.load(open(f))["lines"]) for f in fr)
    days = [os.path.basename(f)[len(ch) + 1:len(ch) + 9] for f in cs]
    print(f"{ch}: {len(cs)} days ({days[0] if days else '-'}..{days[-1] if days else '-'}), {created:,} native pools created, {pulled:,} pulled within 2 h, "
          f"{trips:,} round trips ({early:,} entered within 20 s), {lines} line-days tested by front.py")
