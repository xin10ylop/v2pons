"""load.load() (Oct 8 00:00 -> Oct 9 11:19) plus react9b_data.json (Oct 9 11:19 -> 12:06, fetch9b.py), same pool records; the
crowd classification of classify.annotate() on the union."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
import load as LD
from load import *
from classify import annotate, crowd_fp


def load_all():
    pools = LD.load()
    have = {p["pid"] for p in pools}
    D = json.load(open(HERE + "react9b_data.json"))
    for pid, P in D["pools"].items():
        if pid in have: continue
        m = P["meta"]; FP = P["fp"]; sw = []; mls = []
        for e in P["ev"]:
            d = e["data"]; t = P["txs"].get(e["tx"])
            if e["t0"] == T_ML:
                mls.append({"bn": e["bn"], "li": e["li"], "dl": sgn(W(d, 2)), "tl": sgn(W(d, 0)), "tu": sgn(W(d, 1)), "tx": e["tx"], "sender": e["sender"],
                            "from": t["from"] if t else None, "to": t["to"] if t else None, "nonce": t["nonce"] if t else None, "idx": t["idx"] if t else None, "sel": t["sel"] if t else None})
                continue
            a0, a1 = s128(W(d, 0)), s128(W(d, 1))
            sw.append({"bn": e["bn"], "li": e["li"], "a0": a0, "a1": a1, "sp": W(d, 2), "L": W(d, 3), "tx": e["tx"], "via": e["sender"],
                       "from": t["from"] if t else None, "to": t["to"] if t else None, "nonce": t["nonce"] if t else None, "idx": t["idx"] if t else None,
                       "sel": t["sel"] if t else None, "value": t["value"] if t else None, "fp": FP.get(e["tx"])})
        sw.sort(key=lambda x: (x["bn"], x["li"])); mls.sort(key=lambda x: (x["bn"], x["li"]))
        pull = next((x for x in mls if x["dl"] < 0), None)
        pools.append({"pid": pid, "m": m, "b0": m["block"], "ts": m["ts"], "kind": m["kind"], "fee": m["fee"], "sw": sw, "mls": mls, "pull": pull,
                      "deployer": (m.get("from") or "").lower(), "launch": P["txs"].get(m["tx"], {})})
    pools.sort(key=lambda p: p["b0"])
    head = D["head"]
    return pools, head
