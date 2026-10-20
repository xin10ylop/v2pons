#!/usr/bin/env python3
"""Post-census launches (84,238,620 -> head): families, our operator, rates per hour; the engine-rule paper (independent pricer) on
every pool with a full 400-block window; the PM1444 reaction test out of sample. Also the recount check."""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from chain import T_SWAP, T_ML, W, sgn
import vprice
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
C = pickle.load(open(os.path.join(HERE, "cache_post.pkl"), "rb"))
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
print("recount equal to census set:", set(C["recount"]) == set(R), len(C["recount"]))
OP = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"; OPC = {"2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c", "42544ef5d4754816b3cfe77f3a6fb1c8eb842d6eee101f7d15c638593a3351d2"}
PMPOS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; Z = "0x" + "0" * 40
rows = []
for l in C["post"]["logs"]:
    pid = l["topics"][1]; b0 = int(l["blockNumber"], 16); d = l["data"]; t = C["txs"].get(l["transactionHash"], {})
    fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2 + 128 + 24: 2 + 192]; sp0 = W(d, 3); tick0 = sgn(W(d, 4))
    to = t.get("to"); code = C["codes"].get(to, {}) if to else {}
    if to == OP: fam = "OURS-orig"
    elif code.get("hash") in OPC: fam = "OURS-copy"
    elif t.get("sel") == "0x2fcb9108": fam = "2fcb9108-other-contract"
    elif to == PMPOS and t["inlen"] == 1444 and fee == 10000 and ts == 200 and round(t["value"], 3) == 3.0: fam = "PM1444-v3.0"
    elif to == PMPOS and t["inlen"] == 1444 and fee == 10000 and ts == 200 and round(t["value"], 3) == 5.0: fam = "PM1444-v5.0"
    elif to == PMPOS and t["inlen"] == 1444 and fee == 2500 and ts == 50: fam = "PM1444-v2.433"
    elif to == PMPOS and t["inlen"] == 2276: fam = "PM2276"
    else: fam = f"{to}|{t.get('sel')}|len{t.get('inlen')}|fee{fee}|ts{ts}|v{round(t.get('value', 0), 3)}"
    r = {"pid": pid, "b0": b0, "fam": fam, "fee": fee, "hooks": hooks, "nonce": t.get("nonce"), "from": t.get("from"), "to": to}
    ev = C["plogs"].get(pid)
    if ev is not None:
        sw = []; adds = []; rem = []
        for bn, li, t0, snd, dd, th in sorted(ev, key=lambda x: (x[0], x[1])):
            if t0 == T_SWAP:
                if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), sgn(W(dd, 4))))
            else:
                lo, hi, dl = sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))
                if dl > 0 and th == l["transactionHash"]: adds.append((lo, hi, dl))
                if dl < 0: rem.append(bn)
        L0 = sum(dl for lo, hi, dl in adds if lo < tick0 <= hi); pull = min(rem) if rem else None
        real = [s for s in sw if -s[2] >= 2 * 10**14 and s[0] - b0 <= 150]
        r.update({"liq": L0, "pull": (pull - b0) if pull else None, "trig": (real[0][0] - b0) if real else None})
        gates = []
        if hooks != Z: gates.append("hooks")
        if fee >= 10000: gates.append("fee")
        if L0 < 1e21: gates.append("liq")
        if not real: gates.append("no_trig")
        elif real[0][0] - b0 <= 6: gates.append("late")
        r["gates"] = gates
        if hooks == Z and real and real[0][0] - b0 > 6:
            x = vprice.follow(sw, sp0, L0, fee, real[0][0] + 1, 2, 1, pull); r["paper"] = x["ret"] if x else None
            x = vprice.follow(sw, sp0, L0, fee, real[0][0] + 1, 30, 1, pull); r["paper30"] = x["ret"] if x else None
        outs = [s for s in sw if 2 * 10**14 <= -s[2] < 2 * 10**16 and (pull is None or s[0] < pull)]
        r["outsider_pull_delay"] = (pull - outs[0][0]) if (outs and pull is not None) else ("nopull" if outs else None)
    rows.append(r)
hours = (C["post"]["to"] - 84238619) * 0.103 / 3600
print(f"post-census: blocks 84,238,620-{C['post']['to']:,} (~{hours:.1f} h), pools {len(rows)}")
fc = collections.Counter(r["fam"] for r in rows)
for k, n in fc.most_common(25): print(f"   {n:4d} ({n/hours:5.1f}/h) {k[:110]}")
print("our operator:", [(r["b0"], r["pid"][:10], r["fam"]) for r in rows if r["fam"].startswith("OURS") or r["fam"].startswith("2fcb")])
tr = [r for r in rows if "gates" in r and not r["gates"] and r.get("paper") is not None]
print(f"engine gates passed + paper (land1 fast hold 2): {len(tr)} pools, mean {100*st.mean([r['paper'] for r in tr]):+.2f}%, pos {sum(1 for r in tr if r['paper'] > 0)}" if tr else "none tradable")
bf = collections.defaultdict(list)
for r in tr: bf[r["fam"]].append(r["paper"])
for k, v in sorted(bf.items(), key=lambda x: -len(x[1]))[:15]: print(f"   {len(v):4d} mean {100*st.mean(v):+6.2f}% pos {sum(1 for a in v if a > 0):3d}  {k[:100]}")
pos = [r for r in rows if r.get("paper") is not None and r["paper"] > 0.005]
print("pools with paper > +0.5% (any gates):", [(r["fam"][:60], round(r["paper"], 4), r["gates"], r["nonce"]) for r in pos][:30])
for fam in ("PM1444-v3.0", "PM1444-v5.0", "PM1444-v2.433"):
    xs = [r for r in rows if r["fam"] == fam and "gates" in r]
    dl = [r["outsider_pull_delay"] for r in xs if isinstance(r.get("outsider_pull_delay"), int)]
    p30 = [r["paper30"] for r in xs if r.get("paper30") is not None]
    print(f"{fam}: {len(xs)} with logs; outsider then pull: {len(dl)} (delay p50 {st.median(dl) if dl else None}, <=20: {sum(1 for x in dl if x <= 20)}); outsider, no pull in 400: {sum(1 for r in xs if r.get('outsider_pull_delay') == 'nopull')}; "
          f"hold30 paper n {len(p30)} mean {100*st.mean(p30) if p30 else 0:+.2f}%")
n0 = collections.Counter(r["fam"][:70] for r in rows if r["nonce"] == 0)
print("nonce-0 launches by family:", n0.most_common(10))
json.dump(rows, open(os.path.join(HERE, "v6_post.json"), "w"), indent=0)
