"""load r04_pools_cache.jsonl and summarise each pool: the crowd's first real buy (frb: a crowd buy >= 0.005 ETH), its wave, the pull,
and every outside wallet's position (buys and sells by tx.from, class 'other'), held or sold at the crowd's first buy. Used by r05-r09."""
from common import *
import collections
CROWD = {"crowd", "crowd2", "crowd_r"}
MIN_OUT = 5 * 10 ** 14          # an outside buy that counts: >= 0.0005 ETH
REAL = 5 * 10 ** 15             # the crowd's real buy: >= 0.005 ETH
def load(path=None):
    P = []
    for line in open(path or J("r04_pools_cache.jsonl")):
        P.append(summ(json.loads(line)))
    return P
def summ(p):
    sw = p["sw"]; lb = p["lb"]
    end = min(p["pull_off"] if p["pull_off"] is not None else 10 ** 9, p["win_to"] - lb)   # observed to (offsets)
    frb = next((s for s in sw if s["k"] in CROWD and s["dq"] >= REAL), None)
    cany = next((s for s in sw if s["k"] in CROWD and s["dq"] > 0), None)
    fo = frb["off"] if frb else None
    ceth = lambda a, b: sum(s["dq"] for s in sw if s["k"] in CROWD and s["dq"] > 0 and a <= s["off"] <= b) / 1e18
    # the engine's exit trigger: the first buy >= 0.005 ETH at or after + 2 by the crowd, or anyone's ETH-value buy of that size
    trig = next((s["off"] for s in sw if s["off"] >= 2 and s["dq"] >= REAL and (s["k"] in CROWD or (s["k"] == "other" and (s["val"] or 0) > 0))), None)
    sell = min(trig + 20, 80) if trig is not None else 80
    # outside wallets
    W = collections.OrderedDict()
    for s in sw:
        if s["k"] != "other" or not s["from"]: continue
        w = W.setdefault(s["from"], {"w": s["from"], "buys": [], "sells": [], "to": collections.Counter()})
        (w["buys"] if s["dq"] > 0 else w["sells"]).append(s); w["to"][s["to"]] += 1
    outs = []
    lim = fo if fo is not None else end
    for w in W.values():
        pre = [b for b in w["buys"] if b["off"] < lim or (b["off"] == lim and frb and (b["ti"], b["li"]) < (frb["ti"], frb["li"]))]
        eth_pre = sum(b["dq"] for b in pre)
        if not pre or max(b["dq"] for b in pre) < MIN_OUT: continue
        tok_pre = -sum(b["dt"] for b in pre)
        first = next(b for b in pre if b["dq"] >= MIN_OUT)
        def sold_by(off, inclusive=False):
            return sum(s["dt"] for s in w["sells"] if (s["off"] <= off if inclusive else s["off"] < off))
        tok_all = -sum(b["dt"] for b in w["buys"]); eth_in = sum(b["dq"] for b in w["buys"]); eth_out = -sum(s["dq"] for s in w["sells"])
        tok_sold = sum(s["dt"] for s in w["sells"])
        if tok_all and tok_sold > tok_all * 1.001: eth_out = eth_out * tok_all / tok_sold; tok_sold = tok_all   # a later buy's tx not fetched: the seen buys' share
        sb = sold_by(lim)
        first_sell = w["sells"][0]["off"] if w["sells"] else None
        cum = 0; exit_off = None                     # the block at which it had sold half of its pre-crowd tokens
        for s_ in w["sells"]:
            cum += s_["dt"]
            if cum >= 0.5 * tok_pre: exit_off = s_["off"]; break
        outs.append({"w": w["w"], "first_off": first["off"], "first_eth": first["dq"] / 1e18, "eth_pre": eth_pre / 1e18, "tok_pre": tok_pre,
                     "sold_pre_frac": sb / tok_pre if tok_pre else 0, "held_at_crowd": sb < 0.5 * tok_pre, "first_sell": first_sell, "exit_off": exit_off,
                     "eth_in": eth_in / 1e18, "eth_out": eth_out / 1e18, "tok_frac_sold": tok_sold / tok_all if tok_all else 0, "to": w["to"].most_common(1)[0][0],
                     "nbuys": len(w["buys"]), "nsells": len(w["sells"])})
    lwsw = [s for s in sw if s["k"] == "lw"]
    return {"pool": p["pool"], "lb": lb, "ts": p["ts"], "qs": p["qs"], "lw": p["from"], "end": end, "pull": p["pull_off"], "pull_from": p["pull_from"],
            "pull_by_lw": p["pull_from"] == p["from"] if p["pull_from"] else None, "frb": fo, "frb_eth": frb["dq"] / 1e18 if frb else None,
            "frb_to": frb["to"] if frb else None, "cany": cany["off"] if cany else None, "wave": ceth(fo, fo + 20) if fo is not None else 0.0,
            "c_hold": ceth(2, 80), "c_tot": ceth(0, 10 ** 9), "trig": trig, "sell": sell, "outs": outs, "lw_swaps": len(lwsw),
            "n_unknown": sum(1 for s in sw if s["k"] == "unknown"), "ev": p["ev"], "win_to": p["win_to"], "sw": sw}
