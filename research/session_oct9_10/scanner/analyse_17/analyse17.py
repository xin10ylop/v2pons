"""analyse_17: four assigned families + the two controls (vbot-v2.433 = 1,843 pools, operator A = all 77 pools), from the census, priced by
common17.Pool (the exact replay of explore/chk/replay.py: our buy inserted after every tx of its landing block, later swaps replayed by their
own price shift, a pull at or before our sell = stake lost, gas 2 x 104,000 x the launch block's base fee, the pool's fee both ways, plus
the per-pool ETH tax of hook 0x75a54357 for family 3, read from the launch receipts: hooktax.json).

Definitions:
  first_any   = first non-launch-tx, non-relay buy of any size
  first_real  = first non-launch-tx, non-relay buy >= 0.0002 ETH (the chain-wide dust wallets excluded; every router counted)
  sched       = the scheduled buy: v2.433 -> the bot router's first buy (0x1cbaf24d c1120e3d); others -> first_real
  front       = buy lands at the END of launch+1; sell at the HEAD of (first sched buy after launch+1) + 1, or launch+20 if none by then
  front_wait  = the same but the sell waits for the sched buy whenever it comes (no +20 cap; 3,000-block window)
  follow      = buy lands at the END of first_real + 1; sell at the HEAD of (next buy >= 0.0002 after our buy) + 1, or our buy + 4
Writes rows.json."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common17
from common17 import *  # noqa

P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
HT = json.load(open(os.path.join(HERE, "hooktax.json")))
for pid, r in HT.items():
    common17.ETH_TAX[pid] = (r["tax_ppm"], r["tax_ppm"])
GROUPS = collections.OrderedDict()
for k in KEYS: GROUPS[k] = {"pids": F[k]["pids"], "mode": "first_real"}
GROUPS["control:vbot-v2.433"] = {"pids": [p for p, r in P.items() if r["known"] == "vbot-v2.433"], "mode": "vbot"}
GROUPS["control:operator-A"] = {"pids": [p for p, r in P.items() if r["known"] == "operator-A"], "mode": "first_real"}
allp = set(p for g in GROUPS.values() for p in g["pids"])
E = load_events(allp)


def noise(x):
    return x["from"] in DUST_WALLETS


def is_real(x):
    return x["eth"] >= MIN_REAL and not noise(x)


def is_sched(x, mode):
    if mode == "vbot": return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
    return is_real(x)


def desc(x, b0):
    if x is None: return None
    return {"rel": x["bn"] - b0, "ti": x["ti"], "eth": x["eth"] / 1e18, "to": x["to"], "from": x["from"], "sel": x["sel"], "clen": x["clen"],
            "nonce": x["nonce"], "sender": x["sender"], "fee": x["fee"]}


def pool_row(pid, mode):
    p = P[pid]; pool = Pool(p, E.get(pid), T, M); b0 = pool.b0
    buys = pool.buys()
    first_any = buys[0] if buys else None
    reals = [x for x in buys if is_real(x)]
    first_real = reals[0] if reals else None
    sb = next((x for x in buys if is_sched(x, mode)), None)
    sells = [x for x in pool.seq if not x["buy"] and not x["relay"]]
    relay_buys = [x for x in pool.seq if x["relay"] and x["buy"]]
    row = {"pid": pid, "b0": b0, "ts": p["launch_ts"], "launch_from": p["launch_from"], "launch_to": p["launch_to"], "value": p["launch_value_eth"],
           "nonce": p["launch_nonce"], "start": pool.start, "L0": pool.L0, "base_fee": pool.base_fee, "fee_key": p["fee"], "tick0": p["tick0"],
           "etax": pool.etax, "ranges_launch": [[a["lo"], a["hi"], a["dl"]] for a in pool.adds if a["tx"] == pool.live_tx],
           "buy_in_launch_tx": [x["eth"] / 1e18 for x in pool.seq if x["in_launch"] and x["buy"]],
           "first_any": desc(first_any, b0), "first_real": desc(first_real, b0), "sched": desc(sb, b0),
           "n_buys": len(buys), "n_real_buys": len(reals), "n_sells": len(sells), "relay_buy_rel": [x["bn"] - b0 for x in relay_buys],
           "buys20": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sel"]] for x in buys[:20]],
           "sells10": [[x["bn"] - b0, round(x["eth"] / 1e18, 9), x["from"], x["to"], x["sel"]] for x in sells[:10]],
           "launcher_sells": [[x["bn"] - b0, round(x["eth"] / 1e18, 9)] for x in sells if x["from"] == p["launch_from"]]}
    before = [x for x in buys if sb is not None and (x["bn"], x["li"]) < (sb["bn"], sb["li"])]
    row["outsiders"] = [[x["bn"] - b0, x["eth"] / 1e18, x["to"], x["from"], noise(x)] for x in before]
    row["outsider_real"] = [o for o in row["outsiders"] if o[1] >= 0.0002 and not o[4]]
    pl = pool.pulls[0] if pool.pulls else None
    row["pull"] = None if pl is None else {
        "rel": pl["bn"] - b0, "from_sched": (pl["bn"] - sb["bn"]) if sb else None,
        "from_first_real": (pl["bn"] - first_real["bn"]) if first_real else None,
        "from_first_relay_buy": (pl["bn"] - relay_buys[0]["bn"]) if relay_buys else None,
        "from": p["first_pull_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"],
        "by_launcher": p["first_pull_from"] == p["launch_from"], "dl": pl["dl"],
        "full": -pl["dl"] >= sum(a["dl"] for a in pool.adds if a["tx"] == pool.live_tx),
        "from_first_outsider_real": (pl["bn"] - b0 - row["outsider_real"][0][0]) if row["outsider_real"] else None}
    B = b0 + 1
    if sb is not None and sb["bn"] <= B:
        row["front"] = {"exit": "sched_before_our_buy", "ret": None}; row["front_wait"] = dict(row["front"])
    else:
        trig = next((x for x in buys if x["bn"] > B and is_sched(x, mode)), None)
        S = min(trig["bn"] + 1, b0 + 20) if trig else b0 + 20
        row["front"] = pool.trade(B, S); row["front"]["trig"] = (trig["bn"] - b0) if trig else None
        Sw = trig["bn"] + 1 if trig else b0 + 20
        row["front_wait"] = pool.trade(B, Sw); row["front_wait"]["trig"] = (trig["bn"] - b0) if trig else None
    if first_real is not None:
        Bf = first_real["bn"] + 1
        nxt = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        Sf = min(nxt["bn"] + 1, Bf + 4) if nxt else Bf + 4
        row["follow"] = pool.trade(Bf, Sf); row["follow"]["next"] = (nxt["bn"] - b0) if nxt else None
        row["follow"]["trig_rel"] = first_real["bn"] - b0
    else:
        row["follow"] = {"exit": "no_trigger", "ret": None}
    if sb is not None:
        X = sb["eth"]; fee = sb["fee"]
        s_l, L_l = pool.launch_state()
        quote = v4math.buy_out_int(int(s_l), L_l, X, fee) if L_l > 0 else 0
        mo_real = pool.vbot_minout(sb)
        src = "calldata word 4 (vbot router c1120e3d)" if mo_real is not None else None
        mo = mo_real if mo_real is not None else int(quote * 0.99)
        if src is None:
            src = "ASSUMED 0.99 x launch-state quote" + (" (UR execute: nested, not decoded)" if sb["to"] == UR else f" (router {sb['to']} {sb['sel']} not decoded)")
        s_pre, L_pre = pool.state_through(None, upto_li=(sb["bn"], sb["li"]))
        na = L_l <= 0 or quote == 0
        row["cap"] = {"minout_source": src, "minout": mo, "minout_over_quote": mo / quote if quote else None, "na_no_launch_liquidity": na,
                      "cap_from_launch": None if na else room(s_l, L_l, X, fee, mo),
                      "room_left_at_chain_state": None if na else room(s_pre, L_pre, X, fee, mo), "eth": X / 1e18,
                      "actual_over_launch_quote": sb["a1"] / quote if quote else None}
    else:
        row["cap"] = None
    return row


if __name__ == "__main__":
    rows = {}
    for g, spec in GROUPS.items():
        rows[g] = [pool_row(pid, spec["mode"]) for pid in spec["pids"]]
        print(g[:80], len(rows[g]))
    json.dump({"eth_tax": common17.ETH_TAX, "rows": rows}, open(os.path.join(HERE, "rows.json"), "w"), default=str)
