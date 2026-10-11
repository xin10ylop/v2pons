"""replay helper: insert our buy into a curve's event history (exact curve math, others' trades re-applied on the modified state) and sell at exit."""
import pickle, json, collections, statistics as st
from kload import *
from kcurve import *
GAS_RT = 176000 * 0.0202e9 / 1e18     # buy ~100k + sell ~76k gas at ~0.0202 gwei (receipts)
USD = 2570.0

def cfee(ev):
    for r in ev:
        if r[3] == "B" and r[5][0] > 10**12: return r[5][3] / r[5][0]
        if r[3] == "S" and r[5][1] > 10**12: return r[5][3] / (r[5][1] + r[5][2] + r[5][3])
    return None

def state_at(ev, bn, cv=None):
    """curve after every event in blocks <= bn (the recorded history); returns (curve, index of the next event)"""
    cv = cv or Curve(); i = 0
    while i < len(ev) and ev[i][0] <= bn:
        cv.apply(ev[i]); i += 1
    return cv, i

def replay(ev, entry_bn, exit_bn, stake, surcharge, cf, exit_fn=None):
    """buy `stake` ETH after block entry_bn, sell everything after block exit_bn on the curve. Returns dict or None (curve already graduated)."""
    cv, i = state_at(ev, entry_bn)
    if cv.real() >= THR: return None
    net = int(stake * 1e18 * (1 - FEE - cf - surcharge)); tok = cv.y * net // (cv.x + net); cv.x += net; cv.y -= tok
    grad = False
    while i < len(ev) and ev[i][0] <= exit_bn:
        r = ev[i]; i += 1
        if r[3] in "BS":
            cv.apply_sim(r)
            if cv.real() >= THR: grad = True; break
    if grad:
        return {"grad": True, "tok": tok, "cv": cv}
    g = cv.x * tok // (cv.y + tok); eth = g * (1 - FEE - cf) / 1e18
    return {"grad": False, "ret": (eth - GAS_RT) / stake - 1, "eth_out": eth}

def stats(R, stake, days):
    if not R: return {"n": 0}
    v = sorted(R)
    return {"n": len(v), "mean": round(sum(v) / len(v), 4), "median": round(v[len(v) // 2], 4), "win": round(sum(1 for x in v if x > 0) / len(v), 3),
            "worst": round(v[0], 4), "best": round(v[-1], 4), "usd_per_day": round(sum(v) * stake * USD / days, 2), "per_day_n": round(len(v) / days, 1)}
