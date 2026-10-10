"""List every launch (orig + copy) Oct 8 00:00 -> Oct 9 ~12:06 with family (A/B/copy/fresh/no_crowd_buy, same rule as protect/measure.py),
deployer, launch block, pull block/tx. Writes launches.json."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import load_all
from classify import annotate, REAL, before_pull, utc
pools, head = load_all(); cw = annotate(pools)
L = collections.defaultdict(set); N = collections.defaultdict(list)
for p in pools:
    for x in p["sw"]:
        if x["from"] in cw: L[x["from"]].add(p["pid"]); N[x["from"]].append(x["nonce"])
SPECK = next(w for w in cw if w.startswith("0xb4d43149"))
w4 = next(w for w in cw if w.startswith("0x4c45af68")); B7 = L[w4]
fam = {}
for w in cw:
    if w == SPECK: fam[w] = "speck"
    elif L[w] <= B7 and len(L[w]) >= 3: fam[w] = "B"
    elif min(N[w]) <= 3 and len(L[w]) <= 2: fam[w] = "fresh"
    elif len(L[w]) >= 20: fam[w] = "A"
    else: fam[w] = "other_fp"
out = []
for p in pools:
    c = collections.Counter(fam.get(x["from"]) for x in p["sw"] if x["cls"] == "crowd" and x["a0"] <= -REAL and before_pull(p, x))
    f = "copy" if p["kind"] == "copy" else (c.most_common(1)[0][0] if c else "no_crowd_buy")
    pl = p["pull"]
    out.append({"pid": p["pid"], "utc": utc(p["ts"]), "kind": p["kind"], "family": f, "fee": p["fee"], "b0": p["b0"], "deployer": p["deployer"],
                "launch_tx": p["m"].get("tx"), "launch_to": p["m"].get("to"), "pull_bn": pl["bn"] if pl else None, "pull_tx": pl["tx"] if pl else None,
                "pull_from": pl["from"] if pl else None, "pull_to": pl["to"] if pl else None, "pull_sel": pl["sel"] if pl else None})
json.dump({"head": head, "launches": out, "fam": fam}, open("launches.json", "w"))
print(collections.Counter(x["family"] for x in out))
for x in out:
    if x["family"] == "B": print(x["utc"], x["pid"][:10], x["fee"], x["deployer"], x["pull_bn"], x["pull_from"])
print(sum(1 for x in out if x["pull_from"] and x["pull_from"] != x["deployer"]), "pulls not by deployer")
