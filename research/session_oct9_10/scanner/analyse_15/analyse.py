"""analyse_15: the four assigned families + the two controls (vbot-v2.433, operator A), from the census (common15.Pool = the exact replay).
Per pool: the first non-launch buy (any size; our relay excluded), the first real buy (>= 0.0002 ETH, not the chain-wide dust bot or the
volume bot's decoy routers), the scheduled buy (per group mode), outsiders before it, the pull, the front and follow trades priced exactly,
the capacity of the scheduled buy. Writes rows.json (per pool, per group)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common15
from common15 import *  # noqa

P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
LP_ROUTER = "0xf0b7eaaf868191adc00065ca13391ef436ce8faf"    # the 0xc763b179 launchpad's router (39ecce49), used by everyone in its pools
# per-pool hook 0xae4c0cf7 tax (ppm) measured from the receipts of the family's own swaps (hookfee.py): (buy rate of the pool's first buy, sell rate
# of its first sell if any, else the buy rate); pools with no swap keep the default 4% (the lowest rate seen, here and in analyse_1's 143 pools)
HF = json.load(open(os.path.join(HERE, "hookfee.json")))
for pid in F[KEYS[1]]["pids"]:
    rows = [r for r in HF if pid.startswith(r["pid"])]
    b = next((r for r in rows if r["side"] == "buy"), None); s_ = next((r for r in rows if r["side"] == "sell"), None)
    def rate(r):
        d = dict((t, v) for t, v in r["hook_events"])
        if r["side"] == "buy": v = d["0x8d1f1ed7"]; return round(v[2] / v[0] * 1e6)
        v = d["0x5a2eb160"]; return round(v[2] / v[1] * 1e6)
    if b: common15.ETH_TAX[pid] = (rate(b), rate(s_) if s_ else rate(b))
MODES = {KEYS[0]: "first_real", KEYS[1]: "lp_router", KEYS[2]: "first_real", KEYS[3]: "first_real"}
GROUPS = collections.OrderedDict()
for k in KEYS: GROUPS[k] = {"pids": F[k]["pids"], "mode": MODES[k]}
GROUPS["control:vbot-v2.433"] = {"pids": [p for p, r in P.items() if r["known"] == "vbot-v2.433"], "mode": "vbot"}
GROUPS["control:operator-A"] = {"pids": [p for p, r in P.items() if r["known"] == "operator-A"], "mode": "first_real"}
allp = set(p for g in GROUPS.values() for p in g["pids"])
E = load_events(allp)


def own_noise(x):
    """the chain-wide dust bot and the volume bot's decoy routers"""
    return x["from"] in DUST_WALLETS or x["to"] in DECOY_ROUTERS or x["sender"] in DECOY_ROUTERS


def is_sched(x, mode):
    if mode == "vbot": return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
    if mode == "lp_router": return x["to"] == LP_ROUTER and x["sel"] == "39ecce49" and x["eth"] >= MIN_REAL
    return x["eth"] >= MIN_REAL and not own_noise(x)


def desc(x, b0):
    if x is None: return None
    return {"rel": x["bn"] - b0, "ti": x["ti"], "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "sel": x["sel"], "clen": x["clen"],
            "nonce": x["nonce"], "sender": x["sender"], "fee": x["fee"]}


