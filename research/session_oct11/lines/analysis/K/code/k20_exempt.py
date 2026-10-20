"""are the early buys without the surcharge X made by the addresses named in the create tx's E events (an allowlist)?"""
import json, collections, sys
from kload import *
C = load_creates(); ce = {k: v for k, v in C.items() if v["quote"] == 0}
T = load_trades(set(ce), int(sys.argv[1]) if len(sys.argv) > 1 else None)
cnt = collections.Counter(); nE = collections.Counter()
for c, ev in T.items():
    cr = ce[c]; Es = {r[5][0] for r in ev if r[4] == "E" and r[2] == cr["tx"]}; xs = {r[2] for r in ev if r[4] == "X"}
    nE[min(len(Es), 15)] += 1
    for r in ev:
        if r[4] != "B" or r[2] == cr["tx"]: continue
        dt = r[0] - cr["bn"]
        if not 1 <= dt <= 30: continue
        inE = r[5][1] in Es or r[5][0] in Es
        cnt[("X" if r[2] in xs else "noX", "listed" if inE else "not-listed", "dt<=10" if dt <= 10 else "dt11-30")] += 1
for k, v in sorted(cnt.items()): print(v, k)
print("E addresses per curve", sorted(nE.items()))
