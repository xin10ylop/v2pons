"""analyse_22 checks of the pricer on the 2-ETH operator's own pools:
 1. v4math.buy_out_int from the chain's pre-swap state vs every buy's real output (a1), and the replay's state vs the chain's sqrt_p
 2. the two outside wallets that already trade this operator (0x5e6ec144: buys ~0.0003 ETH at ~+90 and sells ~+1800-2000; 0x13301ff0:
    buys ~+90-320, sells ~300 blocks later): their real round trips re-priced by Pool.trade with their own swaps removed from the chain
    (their buy lands at the end of its block, their sell at the head of its block, as ours would) vs the ETH they really got back"""
import sys, os, json, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common22 import *  # noqa
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
T.update(json.load(open(os.path.join(HERE, "extra_txs.json"))))
F100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
pids = F[K[0]]["pids"] + F[F100]["pids"]
E = load_events(set(pids))
errs, serr = [], []
for x in pids:
    pl = Pool(P[x], E[x], T, M); s = float(pl.s_eff); L = pl.L0
    for z in pl.seq:
        if z["buy"]:
            pred = v4math.buy_out_int(z["pre_sp"], z["liq"], z["eth"], z["fee"]); errs.append(abs(pred - z["a1"]) / z["a1"])
        s = pl.apply(s, z); serr.append(abs(s - z["sqrt_p"]) / z["sqrt_p"])
print("buys", len(errs), "rel err of buy_out_int: median %.2e max %.2e" % (st.median(errs), max(errs)), "| replay state vs chain sqrt_p: max %.2e" % max(serr))
res = []
for x in pids:
    for who in ("0x5e6ec144b5f0391bdc1338d7788d766c5d76435b", "0x13301ff0"):
        pl = Pool(P[x], E[x], T, M)
        mine = [z for z in pl.seq if z["from"] and z["from"].startswith(who)]
        b = [z for z in mine if z["buy"]]; s_ = [z for z in mine if not z["buy"]]
        if len(b) != 1 or len(s_) != 1: continue
        b, s_ = b[0], s_[0]
        for z in pl.seq:
            if z is b or z is s_: z["relay"] = True                      # remove the trader's own swaps from the replayed chain
        before_in_S = any(z["bn"] == s_["bn"] and z["li"] < s_["li"] and not z["relay"] for z in pl.seq)
        after_in_B = any(z["bn"] == b["bn"] and z["li"] > b["li"] and not z["relay"] for z in pl.seq)
        sim = pl.trade(b["bn"], s_["bn"] + (1 if before_in_S else 0), stake=b["eth"])
        real = (s_["eth"] - b["eth"]) / b["eth"]
        res.append((x[:10], who[:10], b["bn"] - pl.b0, s_["bn"] - pl.b0, round(real, 5), round(sim.get("gross") or -9, 5), after_in_B, before_in_S))
for r in res: print(r)
d = [abs(r[4] - r[5]) for r in res]
print("round trips", len(res), "|model - real| median %.2e max %.2e" % (st.median(d), max(d)), "real mean %.4f model mean %.4f" % (st.mean(r[4] for r in res), st.mean(r[5] for r in res)))
json.dump({"buy_out_rel_err_median": st.median(errs), "buy_out_rel_err_max": max(errs), "replay_state_err_max": max(serr), "outsider_round_trips": res}, open(os.path.join(HERE, "validate.json"), "w"), indent=1)
