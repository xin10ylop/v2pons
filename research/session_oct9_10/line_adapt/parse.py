#!/usr/bin/env python3
"""line_adapt parse: per-pool records from data/ (pools, events, txs, heads) -> data/rec.json
Each swap: off (block - b0), li, a0 (signed ETH delta of the caller: < 0 = a buy of -a0 wei), a1, sp (sqrtP after), L (after), tx, to, from, sel,
value, cls (bot = to the bot router with c1120e3d; else the caller's router/selector), minout (word 4 for bot buys).
Pull: the first ModifyLiquidity with a negative liquidity delta (off, li, from, to, sel)."""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"


def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def wd(inp, i):
    s = inp[10 + 64 * i: 10 + 64 * (i + 1)]
    return int(s, 16) if len(s) == 64 else None


def load_txs():
    TX = {}
    for f in sorted(os.listdir(D)):
        if f.startswith("txs_") and f.endswith(".jsonl"):
            for line in open(os.path.join(D, f)):
                try: t = json.loads(line)
                except Exception: continue
                TX[t["hash"]] = t
    return TX


def main():
    P = json.load(open(os.path.join(D, "pools.json"))); EV = json.load(open(os.path.join(D, "events.json"))); TX = load_txs()
    HD = json.load(open(os.path.join(D, "heads.json"))) if os.path.exists(os.path.join(D, "heads.json")) else {}; w = json.load(open(os.path.join(D, "window.json")))
    out = []
    for p in sorted(P, key=lambda p: p["b0"]):
        ev = EV[p["pid"]]; b0 = p["b0"]
        adds = []; swaps = []; mls = []
        for c in ev:
            d = c["data"]; t = TX.get(c["tx"]) or {}
            if c["t"] == T_ML:
                dl = sgn(W(d, 2)); m = {"off": c["bn"] - b0, "li": c["li"], "dl": dl, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "tx": c["tx"], "from": t.get("from"), "to": t.get("to"), "sel": t.get("sel")}
                mls.append(m)
                if c["bn"] == b0 and dl > 0: adds.append((m["lo"], m["hi"], dl))
            else:
                a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
                bot = t.get("to") == ROUTER and t.get("sel") == "c1120e3d"
                swaps.append({"off": c["bn"] - b0, "li": c["li"], "ti": c["ti"], "a0": a0, "a1": a1, "sp": W(d, 2), "L": W(d, 3), "tx": c["tx"], "to": t.get("to"), "from": t.get("from"),
                              "sel": t.get("sel"), "value": t.get("value"), "nonce": t.get("nonce"), "gasPrice": t.get("gasPrice"), "maxPrio": t.get("maxPrio"), "bot": bot,
                              "minout": wd(t["input"], 4) if bot else None, "w2": ("0x" + t["input"][10 + 64 * 2 + 24: 10 + 64 * 3]) if bot else None,
                              "w3": wd(t["input"], 3) if bot else None, "w5": ("0x" + t["input"][10 + 64 * 5 + 24: 10 + 64 * 6]) if bot else None, "side": "B" if a0 < 0 else "S"})
        L0 = v4math.active_liquidity(p["tick0"], adds)
        pull = next((m for m in mls if m["dl"] < 0), None)
        hd = HD.get(str(b0))
        out.append({k: p[k] for k in ("pid", "token", "fam", "b0", "ti0", "fee", "ts", "sp0", "tick0", "tx", "from", "nonce", "value", "gas", "gasPrice", "maxPrio", "ts0", "basefee0")} |
                   {"L0": L0, "n_adds": len(adds), "swaps": swaps, "mls": [m for m in mls if m["off"] > 0 or m["dl"] < 0], "pull": pull, "complete": b0 + 1200 <= w["head"],
                    "input": p["input"]})
    json.dump(out, open(os.path.join(D, "rec.json"), "w"))
    print(len(out), "pools;", sum(r["complete"] for r in out), "complete;", collections.Counter((r["fam"], r["n_adds"], r["L0"]) for r in out))


if __name__ == "__main__":
    main()
