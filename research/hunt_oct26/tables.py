#!/usr/bin/env python3
"""tables.py CHAIN: the report's table for CHAIN from out/verdicts_CHAIN.json (run verdicts.py first): every line where anyone bought ahead of
the fleet or made real-size outside buys, with its verdict over all its days. Lines settled by the earlier reports are left out, except the
2.433 line (the control). Markdown on stdout."""
import sys, os, json, collections, statistics as st
from verdicts import KNOWN, line_verdict

ch = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(here, f"out/verdicts_{ch}.json")))
by = collections.defaultdict(list)
for r in rows:
    if r["known"] and "2.433" not in r["known"]:
        continue
    by[r["line"]].append(r)


def lv(rs):
    v = line_verdict(rs)
    s1 = [r["seat1"] for r in rs if r["seat1"] == r["seat1"]]
    neg = " (seat negative after fees)" if s1 and st.median(s1) <= 0 and v in ("FRONT-OPEN", "TOLERANT") else ""
    return {"FRONT-OPEN": "**FRONT-OPEN**", "TOLERANT": "tolerant (exits, no front evidence)"}.get(v, v.lower() if v in ("UNTESTED", "MIXED") else v) + neg


print("| line (venue, fee in ppm, tick spacing, launch size or route) | days | pools | verdict | real outside buys: sold / rugged | fronted pools: fleet came / none | paper seat after the fleet's 1st buy |")
print("|---|---|---|---|---|---|---|")
ORDER = {"FRONT-OPEN": 0, "TOLERANT": 1, "MIXED": 2, "UNTESTED": 3, "CLOSED": 4, "TRAP": 5}
for line, rs in sorted(by.items(), key=lambda kv: (ORDER[line_verdict(kv[1])], -sum(r["n"] for r in kv[1]))):
    rs = sorted(rs, key=lambda r: r["day"])
    s1 = [r["seat1"] for r in rs if r["seat1"] == r["seat1"]]
    if s1 and abs(st.median(s1)) > 10:                     # a pool of dust (1e-9 ETH) makes any buy a x1000: no meaningful seat
        s1 = []
    name = line.replace(" via ", " via `") + ("`" if " via " in line else "")
    if rs[0]["known"]:
        name += " (the 2.433 line)"
    days = f"{rs[0]['day'][4:6]}/{rs[0]['day'][6:8]}" + (f"-{rs[-1]['day'][4:6]}/{rs[-1]['day'][6:8]}" if rs[-1]["day"] != rs[0]["day"] else "") + f" ({len(rs)})"
    print(f"| {name} | {days} | {sum(r['n'] for r in rs):,} | {lv(rs)} | {sum(r['sold'] for r in rs)} / {sum(r['rugged'] for r in rs)} |"
          f" {sum(r['came'] for r in rs)} / {sum(r['none'] for r in rs)} | {st.median(s1):+.1%} |" if s1 else
          f"| {name} | {days} | {sum(r['n'] for r in rs):,} | {lv(rs)} | {sum(r['sold'] for r in rs)} / {sum(r['rugged'] for r in rs)} |"
          f" {sum(r['came'] for r in rs)} / {sum(r['none'] for r in rs)} | - |")
