# aggregate per-family numbers for the three 7fde822e families (pools nobody trades) + the ce5494bb family's structure
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
from common8 import *
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
keys = ["0xcd1e2cbeda788d2c59b049b5f63810892614182e|7fde822e|804|10000|200|true",
        "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true",
        "0x2b0c777574bd65ed74b211e0f2bf79bd3c9bff20|7fde822e|804|10000|200|true",
        "0x80521fc999a81e467696fd834d1df0a082d01894|7fde822e|804|10000|200|true"]
allp = set(x for k in keys for x in F[k]["pids"]); E = load_events(allp)
out = {}
for k in keys:
    f = F[k]; pids = f["pids"]; rows = []
    fb_off, fb_eth, real_n, pulled, pull_off, nsw, nbuy, distinct = [], [], 0, 0, [], [], [], set()
    front = []
    for pid in pids:
        p = P[pid]; po = Pool(p, E.get(pid), T, M); L0 = po.L0
        b = po.buys()
        if b: fb_off.append(b[0]["bn"] - L0); fb_eth.append(-b[0]["a0"] / 1e18)
        if po.buys(REAL): real_n += 1
        if po.pull_bn is not None: pulled += 1; pull_off.append(po.pull_bn - L0)
        nsw.append(len(po.sw)); nbuy.append(len(b))
        g = po.buys(REAL, after_bn=L0 + 1)
        S = min(g[0]["bn"] + 1, L0 + 20) if g else L0 + 20
        if "7fde822e" in k: front.append(po.trade(L0 + 1, S))
    span_blocks = f["last_block"] - f["first_block"]
    r = {"count": f["count"], "per_day_window": round(f["count"] / WINDOW_DAYS, 2), "active_span_h": round(span_blocks * BLOCK_S / 3600, 2),
         "deployers": f["n_deployers"], "first_buy_off_p10_50_90": pct(fb_off), "first_buy_eth_p10_50_90": pct(fb_eth),
         "pools_with_real_buy": real_n, "pulled_3000": pulled, "pull_off": sorted(pull_off), "swaps_p10_50_90": pct(nsw), "buys_p10_50_90": pct(nbuy)}
    if front:
        rets = [x["ret"] for x in front]
        r["front_rule"] = stats(rets, sum(1 for x in front if x["exit"] == "pulled_first"), f["count"] / WINDOW_DAYS, len(pids))
    out[k] = r; print(k[:60], json.dumps(r))
json.dump(out, open("results.json", "w"), indent=1)
