"""analyse_7: my four 7fde822e families plus the two controls (vbot-v2.433, operator A), every number from the census + the exact replay."""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa

P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "families_in.json")))
VBOT_DECOY_ROUTERS = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}

groups = collections.OrderedDict()
for k in KEYS: groups[k] = list(F[k]["pids"])
groups["control:vbot-v2.433"] = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
groups["control:operator-A"] = [pid for pid, p in P.items() if p["known"] == "operator-A"]
allp = set(x for v in groups.values() for x in v)
E = load_events(allp)
POOLS = {pid: Pool(P[pid], E.get(pid), T, M) for pid in allp}


def sched_buy(g, pool):
    """the operator's first scheduled buy: v2.433 = its router's first buy; otherwise the first non-launch buy >= 0.0002 ETH"""
    bs = pool.buys()
    if g == "control:vbot-v2.433":
        return next((x for x in bs if x["to"] == VBOT_ROUTER), None)
    return next((x for x in bs if x["eth"] >= MIN_REAL), None)


def is_operator_side(g, x):
    if g == "control:vbot-v2.433":
        return x["to"] == VBOT_ROUTER or x["to"] in VBOT_DECOY_ROUTERS or x["from"] == DUST
    return x["from"] == DUST


def validate(pool):
    """the start state against the chain: the first non-launch swap predicted from (s_eff, L0)"""
    x = next((x for x in pool.seq if not x["in_launch"]), None)
    pre = [y for y in pool.seq if y["in_launch"]]
    if x is None or not x["buy"] or pre: return None
    tok = v4math.buy_out_int(pool.s_eff, pool.L0, x["eth"], x["fee"])
    return abs(tok - x["a1"]) / x["a1"] if x["a1"] else None


out = {}
for g, pids in groups.items():
    pools = [POOLS[p] for p in pids]
    n = len(pools)
    rows = []
    for pool in pools:
        p = pool.p; bs = pool.buys(); sb = sched_buy(g, pool)
        fb = bs[0] if bs else None
        fr = next((x for x in bs if x["eth"] >= MIN_REAL), None)
        b0 = pool.b0
        r = {"pid": p["pid"], "b0": b0, "ts": p["launch_ts"], "from": p["launch_from"], "nonce": p["launch_nonce"], "start": pool.start,
             "fb": fb and {"off": fb["bn"] - b0, "eth": fb["eth"] / 1e18, "to": fb["to"], "from": fb["from"], "nonce": fb["nonce"]},
             "fr": fr and {"off": fr["bn"] - b0, "eth": fr["eth"] / 1e18, "to": fr["to"], "from": fr["from"], "nonce": fr["nonce"], "sel": fr["sel"]},
             "sb": sb and {"off": sb["bn"] - b0, "eth": sb["eth"] / 1e18, "to": sb["to"], "from": sb["from"], "nonce": sb["nonce"], "sel": sb["sel"]},
             "pull": (pool.pull_bn - b0) if pool.pull_bn else None, "pull_from": p["first_pull_from"], "pull_to": p["first_pull_to"],
             "val_err": validate(pool)}
        # outsiders before the scheduled buy (or, with none, in the whole window), excluding the operator's side and the dust bot
        lim = sb["bn"] if sb else 10 ** 12
        outs = [x for x in bs if (x["bn"], x["li"]) < ((sb["bn"], sb["li"]) if sb else (lim, 0)) and not is_operator_side(g, x)]
        r["outsiders"] = [(x["bn"] - b0, x["eth"] / 1e18, x["to"], x["from"]) for x in outs]
        r["dust_before"] = sum(1 for x in bs if x["from"] == DUST and (not sb or x["bn"] < sb["bn"]))
        # front: buy at b0+1 (end of block), sell one block after the scheduled buy, or at b0+20
        B = b0 + 1
        if sb and sb["bn"] <= B:
            r["front"] = {"exit": "late", "ret": None, "sched_off": sb["bn"] - b0}
        else:
            S = sb["bn"] + 1 if (sb and sb["bn"] <= b0 + 19) else b0 + 20
            r["front"] = pool.trade(B, S)
        # follow: buy one block after the first real buy, sell one block after the next real buy behind ours, or at our buy + 4
        if fr:
            Bf = fr["bn"] + 1
            nb = next((x for x in bs if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
            Sf = min(nb["bn"] + 1, Bf + 4) if nb else Bf + 4
            if Sf - b0 > 3000: r["follow"] = {"exit": "beyond_window", "ret": None}
            else: r["follow"] = pool.trade(Bf, Sf)
        else:
            r["follow"] = None
        # capacity of the scheduled buy
        if sb:
            fee = sb["fee"]; X = sb["eth"]
            mo_real = pool.vbot_minout(sb)
            quote = v4math.buy_out_int(pool.s_eff, pool.L0, X, fee)
            mo = mo_real if mo_real is not None else int(quote * 0.99)
            pre = [x for x in pool.seq if (x["bn"], x["li"]) < (sb["bn"], sb["li"]) and not x["relay"]]
            s_pre = float(pool.s_eff)
            for x in pre: s_pre = Pool.apply(s_pre, x)
            r["cap"] = {"real_minout": mo_real is not None, "minout_vs_quote": mo / quote if quote else None,
                        "room_from_launch": room(pool.s_eff, pool.L0, X, fee, mo), "room_after_preburys": room(int(s_pre), pool.L0, X, fee, mo),
                        "eth_ahead_actual": sum(x["eth"] for x in pre if x["buy"] and not x["in_launch"]) / 1e18, "sched_eth": X / 1e18}
        rows.append(r)
    out[g] = rows
    print(g, n, "front", summarize([r["front"] for r in rows]), "\n   follow", summarize([r["follow"] for r in rows if r["follow"]]))
json.dump(out, open(os.path.join(HERE, "rows.json"), "w"), default=str)