def pool_row(pid, mode):
    p = P[pid]; pool = Pool(p, E.get(pid), T, M); b0 = pool.b0
    buys = pool.buys()
    first_any = buys[0] if buys else None
    reals = [x for x in buys if x["eth"] >= MIN_REAL and not own_noise(x)]
    first_real = reals[0] if reals else None
    sb = next((x for x in buys if is_sched(x, mode)), None)
    sells = [x for x in pool.seq if not x["buy"] and not x["relay"]]
    row = {"pid": pid, "b0": b0, "ts": p["launch_ts"], "launch_from": p["launch_from"], "launch_to": p["launch_to"], "value": p["launch_value_eth"],
           "nonce": p["launch_nonce"], "start": pool.start, "L0": pool.L0, "base_fee": pool.base_fee, "fee_key": p["fee"], "tick0": p["tick0"],
           "etax": pool.etax, "ranges_launch": [[a["lo"], a["hi"], a["dl"]] for a in pool.adds if a["tx"] == pool.live_tx],
           "buy_in_launch_tx": [x["eth"] / 1e18 for x in pool.seq if x["in_launch"] and x["buy"]],
           "first_any": desc(first_any, b0), "first_real": desc(first_real, b0), "sched": desc(sb, b0),
           "n_buys": len(buys), "n_real_buys": len(reals), "n_sells": len(sells), "relay_in": any(x["relay"] for x in pool.seq),
           "buys20": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sel"]] for x in buys[:20]],
           "sells10": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sel"]] for x in sells[:10]],
           "launcher_sells": [[x["bn"] - b0, round(x["eth"] / 1e18, 9)] for x in sells if x["from"] == p["launch_from"]]}
    before = [x for x in buys if sb is not None and (x["bn"], x["li"]) < (sb["bn"], sb["li"])]
    row["outsiders"] = [[x["bn"] - b0, x["eth"] / 1e18, x["to"], x["from"], own_noise(x)] for x in before]
    row["outsider_real"] = [o for o in row["outsiders"] if o[1] >= 0.0002 and not o[4]]
    pl = pool.pulls[0] if pool.pulls else None
    row["pull"] = None if pl is None else {"rel": pl["bn"] - b0, "from_sched": (pl["bn"] - sb["bn"]) if sb else None,
                                          "from_first_real": (pl["bn"] - first_real["bn"]) if first_real else None,
                                          "from": p["first_pull_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"],
                                          "by_launcher": p["first_pull_from"] == p["launch_from"], "dl": pl["dl"],
                                          "full": -pl["dl"] >= sum(a["dl"] for a in pool.adds if a["tx"] == pool.live_tx),
                                          "from_first_outsider_real": (pl["bn"] - b0 - row["outsider_real"][0][0]) if row["outsider_real"] else None}
    # front: our buy lands at the end of b0+1; sell at the head of one block after the first scheduled buy behind ours, or b0+20
    B = b0 + 1
    if sb is not None and sb["bn"] <= B:
        row["front"] = {"exit": "sched_before_our_buy", "ret": None}
    else:
        trig = next((x for x in buys if x["bn"] > B and is_sched(x, mode)), None)
        S = min(trig["bn"] + 1, b0 + 20) if trig else b0 + 20
        row["front"] = pool.trade(B, S); row["front"]["trig"] = (trig["bn"] - b0) if trig else None
        row["front_nohook"] = None
        if pool.etax != (0, 0):
            keep = pool.etax; pool.etax = (0, 0); row["front_nohook"] = pool.trade(B, S); pool.etax = keep
    # follow: our buy lands at the end of first_real + 1; sell one block after the next real buy behind ours, or at our buy + 4
    if first_real is not None:
        Bf = first_real["bn"] + 1
        nxt = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nxt["bn"] + 1, Bf + 4) if nxt else Bf + 4
        row["follow"] = pool.trade(Bf, Sf); row["follow"]["next"] = (nxt["bn"] - b0) if nxt else None
        row["follow"]["trig_rel"] = first_real["bn"] - b0
        row["follow_nohook"] = None
        if pool.etax != (0, 0):
            keep = pool.etax; pool.etax = (0, 0); row["follow_nohook"] = pool.trade(Bf, Sf); pool.etax = keep
    else:
        row["follow"] = {"exit": "no_trigger", "ret": None}
    # capacity of the scheduled buy
    if sb is not None:
        X = sb["eth"]; fee = sb["fee"]
        s_l, L_l = pool.launch_state()
        quote = v4math.buy_out_int(int(s_l), L_l, X, fee)
        mo_real = pool.vbot_minout(sb); src = None
        if mo_real is not None: src = "calldata word 4 (vbot router c1120e3d)"
        elif sb["to"] == LP_ROUTER and sb["sel"] == "39ecce49" and sb["input"]:
            mo_real = word(sb["input"], 1); src = "calldata word 1 (launchpad router 0xf0b7eaaf 39ecce49)"
        mo = mo_real if mo_real is not None else int(quote * 0.99)
        if src is None:
            src = "ASSUMED 0.99 x launch-state quote" + (" (UR execute: nested, not decoded)" if sb["to"] == UR else f" (router {sb['to']} {sb['sel']} not decoded)")
        s_pre, L_pre = pool.state_through(None, upto_li=(sb["bn"], sb["li"]))
        unl = mo_real is not None and mo_real <= 1          # minOut 0 or 1 wei: no slippage limit at all
        na = L_l <= 0 or quote == 0                         # no liquidity a buy can reach at the launch state: capacity undefined
        row["cap"] = {"minout_source": src, "minout": mo, "minout_over_quote": mo / quote if quote else None, "unlimited": unl, "na_no_launch_liquidity": na,
                      "cap_from_launch": None if na else (float("inf") if unl else room(s_l, L_l, X, fee, mo)),
                      "room_left_at_chain_state": None if na else (float("inf") if unl else room(s_pre, L_pre, X, fee, mo)), "eth": X / 1e18,
                      "actual_over_launch_quote": sb["a1"] / quote if quote else None}
    else:
        row["cap"] = None
    return row


if __name__ == "__main__":
    rows = {}
    for g, spec in GROUPS.items():
        rows[g] = [pool_row(pid, spec["mode"]) for pid in spec["pids"]]
        print(g[:80], len(rows[g]))
    json.dump({"eth_tax": common15.ETH_TAX, "rows": rows}, open(os.path.join(HERE, "rows.json"), "w"), default=str)
