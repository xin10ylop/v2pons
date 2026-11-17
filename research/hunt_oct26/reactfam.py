#!/usr/bin/env python3
"""reactfam.py FEE TS SQRTP HOURS: does a v4 launch family still pull on an outsider? Pools of the family (fee ppm, tick spacing, launch
sqrtPriceX96, no hook, native) launched in the last HOURS. Every buy through the Universal Router (the public's way in) is resolved to its
sender; a sender buying in 3+ of the family's pools is crowd, one in only 1-2 is an outsider. For each pool with an outsider buy: blocks
from it to the pull, whether the pull came within 50 blocks (5 s), whether the outsider sold, its return; against the pull time of pools
with no outsider. Read-only."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
FEE, TS, SP, HOURS = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16); WINB = 6000; PULLW = 72000
init = W.getlogs(head - int(HOURS * 36000), head - WINB, [W.T_INIT4], W.PM)
pools = [(l["topics"][1], int(l["blockNumber"], 16)) for l in init if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:][128 + 24:192], 16) == 0
         and int(l["data"][2:][0:64], 16) == FEE and H.i256(l["data"][2:][64:128]) == TS and int(l["data"][2:][192:256], 16) == SP]
print(f"family fee {FEE} ts {TS} sqrtP {SP}: {len(pools)} pools in {HOURS:g} h", flush=True)
data = {}
for pid, bn in pools:
    sw = W.getlogs(bn, bn + WINB, [W.T_SWAP4, pid], W.PM)
    ml = W.getlogs(bn + 1, min(head, bn + PULLW), [W.T_ML, pid], W.PM)
    pull = min((int(m["blockNumber"], 16) for m in ml if W.sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    data[pid] = (bn, sorted(sw, key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16))), pull)
need = sorted({s["transactionHash"] for bn, sw, _ in data.values() for s in sw if s["topics"][2].endswith(W.UR[2:])})
frm = {}
for i in range(0, len(need), 2000):
    g = need[i:i + 2000]
    for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=8)):
        frm[h] = x["from"].lower() if x else None
cnt = collections.Counter()
for bn, sw, _ in data.values():
    for w in {frm.get(s["transactionHash"]) for s in sw if s["transactionHash"] in frm and W.sg(s["data"][2:66]) < 0}:
        cnt[w] += 1
crowd = {w for w, n in cnt.items() if n >= 3}
print(f"  UR buyers: {len(cnt)} wallets, {len(crowd)} in 3+ pools (crowd)", flush=True)
rows = []; clean = []
for pid, (bn, sw, pull) in data.items():
    outs = [s for s in sw if s["transactionHash"] in frm and frm.get(s["transactionHash"]) not in crowd and -W.sg(s["data"][2:66]) >= 1e15 and int(s["blockNumber"], 16) > bn]
    if not outs:
        clean.append(None if pull is None else pull - bn); continue
    o = outs[0]; w = frm[o["transactionHash"]]; ob = int(o["blockNumber"], 16)
    mine = [s for s in sw if frm.get(s["transactionHash"]) == w]
    nin = sum(-W.sg(s["data"][2:66]) for s in mine if W.sg(s["data"][2:66]) < 0) / 1e18; nout = sum(W.sg(s["data"][2:66]) for s in mine if W.sg(s["data"][2:66]) > 0) / 1e18
    rows.append({"off": ob - bn, "eth": -W.sg(o["data"][2:66]) / 1e18, "lag": None if pull is None else pull - ob, "sold": nout > 0, "ret": (nout / nin - 1) if nin and nout else None})
lags = [r["lag"] for r in rows if r["lag"] is not None]
print(f"  pools with a one-off outsider buy: {len(rows)}; clean: {len(clean)}")
if rows:
    print(f"  pulled within 50 blocks (5 s) of the outsider's buy: {sum(1 for l in lags if l <= 50)}/{len(rows)}; within 200: {sum(1 for l in lags if l <= 200)}/{len(rows)}; never pulled in 2 h: {sum(1 for r in rows if r['lag'] is None)}")
    if lags:
        print(f"  lag from the outsider's buy to the pull: median {st.median(lags):g} blocks")
    print(f"  outsiders that sold: {sum(1 for r in rows if r['sold'])}/{len(rows)}; their median return {st.median([r['ret'] for r in rows if r['ret'] is not None]):+.1%}" if any(r['ret'] is not None for r in rows) else f"  outsiders that sold: 0/{len(rows)}")
cp = sorted(x for x in clean if x is not None)
if cp:
    print(f"  clean pools: pulled {len(cp)}/{len(clean)}, at median +{st.median(cp):g} blocks from launch (p10 +{cp[len(cp)//10]})")
for r in sorted(rows, key=lambda r: r["off"])[:12]:
    print(f"    outsider +{r['off']} {r['eth']:.4f} ETH -> pull lag {r['lag']}, sold {r['sold']} {'' if r['ret'] is None else format(r['ret'], '+.0%')}")
