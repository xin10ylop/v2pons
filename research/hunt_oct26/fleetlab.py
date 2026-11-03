#!/usr/bin/env python3
"""fleetlab.py CHAIN DUMP.json: a buyer fleet's line, judged by the token's code. buyerlab.py (DUMP=...) groups pools by their launch call;
on BNB that is PancakeSwap's public addLiquidityETH for 1,250 unrelated launches a day, so its blind test means nothing there. Here:
  fleet     buyers in the dump with 15+ pools whose buys are of real size (median 0.05-2 native) and land after the launch block
  lines     the pools' tokens by their code's keccak; a line is a code hash the fleet bought into in 5+ pools
  per line  pools, the share the fleet bought in; P(the fleet buys | a real outsider (not the fleet, not the launcher) bought 0.01+ native
            before the fleet's usual offset) against P(the fleet buys | nobody did); pulls within 100 blocks of that outsider's buy;
            the front ride: in at the head of max(launch + 2, the fleet's first buy - 5), out after it (paper, our buy in the pool)
Read-only, public RPC."""
import sys, json, collections, statistics as st
import hlib as H
from eth_utils import keccak
CH, DUMP = sys.argv[1], sys.argv[2]; url = H.CH[CH]["rpc"]; STAKE = 0.005; GAS = 0.000006
d = json.load(open(DUMP)); P = d["pools"]; buys = d["buys"]
fleet = {k for k, v in buys.items() if 0.05 <= st.median(x[1] for x in v.values()) <= 2 and st.median(x[0] for x in v.values()) >= 3}
print(f"fleet: {len(fleet)} buyers of real size in 15+ pools", flush=True)
cand = sorted({pid for k in fleet for pid in buys[k]})
grps = collections.Counter(tuple(P[pid]["grp"]) for pid in cand)
scope = [pid for pid, p in P.items() if tuple(p["grp"]) in {g for g, n in grps.items() if n >= 5}]
toks = sorted({P[pid]["tok"] for pid in scope})
codes = H.batch(url, [("eth_getCode", [t, "latest"]) for t in toks], size=50, workers=4, tries=8)
ch = {t: (keccak(bytes.fromhex(c[2:])).hex()[:12] if c and len(c) > 2 else "nocode") for t, c in zip(toks, codes)}
size = {t: (len(c) - 2) // 2 if c else 0 for t, c in zip(toks, codes)}
print(f"pools in the fleet's launch groups: {len(scope)}, tokens {len(toks)}, distinct token codes {len(set(ch.values()))}", flush=True)

def first_fleet(p):
    xs = [b for b in p["buyers"] if b[3] in fleet and b[0] > p["bn"]]
    return min(xs, key=lambda b: (b[0], b[1])) if xs else None

def sb(p, b):
    prior = [e for e in p["ev"] if e[0] < b and e[4]]
    if prior: return prior[-1][4], prior[-1][5]
    f = next((e for e in p["ev"] if e[4]), None)
    return (f[4] - f[2] * (1 - p["f"]), f[5] + f[3]) if f else (None, None)

def ride(p, entry, exit_b):
    if p["pull"] is not None and p["pull"] <= exit_b: return -1.0
    x, y = sb(p, entry)
    if not x or not y or x <= 0 or y <= 0: return None
    s = STAKE * (1 - p["f"]); q = y - x * y / (x + s); x2, y2 = sb(p, exit_b + 1); x2 += s; y2 -= q
    if y2 <= 0: return None
    return (x2 - x2 * y2 / (y2 + q * (1 - p["f"])) - STAKE - GAS) / STAKE

lines = collections.defaultdict(list)
for pid in scope:
    lines[ch[P[pid]["tok"]]].append(pid)
rows = []
for code, pids in lines.items():
    got = [pid for pid in pids if first_fleet(P[pid])]
    if len(got) < 5: continue
    offs = [first_fleet(P[pid])[0] - P[pid]["bn"] for pid in got]; med = st.median(offs)
    fronted, clean, pulled_after = [], [], 0
    for pid in pids:
        p = P[pid]; ff = first_fleet(p); lim = (ff[0] if ff else p["bn"] + med)
        out = [b for b in p["buyers"] if b[3] not in fleet and b[3] not in (p["launcher"], "?") and p["bn"] < b[0] < lim and b[2] >= 0.01]
        (fronted if out else clean).append(pid)
        if out and p["pull"] is not None and p["pull"] - out[0][0] <= 100: pulled_after += 1
    fr = [r for r in (ride(P[pid], max(P[pid]["bn"] + 2, first_fleet(P[pid])[0] - 5), first_fleet(P[pid])[0] + 1) for pid in got if first_fleet(P[pid])[0] - P[pid]["bn"] >= 4) if r is not None]
    tok0 = P[pids[0]]["tok"]
    rows.append((sum(fr) * STAKE if fr else 0, code, size[tok0], len(pids), len(got), med, fronted, clean, pulled_after, fr,
                 len({P[pid]["launcher"] for pid in pids}), sum(1 for pid in pids if P[pid]["pull"] is not None)))
rows.sort(key=lambda r: -r[0])
print(f"\nlines (token code) the fleet bought into in 5+ pools: {len(rows)}")
for eth, code, sz, n, ng, med, fronted, clean, pa, fr, nl, npull in rows[:25]:
    fb = sum(1 for pid in fronted if first_fleet(P[pid])) / len(fronted) if fronted else None
    cb = sum(1 for pid in clean if first_fleet(P[pid])) / len(clean) if clean else None
    print(f"  code {code} ({sz} B): pools {n} (launchers {nl}, pulled 2h {npull}), fleet bought in {ng} at +{med:g} | "
          f"fleet buys when fronted {fb if fb is None else round(fb, 2)} (n {len(fronted)}) vs clean {cb if cb is None else round(cb, 2)} (n {len(clean)}); "
          f"pulled within 100 of the outsider's buy {pa} | front n {len(fr)} mean {st.mean(fr) if fr else 0:+.1%} won {sum(r > 0 for r in fr)} pulled {sum(r <= -1 for r in fr)} -> {eth:+.4f} a day")
