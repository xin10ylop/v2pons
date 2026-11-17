#!/usr/bin/env python3
"""dumpwho.py HOURS END_HOURS: the fee-0 family's big losers -- who crashed the price, how fast, and could we have seen it coming?

Entry as watchfee0/exitrules (behind the first crowd buy of TRIG_ETH+ after the launch block, ENTRY_LAG late). For every ride:
  outcome     the take-profit/cap ride (+8% / 2000 blocks, sell LAG late)
  the crash   for rides that lose 20%+: the single swap after our entry with the biggest price drop, its tx sender, whether that is the
              launch wallet, its block offset from our entry, and the share of the total drop it made in one transaction (a one-tx dump
              cannot be stopped out)
  before entry, features we could filter on: the launch tx value, launch-block buy (ETH the launcher put in as its own stash), blocks from
              launch to the trigger, trigger size, crowd buys/ETH before entry, the launch wallet's nonce at launch, and the launch wallet's
              earlier launches in the window with their outcome (a launcher that dumped before)
Prints the losers in full and, per feature, winners vs losers. Read-only."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math, watchfee0 as W

HOURS = float(sys.argv[1]); END_H = float(sys.argv[2]) if len(sys.argv) > 2 else 0
STAKE = int(float(os.environ.get("STAKE", "0.02")) * 1e18); GAS = W.GAS; ENTRY_LAG = int(os.environ.get("ENTRY_LAG", "2")); LAG = int(os.environ.get("LAG", "3"))
TRIG = float(os.environ.get("TRIG_ETH", "0.02")); SP = 2505036234966386302045715536678303; TP = 0.08; CAP = 2000
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int((HOURS + END_H) * 36000); hi = head - int(END_H * 36000) - 2100
init = W.getlogs(lo, hi, [W.T_INIT4], W.PM)
fam = [(l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"]) for l in init if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:][128 + 24:192], 16) == 0
       and int(l["data"][2:][0:64], 16) == 0 and H.i256(l["data"][2:][64:128]) == 60 and int(l["data"][2:][192:256], 16) == SP]
print(f"window {HOURS:g} h ending {END_H:g} h ago: {len(fam)} launches", flush=True)
ltx = {}
for i in range(0, len(fam), 200):
    g = fam[i:i + 200]
    for (pid, bn, h), x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for _, _, h in g], size=50, workers=4, tries=8)):
        ltx[pid] = x
rows = []
for pid, bn, h in fam:
    t = ltx.get(pid)
    if not t:
        continue
    lw = t["from"].lower()
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

    def ret_at(b):
        if pull is not None and pull <= b:
            return -1.0
        post = [e for e in ev if entry <= e[0] <= b]
        sp = post[-1][3] if post else sp0
        return (v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L0, STAKE)), L0, q, 0) - STAKE - GAS) / STAKE
    r = None
    for b in sorted({e[0] for e in ev if e[0] >= entry}):
        if b > entry + CAP:
            break
        if pull is not None and pull <= b:
            r = -1.0; break
        if ret_at(b) >= TP:
            r = ret_at(b + LAG); break
    if r is None:
        r = ret_at(entry + CAP)
    row = {"pid": pid, "bn": bn, "lw": lw, "ret": r, "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16),
           "launch_buy": sum(e[2] for e in ev if e[0] == bn and e[2] > 0) / 1e18, "trig_off": trig[0] - bn, "trig_eth": trig[2] / 1e18,
           "pre_buys": sum(1 for e in pre if e[0] > bn and e[2] > 0), "pre_eth": sum(e[2] for e in pre if e[0] > bn and e[2] > 0) / 1e18}
    if r <= -0.2:
        # the swap with the largest one-step price drop (native per token falls as sqrtP falls when token is currency1; use |log| of the
        # step in sqrtP in the direction of a sell, i.e. native out)
        post = [e for e in ev if e[0] >= entry]
        prev = sp0; worst = None; total = 0.0
        for e in post:
            if e[2] < 0 and prev:
                d = abs((e[3] / prev) ** 2 - 1)
                total += d
                if worst is None or d > worst[0]:
                    worst = (d, e)
            prev = e[3]
        if worst:
            x = H.rpc(url, "eth_getTransactionByHash", [worst[1][5]]) or {}
            wf = (x.get("from") or "?").lower()
            row.update({"crash_by": "LAUNCHER" if wf == lw else wf[:10], "crash_off": worst[1][0] - entry, "crash_eth": -worst[1][2] / 1e18,
                        "crash_share": worst[0] / total if total else 0})
    rows.append(row)
# earlier launches by the same wallet in the window and how they went
seen = collections.defaultdict(list)
for row in sorted(rows, key=lambda x: x["bn"]):
    row["prior"] = len(seen[row["lw"]]); row["prior_dump"] = sum(1 for v in seen[row["lw"]] if v <= -0.2)
    seen[row["lw"]].append(row["ret"])
print(f"rides {len(rows)}; mean {st.mean(x['ret'] for x in rows):+.1%}; losers (<= -20%): {sum(1 for x in rows if x['ret'] <= -0.2)}")
print("\n== losers ==")
for x in sorted(rows, key=lambda x: x["ret"]):
    if x["ret"] > -0.2:
        break
    print(f"  {x['pid'][:12]} {x['ret']:+6.1%} crash by {x.get('crash_by','?'):10s} {x.get('crash_eth',0):7.3f} ETH out at entry+{x.get('crash_off','?')} "
          f"({x.get('crash_share',0):.0%} of the drop in that tx) | value {x['value']:.1f} launch-buy {x['launch_buy']:.2f} trig +{x['trig_off']} "
          f"{x['trig_eth']:.3f} pre {x['pre_buys']}/{x['pre_eth']:.2f} nonce {x['nonce']} prior {x['prior']}/{x['prior_dump']}")
cb = collections.Counter(("LAUNCHER" if x.get("crash_by") == "LAUNCHER" else "other") for x in rows if x["ret"] <= -0.2)
print(f"\ncrashed by the launch wallet itself: {cb['LAUNCHER']}, by another wallet: {cb['other']}")
win = [x for x in rows if x["ret"] > 0]; lose = [x for x in rows if x["ret"] <= -0.2]
print(f"\n== feature medians: winners ({len(win)}) vs losers ({len(lose)}) ==")
for k in ["value", "launch_buy", "trig_off", "trig_eth", "pre_buys", "pre_eth", "nonce", "prior", "prior_dump"]:
    if win and lose:
        print(f"  {k:11s} {st.median(x[k] for x in win):9.3f}  vs  {st.median(x[k] for x in lose):9.3f}")
