#!/usr/bin/env python3
"""exitrules.py HOURS END_HOURS: the fee-0 family's ride under several exit rules, every pool's data fetched once.

Entry as watchfee0 (behind the first crowd buy of TRIG_ETH+ after the launch block; the buy lands ENTRY_LAG late). Exits compared (each sell
lands LAG blocks after its signal; -100% on a pull):
  tp8/cap2000     take-profit +8%, else at our buy + 2000 (the rule so far)
  tp8/capN        take-profit +8%, else at our buy + N (N = 100, 300, 600)
  tp8/stopS       take-profit +8%, stop-loss -S% (S = 5, 10), cap 2000
  launcher        sell when the launch wallet's first sell in its own pool shows (or take-profit +8%, cap 2000)
  launcher-only   sell only on the launcher's first sell (cap 2000)
Read-only."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math, watchfee0 as W

HOURS = float(sys.argv[1]); END_H = float(sys.argv[2]) if len(sys.argv) > 2 else 0
STAKE = int(float(os.environ.get("STAKE", "0.02")) * 1e18); GAS = W.GAS; ENTRY_LAG = int(os.environ.get("ENTRY_LAG", "2")); LAG = int(os.environ.get("LAG", "3"))
TRIG = float(os.environ.get("TRIG_ETH", "0.02")); SP = 2505036234966386302045715536678303
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int((HOURS + END_H) * 36000); hi = head - int(END_H * 36000) - 2100
init = W.getlogs(lo, hi, [W.T_INIT4], W.PM)
fam = [(l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"]) for l in init if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:][128 + 24:192], 16) == 0
       and int(l["data"][2:][0:64], 16) == 0 and H.i256(l["data"][2:][64:128]) == 60 and int(l["data"][2:][192:256], 16) == SP]
print(f"window {HOURS:g} h ending {END_H:g} h ago: {len(fam)} launches of the fee-0 family", flush=True)
ltx = {}
for i in range(0, len(fam), 200):
    g = fam[i:i + 200]
    for (pid, bn, h), x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for _, _, h in g], size=50, workers=4, tries=8)):
        ltx[pid] = x["from"].lower() if x else None
RULES = ["tp8/cap2000", "tp8/cap100", "tp8/cap300", "tp8/cap600", "tp8/stop5", "tp8/stop10", "launcher", "launcher-only"]
res = collections.defaultdict(list)
for pid, bn, _ in fam:
    sw = W.getlogs(bn, bn + 2200, [W.T_SWAP4, pid], W.PM); ml = W.getlogs(bn + 1, bn + 2200, [W.T_ML, pid], W.PM)
    pull = min((int(m["blockNumber"], 16) for m in ml if W.sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    ev = sorted((int(s["blockNumber"], 16), int(s["logIndex"], 16), -W.sg(s["data"][2:66]), int(s["data"][2:][128:192], 16), int(s["data"][2:][192:256], 16), s["transactionHash"]) for s in sw)
    trig = next((e for e in ev if e[0] > bn and e[2] >= TRIG * 1e18), None)
    if not trig:
        continue
    entry = trig[0] + 1 + ENTRY_LAG
    pre = [e for e in ev if e[0] < entry]
    sp0, L0 = pre[-1][3], pre[-1][4]
    q = v4math.buy_out_int(sp0, L0, STAKE, 0)
    # the launcher's sells after our entry (tx sender = the launch wallet)
    sells = [e for e in ev if e[0] >= entry and e[2] < 0]
    sfrom = {}
    if sells:
        for e, x in zip(sells, H.batch(url, [("eth_getTransactionByHash", [e[5]]) for e in sells[:400]], size=50, workers=4, tries=8)):
            sfrom[e[5]] = x["from"].lower() if x else None
    lsell = next((e[0] for e in sells if sfrom.get(e[5]) == ltx.get(pid)), None)

    def ret_at(b):
        if pull is not None and pull <= b:
            return -1.0
        post = [e for e in ev if entry <= e[0] <= b]
        sp = post[-1][3] if post else sp0
        return (v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L0, STAKE)), L0, q, 0) - STAKE - GAS) / STAKE
    blocks = sorted({e[0] for e in ev if e[0] >= entry})
    def run(tp=0.08, cap=2000, stop=None, on_launcher=False, tp_on=True):
        for b in blocks:
            if b > entry + cap:
                break
            if pull is not None and pull <= b:
                return -1.0
            if on_launcher and lsell is not None and b >= lsell:
                return ret_at(b + LAG)
            r = ret_at(b)
            if tp_on and r >= tp:
                return ret_at(b + LAG)
            if stop is not None and r <= -stop:
                return ret_at(b + LAG)
        return ret_at(entry + cap)
    res["tp8/cap2000"].append(run()); res["tp8/cap100"].append(run(cap=100)); res["tp8/cap300"].append(run(cap=300)); res["tp8/cap600"].append(run(cap=600))
    res["tp8/stop5"].append(run(stop=0.05)); res["tp8/stop10"].append(run(stop=0.10))
    res["launcher"].append(run(on_launcher=True)); res["launcher-only"].append(run(on_launcher=True, tp_on=False))
n = len(res["tp8/cap2000"])
print(f"rides: {n} (buy {ENTRY_LAG} late, sell {LAG} late, stake {STAKE/1e18:g} ETH)")
print(f"{'rule':16s} {'mean':>7s} {'median':>7s} {'won':>8s} {'worst':>7s} {'ETH/day':>8s}")
for k in RULES:
    r = res[k]
    if r:
        print(f"{k:16s} {st.mean(r):+7.1%} {st.median(r):+7.1%} {sum(x > 0 for x in r):4d}/{len(r):<3d} {min(r):+7.1%} {st.mean(r) * STAKE / 1e18 * len(r) / (HOURS / 24):+8.4f}")
