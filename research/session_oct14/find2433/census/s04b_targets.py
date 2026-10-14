"""Step 4b: choose the families to score. A launch not in a known family is grouped at the finest of five levels that reaches >= 15 launches:
  K1 the exact shape key (target, selector, calldata length, fee, tick spacing, ETH value to 4 significant digits, quote);
  K2 K1 without fee/tick spacing (lines that rotate the fee per launch);  K3 K1 without the value (lines that rotate the value);
  K4 K1 without the calldata length (name/symbol strings);  K5 (target, selector, quote, hooked) only.
Families whose fee is above 3% on every launch are listed but not scored (a front round trip cannot clear the fee).
Adds the positive control (the last 24 VB 2.433 launches) and samples of VB 3.0 (every 3rd) and VB 5.0 (every 2nd).
Writes s05_targets.json and s04b_families.json; prints s04b_targets.out."""
import collections
from common import *
rows = jload("s04_launches.json")
def vr(v):
    v = int(v); return "0" if v == 0 else "%.4g" % (v / 1e18)
H = lambda r: "hooked" if r["hook"] != E else "nohook"
LEV = [("K1", lambda r: r["key"] + " " + H(r)),
       ("K2", lambda r: "%s %s %s %dB v%s %s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["clen"], vr(r["v"]), r["q"], H(r))),
       ("K3", lambda r: "%s %s %s %dB f%d ts%d %s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["clen"], r["fee"], r["ts"], r["q"], H(r))),
       ("K4", lambda r: "%s %s %s f%d ts%d v%s %s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["fee"], r["ts"], vr(r["v"]), r["q"], H(r))),
       ("K5", lambda r: "%s %s %s %s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["q"], H(r)))]
left = [r for r in rows if not r["fam"]]
fam = {}
for name, kf in LEV:
    g = collections.defaultdict(list)
    for r in left:
        if r["pid"] not in fam: g[kf(r)].append(r)
    for k, v in g.items():
        if len(v) >= 15:
            for r in v: fam[r["pid"]] = name + " " + k
fams = collections.defaultdict(list)
for r in left:
    if r["pid"] in fam: fams[fam[r["pid"]]].append(r)
tg = []; table = []
for k, v in sorted(fams.items(), key=lambda kv: -len(kv[1])):
    lowfee = [r for r in v if r["fee"] <= 30000 or r["fee"] == 0x800000]
    span = max(1, (v[-1]["t"] - v[0]["t"]) / 3600)
    row = dict(fam=k, n=len(v), n_lowfee=len(lowfee), senders=len({r["frm"] for r in v}), txs=len({r["h"] for r in v}),
               nonce_p50=sorted(r["n"] for r in v)[len(v) // 2], first=hm(v[0]["t"]), last=hm(v[-1]["t"]), per_day=round(len(v) / span * 24, 1),
               fees=collections.Counter(r["fee"] for r in v).most_common(3), values=collections.Counter(vr(r["v"]) for r in v).most_common(3),
               gas=collections.Counter(r["gas"] for r in v).most_common(2), scored=len(lowfee) >= 15)
    table.append(row)
    if row["scored"]:
        for r in lowfee: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam=k))
for r in rows:
    if r["fam"] == "VB 2.433": tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="CONTROL VB 2.433"))
v3 = [r for r in rows if r["fam"] == "VB 3.0"]; v5 = [r for r in rows if r["fam"] == "VB 5.0"]
for r in v3[::3]: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="SAMPLE VB 3.0"))
for r in v5[::2]: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="SAMPLE VB 5.0"))
jdump(tg, "s05_targets.json"); jdump(table, "s04b_families.json")
print("unlabeled launches", len(left), "in families >= 15:", sum(t["n"] for t in table), "families", len(table), "scored", sum(t["scored"] for t in table))
for t in table:
    print("%-4s %4d (lowfee %4d) senders %4d txs %4d nonce50 %6d %5.0f/day %s..%s fees %s values %s gas %s  %s" % ("YES" if t["scored"] else "no", t["n"], t["n_lowfee"], t["senders"], t["txs"], t["nonce_p50"], t["per_day"], t["first"], t["last"], t["fees"], t["values"], t["gas"], t["fam"]))
c = collections.Counter(t["fam"] for t in tg)
print("\ntargets", len(tg), "pools in", len(c), "groups")
