"""analyse_10: the four assigned families + the two controls (vbot-v2.433, operator A), from the census only.
Writes rows.json (per pool) and results.json (per family)."""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa

P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
GROUPS = collections.OrderedDict()
for k in KEYS: GROUPS[k] = {"pids": F[k]["pids"], "mode": "first_real"}
GROUPS["control:vbot-v2.433"] = {"pids": [p for p, r in P.items() if r["known"] == "vbot-v2.433"], "mode": "vbot"}
GROUPS["control:operator-A"] = {"pids": [p for p, r in P.items() if r["known"] == "operator-A"], "mode": "first_real"}
allp = set(p for g in GROUPS.values() for p in g["pids"])
E = load_events(allp)


def is_sched(x, mode):
    if mode == "vbot": return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
    return x["eth"] >= MIN_REAL


def pool_row(pid, mode):
    p = P[pid]; pool = Pool(p, E.get(pid), T, M); b0 = pool.b0
    buys = pool.buys()
    first_any = buys[0] if buys else None
    reals = [x for x in buys if x["eth"] >= MIN_REAL]
    first_real = reals[0] if reals else None
    sb = next((x for x in buys if is_sched(x, mode)), None)
    desc = lambda x: None if x is None else {"rel": x["bn"] - b0, "ti": x["ti"], "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "sel": x["sel"],
                                            "clen": x["clen"], "nonce": x["nonce"], "sender": x["sender"]}
    row = {"pid": pid, "b0": b0, "ts": p["launch_ts"], "launch_from": p["launch_from"], "launch_to": p["launch_to"], "value": p["launch_value_eth"],
           "start": pool.start, "L0": pool.L0, "tax": pool.tax, "base_fee": pool.base_fee,
           "first_any": desc(first_any), "first_real": desc(first_real), "sched": desc(sb),
           "n_buys": len(buys), "n_real_buys": len(reals), "n_sells": sum(1 for x in pool.seq if not x["buy"] and not x["relay"]),
           "relay_in": any(x["relay"] for x in pool.seq)}
    # outsiders before the scheduled buy (non-launch, non-relay buys strictly before it)
    if sb is not None:
        before = [x for x in buys if (x["bn"], x["li"]) < (sb["bn"], sb["li"])]
    else:
        before = []
    row["outsiders"] = [[x["bn"] - b0, x["eth"] / 1e18, x["to"], x["from"]] for x in before]
    row["outsider_real"] = [o for o in row["outsiders"] if o[1] >= 0.0002]
    row["relay_before_sched"] = sb is not None and any(x["relay"] and x["buy"] and (x["bn"], x["li"]) < (sb["bn"], sb["li"]) for x in pool.seq)
    # pull
    pl = pool.pulls[0] if pool.pulls else None
    row["pull"] = None if pl is None else {"rel": pl["bn"] - b0, "from_sched": (pl["bn"] - sb["bn"]) if sb else None, "from": p["first_pull_from"], "to": p["first_pull_to"],
                                          "sel": p["first_pull_selector"], "by_launcher": p["first_pull_from"] == p["launch_from"],
                                          "from_first_outsider_real": (pl["bn"] - b0 - row["outsider_real"][0][0]) if row["outsider_real"] else None}
    # front: buy lands at the end of b0+1; sell at the head of one block after the first scheduled buy behind ours, or b0+20
    B = b0 + 1
    if sb is not None and sb["bn"] <= B and mode == "vbot":
        row["front"] = {"exit": "late_sched_before_our_buy", "ret": None}
    else:
        trig = next((x for x in buys if x["bn"] > B and is_sched(x, mode)), None)
        S = min(trig["bn"] + 1, b0 + 20) if trig else b0 + 20
        row["front"] = pool.trade(B, S); row["front"]["trig"] = (trig["bn"] - b0) if trig else None
    # follow: buy lands at the end of first_real + 1; sell one block after the next real buy behind ours, or at our buy + 4
    if first_real is not None:
        Bf = first_real["bn"] + 1
        nxt = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nxt["bn"] + 1, Bf + 4) if nxt else Bf + 4
        row["follow"] = pool.trade(Bf, Sf); row["follow"]["next"] = (nxt["bn"] - b0) if nxt else None
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
        # the chain's own pre-state (our relay included) for the validation of the pricer on this swap
        pred = v4math.buy_out_int(int(sb["pre_sp"]), sb["liq"], X, fee)
        row["cap"] = {"minout_source": "calldata word 4 (vbot router)" if mo_real is not None else ("assumed 0.99 x launch-state quote" + (" (UR execute: nested, not decoded)" if sb["to"] == UR else "")),
                      "minout_over_quote": mo / quote if quote else None, "cap_from_launch": room(s_l, L_l, X, fee, mo),
                      "room_left_at_chain_state": room(s_pre, L_pre, X, fee, mo), "eth": X / 1e18, "pred_vs_actual": pred / sb["a1"] if sb["a1"] else None}
    else:
        row["cap"] = None
    # pricer validation on every buy with a known tx (prediction from the chain's own pre-state)
    row["val"] = [v4math.buy_out_int(int(x["pre_sp"]), x["liq"], x["eth"], x["fee"]) / x["a1"] for x in pool.seq if x["buy"] and x["a1"] > 0][:8]
    return row


rows = {}
for g, spec in GROUPS.items():
    rows[g] = [pool_row(pid, spec["mode"]) for pid in spec["pids"]]
    print(g[:70], len(rows[g]))
json.dump(rows, open(os.path.join(HERE, "rows.json"), "w"), default=str)
