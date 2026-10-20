#!/usr/bin/env python3
"""The flip engine's log for the last N hours, rotations included, one JSON line per event (newest last).
    sudo python3 deploy/englog.py 3 | grep '"ev":"trade_done"'"""
import glob, gzip, json, sys, time
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 24; t_lo = time.time() - hours * 3600; base = "/var/log/flip/engine.jsonl"
files = sorted(glob.glob(base + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [base]
for f in files:
    try:
        for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
            try:
                if json.loads(line).get("t", 0) >= t_lo: sys.stdout.write(line)
            except Exception:
                pass
    except FileNotFoundError:
        pass
