"""analyse_13: four assigned families + the two controls (vbot-v2.433, operator A), from the census only.
Per pool: the first non-launch buy (any size, our relay excluded), the first real (>= 0.0002 ETH) buy, the scheduled buy (per group mode:
vbot = its router c1120e3d; r75 = the first buy whose tx goes to router 0x75379d5d; first_real = the first real buy that is not the dust
bot's / the vbot decoy routers'), outsiders before it, the pull, the front and follow trades priced exactly (common13.Pool.trade), the capacity.
Writes rows.json (per pool)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common13 import *  # noqa

P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
MODES = {KEYS[2]: "r75"}
GROUPS = collections.OrderedDict()
for k in KEYS: GROUPS[k] = {"pids": F[k]["pids"], "mode": MODES.get(k, "first_real")}
GROUPS["control:vbot-v2.433"] = {"pids": [p for p, r in P.items() if r["known"] == "vbot-v2.433"], "mode": "vbot"}
GROUPS["control:operator-A"] = {"pids": [p for p, r in P.items() if r["known"] == "operator-A"], "mode": "first_real"}
allp = set(p for g in GROUPS.values() for p in g["pids"])
E = load_events(allp)


def own_noise(x):
    """the chain-wide dust bot and the volume bot's decoy routers"""
    return x["from"] in DUST_WALLETS or x["to"] in DECOY_ROUTERS or x["sender"] in DECOY_ROUTERS


def is_sched(x, mode):
    if mode == "vbot": return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
    if mode == "r75": return x["to"] == R75
    return x["eth"] >= MIN_REAL and not own_noise(x)


def desc(x, b0):
    if x is None: return None
    return {"rel": x["bn"] - b0, "ti": x["ti"], "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "sel": x["sel"], "clen": x["clen"],
            "nonce": x["nonce"], "sender": x["sender"], "fee": x["fee"]}


