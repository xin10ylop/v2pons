"""The ride rules on one pool (shared by the census and chain replays). A pool dict: sw (sorted swaps with off, buy, q, t, sp, L, who),
T (offset of the bot's first buy), pull (first pull offset or None), sp0/L0 (launch state), fee."""
from common import *
HOLDS = (10, 20, 30, 40, 60)
QS = (0.002, 0.0058, 0.0097)


def rules(p, lag):
    """-> list of (rule name, B offset, S offset or None + reason)"""
    T = p["T"]; B = T + lag; out = []
    bots = [s for s in p["sw"] if s["who"] == "bot" and s["off"] >= B]
    if bots and bots[0]["off"] < B + 60: out.append(("a 2nd-bot+1", B, bots[0]["off"] + 1))
    else: out.append(("a 2nd-bot+1", B, B + 60))                       # no bot buy behind ours within 60 blocks: the deadline
    for h in HOLDS: out.append((f"b hold{h}", B, B + h))
    sells = [s for s in p["sw"] if s["who"] == "botsell" and s["off"] > B + 1]
    if sells and sells[0]["off"] - 1 <= B + 60: out.append(("c botsell-1", B, sells[0]["off"] - 1))
    else: out.append(("c botsell-1", B, B + 60))
    return out


def run_pool(p, q_eth, lag, fee_ours, fee_pool=None, skip=None):
    fee_pool = p["fee"] if fee_pool is None else fee_pool
    res = {}
    if p["T"] is None: return res
    sw = [dict(s, bn=s["off"]) for s in p["sw"]]
    for name, B, S in rules(p, lag):
        r = replay(sw, p["sp0"], p["L0"], B, S, int(q_eth * 1e18), fee_ours, fee_pool, p["pull"], skip=skip)
        r["B"] = B; r["S"] = S; res[name] = r
    return res
