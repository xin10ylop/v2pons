"""Uniform loader: every operator launch Oct 8 00:00 -> now (Oct 8 from ../yday/react_data.json + react_fp.json, Oct 9 from
react9_data.json). Each pool: meta, swaps (sorted, with tx sender/nonce/fingerprint), pull (first ModifyLiquidity with a negative
liquidityDelta), adds."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
SP = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
HERE = SP + "protect/"
US = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
REAL = 2 * 10**14


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))


def load():
    D8 = json.load(open(SP + "yday/react_data.json")); FP8 = json.load(open(SP + "yday/react_fp.json"))
    D9 = json.load(open(HERE + "react9_data.json"))
    raw = {}
    for pid, P in D8["pools"].items():
        raw[pid] = (P, FP8)
    for pid, P in D9["pools"].items():
        raw[pid] = (P, P["fp"])                     # Oct 9 replaces the Oct 9 00:11 pool of the Oct 8 file
    pools = []
    for pid, (P, FP) in raw.items():
        m = P["meta"]; sw = []; mls = []
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
        launch_tx = P["txs"].get(m["tx"], {})
        pools.append({"pid": pid, "m": m, "b0": m["block"], "ts": m["ts"], "kind": m["kind"], "fee": m["fee"], "sw": sw, "mls": mls, "pull": pull,
                      "deployer": (m.get("from") or "").lower(), "launch": launch_tx})
    pools.sort(key=lambda p: p["b0"])
    return pools


def before_pull(p, x):
    return p["pull"] is None or (x["bn"], x["li"]) < (p["pull"]["bn"], p["pull"]["li"])


def is_us(x): return x["via"] == RELAY or x["from"] == US
