#!/usr/bin/env python3
"""earlyentry.py HOURS [END_HOURS]: the fee-0 family bought AHEAD of its crowd (at launch + k) instead of behind the crowd's first buy,
across stake sizes, and how much the crowd buys per pool (the capacity to sell into).

Entries (our buy lands at that block, at the state before it):
  trig      behind the first crowd buy of 0.02 ETH+ after the launch block, landing 2 blocks late (the engine's rule, for comparison)
  L+k       launch block + k (k = 3, 10, 30, 100): seen in the launch block's logs and bought before the crowd
Exits: take-profit TP, stop-loss S, cap C blocks after our buy; each sell lands LAG blocks after its signal; -100% on a pull.
Stakes 0.02 / 0.1 / 0.3 / 1 ETH, with our own price impact on the way in and out (our buy is added to the pool's later states).
Pool data is cached in the scratchpad (CACHE) so reruns are free. Read-only."""
import os, sys, pickle, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math, watchfee0 as W

HOURS = float(sys.argv[1]); END_H = float(sys.argv[2]) if len(sys.argv) > 2 else 0
WIN = 6000; LAG = int(os.environ.get("LAG", "3")); GAS = W.GAS; SP = 2505036234966386302045715536678303
CACHE = os.environ.get("CACHE", "/tmp/claude-0/-home-user-v2pons/48f7dd16-3073-5667-9085-af9d544164ac/scratchpad/fee0cache.pkl")
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int((HOURS + END_H) * 36000); hi = head - int(END_H * 36000) - WIN - 100
cache = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
init = W.getlogs(lo, hi, [W.T_INIT4], W.PM)
fam = [(l["topics"][1], int(l["blockNumber"], 16)) for l in init if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:][128 + 24:192], 16) == 0
       and int(l["data"][2:][0:64], 16) == 0 and H.i256(l["data"][2:][64:128]) == 60 and int(l["data"][2:][192:256], 16) == SP]
print(f"window {HOURS:g} h ending {END_H:g} h ago: {len(fam)} launches", flush=True)
for i, (pid, bn) in enumerate(fam):
    if pid in cache:
        continue
    sw = W.getlogs(bn, bn + WIN, [W.T_SWAP4, pid], W.PM); ml = W.getlogs(bn + 1, bn + WIN, [W.T_ML, pid], W.PM)
    pull = min((int(m["blockNumber"], 16) for m in ml if W.sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    ev = sorted((int(s["blockNumber"], 16), int(s["logIndex"], 16), -W.sg(s["data"][2:66]), int(s["data"][2:][128:192], 16), int(s["data"][2:][192:256], 16)) for s in sw)
    cache[pid] = {"bn": bn, "ev": ev, "pull": pull}
    if i % 25 == 24:
        pickle.dump(cache, open(CACHE, "wb")); print(f"  fetched {i + 1}/{len(fam)}", flush=True)
pickle.dump(cache, open(CACHE, "wb"))

STAKES = [float(x) for x in os.environ.get("STAKES", "0.02,0.1,0.3,1").split(",")]
EXITS = [(0.08, 0.05, 2000), (0.15, 0.05, 2000), (0.15, 0.10, 2000), (0.30, 0.10, 2000), (0.30, 0.15, 6000), (0.50, 0.15, 6000), (None, None, 300), (None, None, 1000)]
ENTRIES = os.environ.get("ENTRIES", "trig,L+3,L+10,L+30,L+100").split(",")


def ride(c, entry_rule, stake, tp, stop, cap):
    bn, ev, pull = c["bn"], c["ev"], c["pull"]
    if entry_rule == "trig":
        t = next((e for e in ev if e[0] > bn and e[2] >= 0.02e18), None)
        if not t:
            return None
        entry = t[0] + 1 + 2
    else:
        entry = bn + int(entry_rule[2:])
    pre = [e for e in ev if e[0] < entry]
    if not pre:
        return None
    sp0, L0 = pre[-1][3], pre[-1][4]
    q = v4math.buy_out_int(sp0, L0, stake, 0)
    post = [e for e in ev if e[0] >= entry]

    def ret_at(b):
        if pull is not None and pull <= b:
            return -1.0
        sp = sp0
        for e in post:
            if e[0] > b:
                break
            sp = e[3]
        return (v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L0, stake)), L0, q, 0) - stake - GAS) / stake
    sp = sp0
    blocks = sorted({e[0] for e in post})
    for b in blocks:
        if b > entry + cap:
            break
        if pull is not None and pull <= b:
            return -1.0
        r = ret_at(b)
        if (tp is not None and r >= tp) or (stop is not None and r <= -stop):
            return ret_at(b + LAG)
    return ret_at(entry + cap)


pools = [cache[p] for p, _ in fam]
days = max((HOURS) / 24, 1e-9)
# crowd capacity: buys and net flow after the launch block, first 2000 blocks
gb, nf = [], []
for c in pools:
    xs = [e for e in c["ev"] if c["bn"] < e[0] <= c["bn"] + 2000]
    gb.append(sum(e[2] for e in xs if e[2] > 0) / 1e18); nf.append(sum(e[2] for e in xs) / 1e18)
if pools:
    print(f"crowd per pool, first 2000 blocks: gross buys median {st.median(gb):.2f} ETH (mean {st.mean(gb):.2f}), net in median {st.median(nf):.2f} ETH (mean {st.mean(nf):.2f})")
print(f"{'entry':6s} {'stake':>5s} {'exit':18s} {'n':>4s} {'mean':>7s} {'median':>7s} {'won':>5s} {'ETH/day':>8s}")
for ent in ENTRIES:
    for s in STAKES:
        best = None
        for tp, stop, cap in EXITS:
            r = [x for x in (ride(c, ent, int(s * 1e18), tp, stop, cap) for c in pools) if x is not None]
            if not r:
                continue
            m = st.mean(r)
            lab = f"tp{tp or 0:.0%}/st{stop or 0:.0%}/c{cap}"
            line = f"{ent:6s} {s:5.2f} {lab:18s} {len(r):4d} {m:+7.1%} {st.median(r):+7.1%} {sum(x > 0 for x in r):5d} {m * s * len(r) / days:8.3f}"
            print(line)
            if best is None or m > best[0]:
                best = (m, line)
        print(f"  best: {best[1] if best else '-'}", flush=True)
