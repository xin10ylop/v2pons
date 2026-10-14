"""Step 4b: choose the pools to study. Every launch of a non-known shape key with >= 15 launches (label = key); keys below 15 that pool to
>= 15 when the calldata length or the target is ignored (label 'coarse:...'); the positive control (VB 2.433, the last 24 launches);
samples of VB 3.0 (every 3rd) and VB 5.0 (every 2nd) to recheck the bot's first-buy timing to the head. Writes s05_targets.json."""
import collections
from common import *
rows = jload("s04_launches.json")
by = collections.defaultdict(list)
for r in rows:
    if not r["fam"]: by[r["key"]].append(r)
tg = []; used = set()
for k, v in by.items():
    if len(v) >= 15:
        for r in v: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam=k)); used.add(r["pid"])
def vr(v):
    v = int(v); return "0" if v == 0 else "%.4g" % (v / 1e18)
for name, kf in (("coarse-noclen", lambda r: "%s %s %s f%d ts%d v%s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["fee"], r["ts"], vr(r["v"]), r["q"])),
                 ("coarse-noto", lambda r: "%s %s %dB f%d ts%d v%s %s" % (r["ven"], r["sel"], r["clen"], r["fee"], r["ts"], vr(r["v"]), r["q"]))):
    g = collections.defaultdict(list)
    for r in rows:
        if not r["fam"] and r["pid"] not in used: g[kf(r)].append(r)
    for k, v in g.items():
        if len(v) >= 15:
            for r in v:
                if r["pid"] in used: continue
                tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam=name + ": " + k)); used.add(r["pid"])
ctl = [r for r in rows if r["fam"] == "VB 2.433"]
for r in ctl: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="CONTROL VB 2.433"))
v3 = [r for r in rows if r["fam"] == "VB 3.0"]; v5 = [r for r in rows if r["fam"] == "VB 5.0"]
for r in v3[::3]: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="SAMPLE VB 3.0"))
for r in v5[::2]: tg.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], fam="SAMPLE VB 5.0"))
jdump(tg, "s05_targets.json")
c = collections.Counter(t["fam"] for t in tg)
for k, v in c.most_common(): print("%5d %s" % (v, k))
print("targets", len(tg))
