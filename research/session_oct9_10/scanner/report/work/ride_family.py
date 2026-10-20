# A follow-style ride on one census family (argv[1]): buy at the end of block c+1 (c = the first buy of 0.0002 ETH or more), sell at the head
# of c+1+H, replayed with the C-1 skeptic's replay (copied from skeptic_.../f2276_100/common_s.py). Output report/work/ride_<key prefix>.json.
# Hook effects (taxes, afterSwap deltas) are not visible in Swap events and are NOT modelled.
import sys, json, statistics as st
S = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner"
sys.path.insert(0, S + "/census"); sys.path.insert(0, "/home/user/v2pons/src")
from load import load_families, load_pools, load_events
import v4math
Q96 = 1 << 96; STAKE = int(0.0058e18); GAS_ETH = 0.012 / 15 * 0.0058
F = load_families(); P = load_pools()
k = sys.argv[1]; pids = F[k]["pids"]; E = load_events(set(pids))
def replay(pl, B, Sb, stake=STAKE):
    if pl["pull_bn"] is not None and pl["pull_bn"] <= B: return None, "pulled_before_buy"
    prev = pl["sp0"]; L = pl["L0"]; s_cf = float(pl["sp0"]); bought = False; tokens = 0; feeb = 10000
    for x in pl["swaps"]:
        if not bought and x["bn"] > B:
            fee = x["fee"]; tokens = v4math.buy_out(s_cf, L, stake * (1 - fee / 1e6)); s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - fee / 1e6)); bought = True; feeb = fee
        if bought and x["bn"] >= Sb: break
        if x["a0"] < 0: s_cf = Q96 / (Q96 / s_cf + (Q96 / x["sqrt_p"] - Q96 / prev))
        else: s_cf = s_cf + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]; L = x["liq"]
    if not bought:
        tokens = v4math.buy_out(s_cf, L, stake * (1 - feeb / 1e6)); s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - feeb / 1e6))
    if pl["pull_bn"] is not None and pl["pull_bn"] <= Sb: return -1.0 - GAS_ETH * 1e18 / stake, "pulled"
    return v4math.sell_out(s_cf, L, tokens * (1 - feeb / 1e6)) / stake - 1 - GAS_ETH * 1e18 / stake, "sold"
out = {}
for H in (5, 10, 20, 50, 100):
    v = []; pulled = 0
    for pid in pids:
        e = E[pid]; b0 = P[pid]["launch_block"]
        rb = [s for s in e["swaps"] if s["a0"] <= -int(0.0002e18)]
        if not rb: continue
        L0 = sum(a["dl"] for a in e["adds"][:1]) if e["adds"] else 0
        pl = {"sp0": P[pid]["sqrt_p0"], "L0": L0, "swaps": e["swaps"], "pull_bn": e["pulls"][0]["bn"] if e["pulls"] else None}
        c = rb[0]["bn"]; r, why = replay(pl, c + 1, c + 1 + H)
        if r is None: continue
        v.append(r); pulled += why == "pulled"
    out[H] = {"n": len(v), "mean": round(st.mean(v), 4), "median": round(st.median(v), 4), "win": round(sum(1 for x in v if x > 0) / len(v), 3), "pulled": pulled}
print(json.dumps(out, indent=1))
json.dump(out, open(S + "/report/work/ride_" + k[:10] + ".json", "w"), indent=1)
