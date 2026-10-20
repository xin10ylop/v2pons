"""Skeptic f2276/100 step 6: the trap. What triggers the creator's pull? For every census + fresh pool: the ETH in the pool at the pull,
blocks since the last buy and its size, the pull vs the first crowd buy; the pools where an outsider (not the app router, not the dust
wallets) bought >= 0.001 ETH and the pull after it; the 5 rides the pull beat; pulls within 50 blocks of ANY buy >= 0.003 ETH vs the base
rate of a pull in a random 50-block window."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
pools, TX = load_sample()
P = load_pools(); F = load_families(); T = load_txs(); pids = F[K]["pids"]; E = load_events(set(pids))
SP_TOP = 792280926924313289846529216293289
def eth_in_pool(sp, L): return L * (Q96 / sp - Q96 / SP_TOP) / 1e18 if sp < SP_TOP else 0.0
rows = []
for pid in pids:
    p = P[pid]; e = E[pid]; sw = e["swaps"]; b0 = p["launch_block"]
    cr = [s for s in sw if s["tx"] in T and T[s["tx"]]["to"] == CROWD and s["a0"] < 0]
    c1 = cr[0]["bn"] if cr else None
    pull = e["pulls"][0]["bn"] if e["pulls"] else None
    r = {"pid": pid, "c1": c1 - b0 if c1 else None, "pull": pull - b0 if pull else None}
    if pull:
        before = [s for s in sw if s["bn"] <= pull]
        last = before[-1] if before else None
        lastbuy = [s for s in before if s["a0"] < 0]
        r["eth_at_pull"] = round(eth_in_pool(last["sqrt_p"], last["liq"]), 4) if last else 0.0
        r["since_last_swap"] = pull - last["bn"] if last else None
        r["since_last_buy"] = pull - lastbuy[-1]["bn"] if lastbuy else None
        r["last_buy_eth"] = -lastbuy[-1]["a0"] / 1e18 if lastbuy else None
        big = [s for s in lastbuy if -s["a0"] >= 3e15]
        r["since_last_buy_3e15"] = pull - big[-1]["bn"] if big else None
        r["n_swaps_before"] = len(before)
        r["swaps_after_pull"] = sum(1 for s in sw if s["bn"] > pull)
    # buys >= 0.003 ETH: a pull within 50 blocks after
    rows.append(r)
pulled = [r for r in rows if r["pull"] is not None]
print("pulled", len(pulled), "of", len(rows))
print("ETH in pool at pull q", q([r["eth_at_pull"] for r in pulled]))
print("blocks since last swap at pull q", q([r["since_last_swap"] for r in pulled]))
print("blocks since last buy q", q([r["since_last_buy"] for r in pulled]), "last buy eth q", q([r["last_buy_eth"] for r in pulled]))
print("blocks since last buy >=0.003 q", q([r["since_last_buy_3e15"] for r in pulled]))
print("pull within 1..10 blocks after the last buy:", sum(1 for r in pulled if r["since_last_buy"] is not None and r["since_last_buy"] <= 10))
print("pull - c1 q", q([r["pull"] - r["c1"] for r in pulled if r["c1"] is not None]))
# hazard: for each buy >= 0.003 ETH (any buyer), P(pull in (bn, bn+50]); vs P(pull in a random 50-block window of the pool's life before the pull)
hz_b = []; hz_r = []; rnd = random.Random(3)
for pid in pids:
    e = E[pid]; b0 = P[pid]["launch_block"]; pull = e["pulls"][0]["bn"] if e["pulls"] else None
    end = pull if pull else b0 + 3000
    for s in e["swaps"]:
        if s["a0"] < 0 and -s["a0"] >= 3e15 and s["bn"] < end and s["bn"] <= b0 + 2950:
            hz_b.append(1 if pull and s["bn"] < pull <= s["bn"] + 50 else 0)
    for _ in range(5):
        x = rnd.randint(b0 + 30, min(end, b0 + 2950)) if min(end, b0 + 2950) > b0 + 30 else None
        if x: hz_r.append(1 if pull and x < pull <= x + 50 else 0)
print("P(pull within 50 after a buy >= 0.003):", round(sum(hz_b) / len(hz_b), 4), "n", len(hz_b), "| random block:", round(sum(hz_r) / len(hz_r), 4), "n", len(hz_r))
# outsiders in the attributed sample
OUT_EX = {DUST, "0x93b0790287720a922bb7e3cf0712062c1669847d"}
ob = []
for pl in pools:
    for s in pl["swaps"]:
        if s["buy"] and not s["crowd"] and s["from"] not in OUT_EX and s["eth"] >= 1e15:
            ob.append({"pid": pl["pid"][:10], "off": s["bn"] - pl["b0"], "eth": s["eth"] / 1e18, "from": s["from"], "to": s["to"],
                       "pull_after": (pl["pull_bn"] - s["bn"]) if pl["pull_bn"] else None, "c1": (pl["crowd1"] - pl["b0"]) if pl["crowd1"] else None})
print("outsider buys >= 0.001 ETH in the 66 attributed pools:", len(ob))
for o in ob: print("  ", o)
# all census first-8: outsider buys >= 0.001 before c1 and the pull
ob2 = []
for pid in pids:
    e = E[pid]; b0 = P[pid]["launch_block"]; pull = e["pulls"][0]["bn"] if e["pulls"] else None
    for s in e["swaps"]:
        t = T.get(s["tx"])
        if t and s["a0"] < 0 and t["to"] != CROWD and t["from"] not in OUT_EX and -s["a0"] >= 1e15:
            ob2.append((s["bn"] - b0, round(-s["a0"] / 1e18, 4), t["from"][:10], (pull - s["bn"]) if pull else None))
print("census first-8 outsider buys >= 0.001:", len(ob2), "pull after (blocks) q", q([x[3] for x in ob2 if x[3] is not None]), "never pulled", sum(1 for x in ob2 if x[3] is None))
print("   ", sorted(ob2, key=lambda x: -x[1])[:25])
json.dump({"rows": rows, "outsiders_attributed": ob, "outsiders_census_first8": ob2}, open(os.path.join(HERE, "a6_trap.json"), "w"), indent=1)
