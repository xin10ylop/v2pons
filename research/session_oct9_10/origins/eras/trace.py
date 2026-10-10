"""money trace around one launch, from full-block scans of [bn-PRE, bn+5] and [pull, pull+POST]:
   creator funding chain (up to 4 hops back), crowd wallets' funders, the top (dispatcher) wallet's inputs (sweep: from previous creator / crowd?),
   after the pull: creator payout destination, its inputs (crowd leftovers) and outputs.
   usage: trace.py <launch block|hash prefix|sender prefix> [PRE] [POST] [tag]"""
from B import *
X = launches(); R = json.load(open(D + "p1.json"))
CRE = {x["from"]: x for x in X}
arg = sys.argv[1]; PRE = int(sys.argv[2]) if len(sys.argv) > 2 else 700; POST = int(sys.argv[3]) if len(sys.argv) > 3 else 450
tag = sys.argv[4] if len(sys.argv) > 4 else ""
x = next(v for v in X if (arg.isdigit() and v["bn"] == int(arg)) or v["h"].startswith(arg) or (not arg.isdigit() and v["from"].startswith(arg)))
r = R[x["h"]]; bn = x["bn"]; P = r["pull"]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
cnt = collections.Counter()
for y in X:
    for t in {t for n, t, h in R[y["h"]]["buys"]}: cnt[t] += 1
buyers = []
for n, t, h in r["buys"]:
    if t not in SK and t != x["from"] and t not in buyers: buyers.append(t)
_PC = set(t for v in json.load(open(D + "p6_crowds.json")).values() for t in v["crowd"])
try:
    _PP = json.load(open(S + "money/pots.json"))["pots"]; _PC |= set(_PP["A_7.01"]["crowd"]) | set(_PP["B_4.86"]["crowd"])
except Exception: pass
crowd = [b for b in buyers if cnt[b] < 40 or b in _PC]; snip = [b for b in buyers if b not in crowd]
out = {"launch": x["h"], "bn": bn, "time": T(bn), "creator": x["from"], "nonce": x["nonce"], "value": x["value"], "pull": P, "tag": tag,
       "buyers": len(buyers), "crowd": crowd, "snipers": [(s, cnt[s]) for s in snip]}
print(f"=== {tag} launch {bn} ({T(bn)}) creator {x['from']} n{x['nonce']} value {x['value']} pull {P} (+{(P or 0)-bn}) buyers {len(buyers)} (crowd {len(crowd)}, frequent {len(snip)})", flush=True)
A = rows(bn - PRE, bn + 5)
def ins(a, rr): return [q for q in rr if q[4] == a and int(q[5]) > 0]
def outs(a, rr): return [q for q in rr if q[3] == a and int(q[5]) > 0]
# creator funding chain
chain = []; cur = x["from"]
for hop in range(5):
    i = [q for q in ins(cur, A) if q[0] <= (chain[-1][0] if chain else bn)]
    if not i: break
    q = max(i, key=lambda q: int(q[5])); chain.append(q); print("   fund hop", hop, fmt(q, bn))
    o = outs(q[3], A)
    if len(o) > 3: break   # reached a fan-out wallet (dispatcher)
    cur = q[3]
out["fund_chain"] = [[q[0], q[3], q[4], int(q[5]) / 1e18, q[6]] for q in chain]
top = chain[-1][3] if chain else None
# crowd funding
cf = collections.Counter(); hop2 = collections.Counter(); cnon = collections.Counter()
for b in crowd:
    i = ins(b, A)
    if not i: cf["(none in window)"] += 1; continue
    q = i[-1]; cf[q[3]] += 1
    if q[3] != top:
        j = ins(q[3], A)
        hop2[j[-1][3] if j else "(none)"] += 1
print("   crowd funders:", cf.most_common(4), "| 2nd hop:", hop2.most_common(3))
out["crowd_funders"] = cf.most_common(6); out["crowd_hop2"] = hop2.most_common(4)
if top:
    o = outs(top, A); i = ins(top, A)
    print(f"   TOP {top}: outs {len(o)} total {sum(int(q[5]) for q in o)/1e18:.4f} nonces {o[0][6] if o else '-'}..{o[-1][6] if o else '-'} | ins {len(i)} total {sum(int(q[5]) for q in i)/1e18:.4f}")
    for q in sorted(i, key=lambda q: -int(q[5]))[:4]:
        print("      in:", fmt(q, bn), "<- prev creator %d %s" % (CRE[q[3]]["bn"], T(CRE[q[3]]["bn"])) if q[3] in CRE else "")
    prevc = [q for q in i if q[3] in CRE]
    out["top"] = {"addr": top, "n_out": len(o), "out_total": sum(int(q[5]) for q in o) / 1e18, "n_in": len(i), "in_total": sum(int(q[5]) for q in i) / 1e18,
                  "in_from_prev_creators": [[q[3], CRE[q[3]]["bn"], int(q[5]) / 1e18] for q in prevc],
                  "in_top": [[q[3], int(q[5]) / 1e18, q[6], q[0]] for q in sorted(i, key=lambda q: -int(q[5]))[:6]]}
    # one more level: where did the top's largest input come from (if it is not a crowd leftover)
    if i:
        big = max(i, key=lambda q: int(q[5])); j = ins(big[3], A)
        for q in j[-3:]: print("      in-of-in:", fmt(q, bn))
        out["top"]["big_in_src"] = [[q[3], int(q[5]) / 1e18, q[6], q[0]] for q in j[-3:]]
if P:
    Bq = rows(P, P + POST)
    po = outs(x["from"], Bq)
    for q in po: print("   payout:", fmt(q, P))
    out["payout"] = [[q[0] - P, q[4], int(q[5]) / 1e18, q[6]] for q in po]
    if po:
        s = max(po, key=lambda q: int(q[5]))[4]
        si = ins(s, Bq); so = outs(s, Bq)
        fromcrowd = [q for q in si if q[3] in crowd]
        print(f"   SWEEP {s}: ins {len(si)} total {sum(int(q[5]) for q in si)/1e18:.4f} (from this crowd {len(fromcrowd)} = {sum(int(q[5]) for q in fromcrowd)/1e18:.4f})")
        for q in so[:5]: print("      out:", fmt(q, P))
        out["sweep"] = {"addr": s, "n_in": len(si), "in_total": sum(int(q[5]) for q in si) / 1e18, "from_crowd": len(fromcrowd),
                        "outs": [[q[0] - P, q[4], int(q[5]) / 1e18, q[6]] for q in so[:40]], "n_out": len(so)}
        if so:
            d2 = max(so, key=lambda q: int(q[5]))[4]; o2 = outs(d2, Bq)
            nxt = [q for q in Bq if q[3] == d2]
            print(f"      next hop {d2}: outs {len(o2)} total {sum(int(q[5]) for q in o2)/1e18:.4f}")
            out["sweep"]["next"] = {"addr": d2, "n_out": len(o2), "out_total": sum(int(q[5]) for q in o2) / 1e18, "first_outs": [[q[0] - P, q[4], int(q[5]) / 1e18, q[6]] for q in o2[:3]]}
    co = collections.Counter(q[4] for q in Bq if q[3] in crowd and int(q[5]) > 0)
    print("   crowd outflows after pull:", co.most_common(3))
    out["crowd_out"] = co.most_common(4)
with open(D + "traces.jsonl", "a") as f: f.write(json.dumps(out) + "\n")