def pool_row(pid, mode):
    p = P[pid]; pool = Pool(p, E.get(pid), T, M); b0 = pool.b0
    buys = pool.buys()
    first_any = buys[0] if buys else None
    reals = [x for x in buys if x["eth"] >= MIN_REAL]
    first_real = reals[0] if reals else None
    sb = next((x for x in buys if is_sched(x, mode)), None)
    sells = [x for x in pool.seq if not x["buy"] and not x["relay"]]
    row = {"pid": pid, "b0": b0, "ts": p["launch_ts"], "launch_from": p["launch_from"], "launch_to": p["launch_to"], "value": p["launch_value_eth"],
           "nonce": p["launch_nonce"], "start": pool.start, "L0": pool.L0, "base_fee": pool.base_fee, "fee_key": p["fee"],
           "n_ranges_launch": sum(1 for a in pool.adds if a["tx"] == pool.live_tx),
           "buy_in_launch_tx": [x["eth"] / 1e18 for x in pool.seq if x["in_launch"] and x["buy"]],
           "first_any": desc(first_any, b0), "first_real": desc(first_real, b0), "sched": desc(sb, b0),
           "n_buys": len(buys), "n_real_buys": len(reals), "n_sells": len(sells),
           "relay_in": any(x["relay"] for x in pool.seq),
           "buys40": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sender"]] for x in buys[:40]],
           "sells20": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sender"]] for x in sells[:20]],
           "launcher_sells": [[x["bn"] - b0, round(x["eth"] / 1e18, 9)] for x in sells if x["from"] == p["launch_from"]]}
    before = [x for x in buys if sb is not None and (x["bn"], x["li"]) < (sb["bn"], sb["li"])]
    row["outsiders"] = [[x["bn"] - b0, x["eth"] / 1e18, x["to"], x["from"], own_noise(x)] for x in before]
    row["outsider_real"] = [o for o in row["outsiders"] if o[1] >= 0.0002 and not o[4]]
    pl = pool.pulls[0] if pool.pulls else None
    row["pull"] = None if pl is None else {"rel": pl["bn"] - b0, "from_sched": (pl["bn"] - sb["bn"]) if sb else None,
                                          "from_first_real": (pl["bn"] - first_real["bn"]) if first_real else None,
                                          "from": p["first_pull_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"],
                                          "by_launcher": p["first_pull_from"] == p["launch_from"], "dl": pl["dl"],
                                          "from_first_outsider_real": (pl["bn"] - b0 - row["outsider_real"][0][0]) if row["outsider_real"] else None}
    # front: our buy lands at the end of b0+1; sell at the head of one block after the first scheduled buy behind ours, or b0+20
    B = b0 + 1
    if sb is not None and sb["bn"] <= B:
        row["front"] = {"exit": "sched_before_our_buy", "ret": None}
        row["front_wait"] = row["front"]
    else:
        trig = next((x for x in buys if x["bn"] > B and is_sched(x, mode)), None)
        S = min(trig["bn"] + 1, b0 + 20) if trig else b0 + 20
        row["front"] = pool.trade(B, S); row["front"]["trig"] = (trig["bn"] - b0) if trig else None
        # variant: hold until one block after the scheduled buy wherever it comes (cap: the end of the 3,000-block window)
        Sw = min(trig["bn"] + 1, b0 + 3000) if trig else b0 + 3000
        row["front_wait"] = pool.trade(B, Sw); row["front_wait"]["trig"] = row["front"]["trig"]
    # follow: our buy lands at the end of first_real + 1; sell one block after the next real buy behind ours, or at our buy + 4
    if first_real is not None:
        Bf = first_real["bn"] + 1
        nxt = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nxt["bn"] + 1, Bf + 4) if nxt else Bf + 4
        row["follow"] = pool.trade(Bf, Sf); row["follow"]["next"] = (nxt["bn"] - b0) if nxt else None
        row["follow"]["trig_rel"] = first_real["bn"] - b0
    else:
        row["follow"] = None
    # capacity of the scheduled buy
    if sb is not None:
        X = sb["eth"]; fee = sb["fee"]
        s_l, L_l = pool.launch_state()
        quote = v4math.buy_out_int(int(s_l), L_l, X, fee)
        mo_real = pool.vbot_minout(sb)
        mo = mo_real if mo_real is not None else int(quote * 0.99)
        s_pre, L_pre = pool.state_through(None, upto_li=(sb["bn"], sb["li"]))
        pred = v4math.buy_out_int(int(sb["pre_sp"]), sb["liq"], X, fee)
        src = "calldata word 4 (vbot router c1120e3d)" if mo_real is not None else (
            "ASSUMED 0.99 x launch-state quote" + (" (UR execute: nested, not decoded)" if sb["to"] in (UR, R75) and sb["sel"] == "3593564c" else (
                " (tx not in census)" if sb["to"] is None else f" (router {sb['to']} {sb['sel']} not decoded)")))
        row["cap"] = {"minout_source": src, "minout_over_quote": mo / quote if quote else None, "cap_from_launch": room(s_l, L_l, X, fee, mo),
                      "room_left_at_chain_state": room(s_pre, L_pre, X, fee, mo), "eth": X / 1e18, "pred_vs_actual": pred / sb["a1"] if sb["a1"] else None,
                      "actual_over_launch_quote": sb["a1"] / quote if quote else None}
    else:
        row["cap"] = None
    row["val"] = [v4math.buy_out_int(int(x["pre_sp"]), x["liq"], x["eth"], x["fee"]) / x["a1"] for x in pool.seq if x["buy"] and x["a1"] > 0][:8]
    return row


if __name__ == "__main__":
    rows = {}
    for g, spec in GROUPS.items():
        rows[g] = [pool_row(pid, spec["mode"]) for pid in spec["pids"]]
        print(g[:70], len(rows[g]))
    json.dump(rows, open(os.path.join(HERE, "rows.json"), "w"), default=str)
