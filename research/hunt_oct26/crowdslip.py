#!/usr/bin/env python3
"""crowdslip.py HOURS: how much buying ahead can the fee-0 family's crowd absorb before its buys revert? For every crowd buy through the
Universal Router (exact-in single swap) in the first WIN2 blocks of each pool: its minimum-out (the word after its amountIn) against the
tokens it actually got -> its tolerance t = minOut / actual. With x = the pool's virtual native reserve just before that buy, a buy of S
ETH landing ahead of it cuts its output by (x / (x + S))^2 (fee 0, one range), so it still goes through while S <= x * (1/sqrt(t) - 1).
Prints the distribution of that per-buy limit, and the share of buys that would survive stakes of 0.01 .. 1 ETH ahead of them."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24; WIN2 = int(os.environ.get("WIN2", "2000"))
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
init = W.getlogs(head - int(HOURS * 36000), head - WIN2, [W.T_INIT4], W.PM)
pools = [(l["topics"][1], int(l["blockNumber"], 16)) for l in init if int(l["data"][2:][0:64], 16) == 0 and int(l["data"][2:][64:128], 16) == 60
         and int(l["data"][2:][128 + 24:192], 16) == 0 and l["topics"][2] == "0x" + "0" * 64]
Q96 = 2 ** 96; limits = []; tols = []
for pid, bn in pools:
    sw = sorted(W.getlogs(bn, bn + WIN2, [W.T_SWAP4, pid], W.PM), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    prev_sp = None; prev_L = None; cand = []
    for s in sw:
        d = s["data"][2:]; a0 = W.sg(d[0:64]); a1 = W.sg(d[64:128]); sp = int(d[128:192], 16); L = int(d[192:256], 16)
        if a0 < 0 and s["topics"][2].endswith(W.UR[2:]) and prev_sp and int(s["blockNumber"], 16) > bn:
            cand.append((s["transactionHash"], -a0, a1, prev_L * Q96 / prev_sp))   # native in, tokens out, virtual native reserve before (wei)
        prev_sp, prev_L = sp, L
    cand = cand[:60]
    txs = H.batch(url, [("eth_getTransactionByHash", [c[0]]) for c in cand], size=50, workers=4, tries=8) if cand else []
    for (h, nin, tout, x), t in zip(cand, txs):
        if not t:
            continue
        d = t["input"][10:]; words = [int(d[64 * i:64 * (i + 1)], 16) for i in range(len(d) // 64)]
        try:
            i = words.index(nin)
        except ValueError:
            continue
        if i + 1 >= len(words):
            continue
        mo = words[i + 1]
        if not (0 < mo <= tout):
            continue
        tol = mo / tout; tols.append(tol)
        limits.append(x * (1 / tol ** 0.5 - 1) / 1e18)
print(f"last {HOURS:g} h: {len(pools)} pools; crowd buys decoded: {len(limits)}")
if limits:
    sl = sorted(limits); tl = sorted(tols)
    print(f"their min-out as a share of what they got: median {st.median(tl):.2f} (p10 {tl[len(tl)//10]:.2f}, p90 {tl[9*len(tl)//10]:.2f})")
    print(f"largest buy ahead of each that it survives: p10 {sl[len(sl)//10]:.3f} ETH, p25 {sl[len(sl)//4]:.3f}, median {st.median(sl):.3f}, p75 {sl[3*len(sl)//4]:.3f}")
    for S in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0):
        print(f"  a {S:5.2f} ETH buy ahead: {sum(1 for x in sl if x >= S) / len(sl):5.0%} of the crowd's buys still go through")
