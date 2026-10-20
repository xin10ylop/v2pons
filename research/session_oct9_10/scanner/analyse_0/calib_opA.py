"""Calibration of the follow pricer on operator A (the live follow strategy's operator): every census pool labelled operator-A, the literal
follow rule (buy landing one block after the first buy >= 0.0002 ETH, sell one block after the next such buy or at our buy + 4), our relay's
real swaps removed. The live record (HANDOFF 3.1/10): about +2-4% a trade since Oct 9, none pulled before our sell after Oct 8."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = [p for p, r in P.items() if r["known"] == "operator-A"]
E = load_events(set(pids))
rs = []; rows = []
for pid in pids:
    pl = Pool(P[pid], E.get(pid), T, M)
    if pl.L0 <= 0: continue
    buys = pl.buys()
    fr = next((x for x in buys if x["eth"] >= MIN_REAL), None)
    if not fr: continue
    if fr["bn"] - pl.live_block > 150: continue                      # the engine's arming window
    B = fr["bn"] + 1
    nx = next((x for x in buys if x["bn"] > B and x["eth"] >= MIN_REAL), None)
    S = min(nx["bn"] + 1, B + 4) if nx else B + 4
    t = pl.trade(B, S); t["trig"] = fr["bn"] - pl.live_block; t["fee"] = pl.fee; t["relay_in"] = any(x["relay"] for x in pl.seq)
    rs.append(t); rows.append({"pid": pid, **{k: t.get(k) for k in ("exit", "ret", "B", "S", "trig", "fee", "relay_in")}})
s = summarize(rs)
print("operator A follow (literal):", json.dumps(s))
print("  with our relay in the pool:", json.dumps(summarize([r for r in rs if r["relay_in"]])))
print("  without:", json.dumps(summarize([r for r in rs if not r["relay_in"]])))
json.dump({"summary": s, "rows": rows}, open(os.path.join(HERE, "calib_opA.json"), "w"), indent=1, default=str)
