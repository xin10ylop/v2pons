"""Sensitivity only (not from this window): if the operator answers our buy like the census outsiders >= 0.0002 ETH (25 of 26 pulled
within 15 blocks; lags of all outsider first-buys pulled within 15), a pull at B + lag <= S loses the stake."""
import json, statistics as st, numpy as np
L = np.array(json.load(open("../explore/chk/react_all.json"))["v2.433"]["lags"])
rows = json.load(open("replay.json"))
for case in ("fast", "slow"):
    ev = {r: [] for r in (0.25, 0.5, 25 / 26)}; ds = []
    for x in rows:
        t = x[case]; d = t["S"] - t["B"]; ds.append(d); P = float((L <= d).mean())
        for r in ev: ev[r].append((1 - r * P) * t["ret"] + r * P * (-1.0035))
    print(case, "exposure S-B", sorted(set(ds)), "P(lag<=d)", {d: round(float((L <= d).mean()), 3) for d in sorted(set(ds))},
          {f"r={r:.2f}": f"{100 * st.mean(v):+.1f}%" for r, v in ev.items()})
