#!/usr/bin/env python3
"""exitlag.py HOURS END_HOURS: how much the fee-0 ride depends on how fast we act. Same entry and pools as exitrules.py, every pool fetched
once; for each (ENTRY_LAG, LAG) pair -- our buy landing ENTRY_LAG blocks after the trigger's block + 1, each sell LAG blocks after its signal --
the rules: take-profit +8% with cap 2000, with a stop-loss at -5% / -10%, and the -5% stop with a 600 / 300-block cap. A slow route (an RPC
poll instead of the feed) shows up as a large lag. Read-only."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math, watchfee0 as W

HOURS = float(sys.argv[1]); END_H = float(sys.argv[2]) if len(sys.argv) > 2 else 0
STAKE = int(float(os.environ.get("STAKE", "0.02")) * 1e18); GAS = W.GAS; TRIG = float(os.environ.get("TRIG_ETH", "0.02")); SP = 2505036234966386302045715536678303
LAGS = [(2, 3), (5, 5), (10, 10), (20, 20), (50, 20)]
RULES = {"tp8/cap2000": dict(), "tp8/stop5": dict(stop=0.05), "tp8/stop10": dict(stop=0.10), "tp8/stop5/cap600": dict(stop=0.05, cap=600), "tp8/stop5/cap300": dict(stop=0.05, cap=300)}
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int((HOURS + END_H) * 36000); hi = head - int(END_H * 36000) - 2200
init = W.getlogs(lo, hi, [W.T_INIT4], W.PM)
fam = [(l["topics"][1], int(l["blockNumber"], 16)) for l in init if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:][128 + 24:192], 16) == 0
       and int(l["data"][2:][0:64], 16) == 0 and H.i256(l["data"][2:][64:128]) == 60 and int(l["data"][2:][192:256], 16) == SP]
print(f"window {HOURS:g} h ending {END_H:g} h ago: {len(fam)} launches", flush=True)
res = collections.defaultdict(list); toff = []
for pid, bn in fam:
    sw = W.getlogs(bn, bn + 2300, [W.T_SWAP4, pid], W.PM); ml = W.getlogs(bn + 1, bn + 2300, [W.T_ML, pid], W.PM)
    pull = min((int(m["blockNumber"], 16) for m in ml if W.sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    ev = sorted((int(s["blockNumber"], 16), int(s["logIndex"], 16), -W.sg(s["data"][2:66]), int(s["data"][2:][128:192], 16), int(s["data"][2:][192:256], 16)) for s in sw)
    trig = next((e for e in ev if e[0] > bn and e[2] >= TRIG * 1e18), None)
    if not trig:
        continue
    toff.append(trig[0] - bn)
    for el, lag in LAGS:
        entry = trig[0] + 1 + el
        pre = [e for e in ev if e[0] < entry]
        sp0, L0 = pre[-1][3], pre[-1][4]
        q = v4math.buy_out_int(sp0, L0, STAKE, 0)

        def ret_at(b):
            if pull is not None and pull <= b:
                return -1.0
            post = [e for e in ev if entry <= e[0] <= b]
            sp = post[-1][3] if post else sp0
            return (v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L0, STAKE)), L0, q, 0) - STAKE - GAS) / STAKE
        blocks = sorted({e[0] for e in ev if e[0] >= entry})
        for name, kw in RULES.items():
            tp, cap, stop = 0.08, kw.get("cap", 2000), kw.get("stop")
            r = None
            for b in blocks:
                if b > entry + cap:
                    break
                if pull is not None and pull <= b:
                    r = -1.0; break
                x = ret_at(b)
                if x >= tp or (stop is not None and x <= -stop):
                    r = ret_at(b + lag); break
            res[(el, lag, name)].append(ret_at(entry + cap) if r is None else r)
n = len(toff)
print(f"rides {n}; trigger at launch + {min(toff)}..{max(toff)} blocks (median {st.median(toff):g})")
print(f"{'buy late':>8s} {'sell late':>9s} {'rule':18s} {'mean':>7s} {'median':>7s} {'won':>8s} {'worst':>7s}")
for el, lag in LAGS:
    for name in RULES:
        r = res[(el, lag, name)]
        print(f"{el:8d} {lag:9d} {name:18s} {st.mean(r):+7.1%} {st.median(r):+7.1%} {sum(x > 0 for x in r):4d}/{len(r):<3d} {min(r):+7.1%}")
