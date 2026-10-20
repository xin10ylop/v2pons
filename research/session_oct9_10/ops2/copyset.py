"""copy loop, blocks 83396250-83518499 (cache only, run after the full scan): every wallet the collector paid or was paid by, and their own
plain-transfer counterparties (one-time funders, burst buyers, deployers); then any transaction in the window that touches crowd A, the
A dispatchers/sweeps (Oct 9 lists), 0x5861..., or 0x20d811c8; and any transaction between the copy set and those."""
import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
LO, HI = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (83396250, 83518499)
assert not missing(LO, HI), missing(LO, HI)[:5]
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
ASIDE = A | DISP | SWEEP
T = [(bn, ts, t) for bn, ts, t in bc.txs(LO, HI)]
print("txs in window", len(T))
plain = lambda t: t[5] in ("0x", "") and int(t[3]) > 0
eoa = set(t[1] for bn, ts, t in T)           # senders = EOAs
W1 = set()
for bn, ts, t in T:
    if plain(t) and C in (t[1], t[2]): W1.add(t[2] if t[1] == C else t[1])
W2 = set()
for bn, ts, t in T:
    if plain(t) and (t[1] in W1 or t[2] in W1):
        o = t[2] if t[1] in W1 else t[1]
        if o in eoa: W2.add(o)
W = ({C} | W1 | W2)
print("collector counterparties", len(W1), "second ring", len(W2 - W1 - {C}), "copy set", len(W))
print("copy set labels:", collections.Counter(lab(a) or "-" for a in W))
aside_tx = [(bn, t) for bn, ts, t in T if t[1] in ASIDE or t[2] in ASIDE]
print("transactions touching crowd A / A hubs / 0x5861 in the window:", len(aside_tx))
for bn, t in aside_tx[:20]: print("   ", bn, t[1], lab(t[1]), "->", t[2], lab(t[2]), int(t[3]) / 1e18, "n", t[4], t[5])
cross = [(bn, t) for bn, ts, t in T if (t[1] in W and t[2] in ASIDE) or (t[1] in ASIDE and t[2] in W)]
print("transactions between the copy set and the A side:", len(cross))
# copy set wallets that also show up as senders outside the window in other cached ranges is checked by mix.py (cache-wide)
# collector accounting
cin = sum(int(t[3]) for bn, ts, t in T if t[2] == C) / 1e18; cout = sum(int(t[3]) for bn, ts, t in T if t[1] == C) / 1e18
print(f"collector: in {cin:.4f} ETH, out {cout:.4f} ETH over the window; txs sent {sum(1 for bn, ts, t in T if t[1] == C)}")
big_in = sorted([(bn, t[1], int(t[3]) / 1e18, t[4]) for bn, ts, t in T if t[2] == C and int(t[3]) > 1e18])
big_out = sorted([(bn, t[2], int(t[3]) / 1e18, t[4]) for bn, ts, t in T if t[1] == C and int(t[3]) > 1e18])
print("collector big inputs (>1 ETH):", len(big_in), "sum %.3f" % sum(x[2] for x in big_in)); print("collector big outputs (>1 ETH):", len(big_out), "sum %.3f" % sum(x[2] for x in big_out))
print("first big in:", big_in[:2]); print("last big out:", big_out[-2:])
json.dump(sorted(W), open("copyset.json", "w"))
# B crowd activity in the window
bt = collections.Counter((lab(t[1]) if t[1] in B else lab(t[2])) for bn, ts, t in T if t[1] in B or t[2] in B)
print("txs touching crowd B in window:", sum(bt.values()))
