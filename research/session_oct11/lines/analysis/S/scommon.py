"""S common: decode the s02 data into per-launch records (events in analyst C's compact format for replay.py's V3Sim)."""
import os, sys, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/W")
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from wcommon import compact, T_SW, T_MI, T_BU
OUT = os.path.dirname(os.path.abspath(__file__))
SR02 = "0xcaf681a66d020601342297493863e78c959e5cb2"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
def words(h, o=0): return [h[o + 64 * i: o + 64 * (i + 1)] for i in range((len(h) - o) // 64)]
def decode_buy(t):
    """the swap call: (to, selector, len, value ETH, amountIn, minOut) for exactInputSingle 04e45aaf, inside a multicall too"""
    inp = t["input"][2:]; sel = inp[:8]; to = (t.get("to") or "").lower()
    r = {"to": to, "sel": sel, "len": len(inp) // 2, "value": int(t["value"], 16) / 1e18, "amount_in": None, "min_out": None}
    def eis(h):
        w = words(h); r["amount_in"] = int(w[4], 16); r["min_out"] = int(w[5], 16); r["tok_in"] = "0x" + w[0][-40:]; r["recipient"] = "0x" + w[3][-40:]
    if sel == "04e45aaf": eis(inp[8:])
    elif sel in ("ac9650d8", "5ae401dc", "1f0464d1"):
        b = bytes.fromhex(inp[8:]); base = 32 if sel == "5ae401dc" else 0
        try:
            arr = int.from_bytes(b[base:base + 32], "big"); n = int.from_bytes(b[arr:arr + 32], "big"); r["inner"] = []
            for i in range(n):
                st = arr + 32 + int.from_bytes(b[arr + 32 + 32 * i: arr + 64 + 32 * i], "big"); ln = int.from_bytes(b[st:st + 32], "big")
                c = b[st + 32: st + 32 + ln].hex(); r["inner"].append(c[:8])
                if c[:8] == "04e45aaf": eis(c[8:])
        except Exception: pass
    return r
def load():
    D = json.load(open(os.path.join(OUT, "s02_events.json"))); TX = D["txs"]; recs = []
    for x in D["launches"]:
        lb = x["lb"]; qs = x["qs"]; lw = x["launch_from"]
        ev = [compact(l) for l in x["logs"]]; ev = [e for e in ev if e]
        mints, swaps, burns = [], [], []
        for e in ev:
            t = TX.get(e[-1]); frm = (t["from"].lower() if t else None)
            if e[0] == "mi":
                mints.append({"off": e[1] - lb, "lo": e[6], "hi": e[7], "L": e[8], "a0": e[9], "a1": e[10], "from": frm, "by_lw": frm == lw,
                              "to": (t.get("to") or "").lower() if t else None, "sel": t["input"][2:10] if t else None, "e": e})
            elif e[0] == "b":
                burns.append({"off": e[1] - lb, "L": e[8], "from": frm, "by_lw": frm == lw, "sel": t["input"][2:10] if t else None, "e": e})
            elif e[0] == "s":
                dq = e[7] if qs == 0 else e[8]; dt = e[8] if qs == 0 else e[7]
                d = {"off": e[1] - lb, "ti": e[2], "li": e[3], "dir": "B" if dq > 0 else "S", "eth": abs(dq) / 1e18, "tok": abs(dt), "from": frm, "by_lw": frm == lw, "e": e}
                if t: d.update({k: v for k, v in decode_buy(t).items() if k in ("to", "sel", "len", "value", "min_out", "amount_in", "inner")})
                swaps.append(d)
        own = [s for s in swaps if s["by_lw"] and s["dir"] == "B"]
        pulls = [b for b in burns if b["L"] > 0]
        recs.append({"pool": x["pool"], "lb": lb, "ts": x["ts"], "fee": x["fee"], "qs": qs, "lw": lw, "nonce": x["launch_nonce"], "ev_to": x["ev_to"],
                     "ev": ev, "mints": mints, "swaps": swaps, "burns": burns, "own": own, "own1": own[0] if own else None,
                     "pull1": pulls[0] if pulls else None, "token": x["token1"] if qs == 0 else x["token0"]})
    return D, recs
