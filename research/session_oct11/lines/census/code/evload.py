"""Per-pool events from cache/ev.jsonl, trimmed to [launch, launch + SPAN], deduplicated, sorted; plus normalised swap/liquidity views."""
from base import *


def load_events(keep=None):
    """pool -> {"kind", "lb", "ev_to", "ev": [...]} ; ev rows are the compact lists of f4_events.compact"""
    out = {}
    for g in jl_iter("ev.jsonl"):
        for i, b in g["launch"].items():
            if keep is not None and i not in keep: continue
            o = out.setdefault(i, {"kind": g["kind"], "lb": b, "ev_to": min(b + SPAN, g["b"]), "ev": {}})
            o["ev_to"] = max(o["ev_to"], min(b + SPAN, g["b"]))
        L = g["launch"]
        for e in g["ev"]:
            i = e[4]
            if i not in L or (keep is not None and i not in keep): continue
            if L[i] <= e[1] <= L[i] + SPAN: out[i]["ev"][(e[1], e[3])] = e
    for i, o in out.items(): o["ev"] = [o["ev"][k] for k in sorted(o["ev"])]
    return out


def norm(p, o):
    """-> swaps [{bn, ti, li, tx, buy, q (quote amount, abs, raw units), t (token amount, abs), router}], adds [...], pulls [...]
    v4: q/t from the swapper's deltas (negative = paid in); V2: in/out; V3: the pool's deltas (positive = into the pool)."""
    qs = p["quote_side"]; kind = o["kind"]; sw, adds, pulls = [], [], []
    for e in o["ev"]:
        if kind == "v4":
            if e[0] == "s":
                dq, dt = (e[6], e[7]) if qs == 0 else (e[7], e[6])
                sw.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[12], "buy": dq < 0, "q": abs(dq), "t": abs(dt), "router": e[5]})
            elif e[0] == "m":
                m = {"bn": e[1], "ti": e[2], "li": e[3], "tx": e[10], "L": abs(e[8]), "lo": e[6], "hi": e[7], "salt": e[9], "via": e[5]}
                (pulls if e[8] < 0 else adds if e[8] > 0 else []).append(m)
        elif kind == "v2":
            if e[0] == "s":
                qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
                buy = qin > 0 and tout > 0
                sw.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[11], "buy": buy, "q": qin if buy else qout, "t": tout if buy else tin, "router": e[5]})
            elif e[0] == "mi":
                adds.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[8], "q": e[6] if qs == 0 else e[7], "via": e[5]})
            elif e[0] == "b":
                pulls.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[9], "q": e[6] if qs == 0 else e[7], "via": e[5]})
        else:
            if e[0] == "s":
                dq, dt = (e[7], e[8]) if qs == 0 else (e[8], e[7])
                sw.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[12], "buy": dq > 0, "q": abs(dq), "t": abs(dt), "router": e[5]})
            elif e[0] == "mi":
                adds.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[11], "L": e[8], "lo": e[6], "hi": e[7], "via": e[5]})
            elif e[0] == "b" and e[8] > 0:
                pulls.append({"bn": e[1], "ti": e[2], "li": e[3], "tx": e[11], "L": e[8], "lo": e[6], "hi": e[7], "via": e[5]})
    return sw, adds, pulls
