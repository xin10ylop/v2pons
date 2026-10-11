"""graduations: factory events cdb72f15 (curve full) / a0a18f5b / 0a44ef75 (migration) joined with the creates and the census's pools (offline)."""
import json, collections, bisect, time
from krpc import *
G = json.load(open(os.path.join(DATA, "factory_other_logs.json")))["logs"]
creates = {}
for line in open(os.path.join(CEN, "cache", "bonding.jsonl")):
    r = json.loads(line)
    for l in r["logs"]:
        creates[A(l["topics"][1])] = {"bn": l["bn"], "tx": l["tx"], "token": A(l["topics"][1]), "curve": A(l["topics"][2]), "creator": A(l["topics"][3]), "quote": W(l["data"], 0), "thr": W(l["data"], 2)}
for r in jl_read(os.path.join(DATA, "creates_new.jsonl")): creates.setdefault(r["token"], {"bn": r["bn"], "tx": r["tx"], "token": r["token"], "curve": r["curve"], "creator": r["creator"], "quote": r["w"][0], "thr": r["w"][2]})
by = collections.defaultdict(dict)
for l in G:
    t = l["topics"][0][:10]; tok = A(l["topics"][1]) if len(l["topics"]) > 1 else None
    by[tok].setdefault(t, []).append({"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "w": [W(l["data"], i) for i in range((len(l["data"]) - 2) // 64)], "topics": [A(x) for x in l["topics"][1:]]})
grads = {k: v for k, v in by.items() if "0xcdb72f15" in v}
print("graduated tokens", len(grads), "with a create in our window", sum(1 for k in grads if k in creates))
# other factory events
oth = collections.Counter(l["topics"][0][:10] for l in G)
print(oth)
for t in ("0x308c390e", "0xbd886f85", "0x67d517ee", "0x060d1992", "0x7f119e44"):
    x = [l for l in G if l["topics"][0][:10] == t][:2]
    for l in x: print(t, int(l["blockNumber"], 16), [A(y) for y in l["topics"][1:]], l["data"][:200])
# is topic1 of 308c390e a token of a create? which positions
c308 = [l for l in G if l["topics"][0][:10] == "0x308c390e"]
pos = collections.Counter()
for l in c308:
    for i, y in enumerate(l["topics"][1:]):
        if A(y) in creates: pos[f"token@{i}"] += 1
        if A(y) in {c["curve"] for c in []}: pass
print("308c390e topic positions that are tokens", pos, len(c308))
out = []
for tok, v in grads.items():
    c = creates.get(tok)
    g = v["0xcdb72f15"][0]; m = v.get("0x0a44ef75", [{}])[0]; bnr = v.get("0xa0a18f5b", [{}])[0]
    out.append({"token": tok, "create_bn": c and c["bn"], "curve": c and c["curve"], "creator": c and c["creator"], "quote": c and c["quote"], "thr": c and c["thr"],
                "full_bn": g["bn"], "full_tx": g["tx"], "full_w": g["w"], "mig_bn": m.get("bn"), "mig_tx": m.get("tx"), "mig_w": m.get("w"), "burn_w": bnr.get("w")})
json.dump(out, open(os.path.join(OUT, "k12_grads.json"), "w"), indent=0)
d = sorted(o["full_bn"] - o["create_bn"] for o in out if o["create_bn"])
print("blocks create->full: n", len(d), "p10/25/50/75/90", [d[int(len(d) * q)] for q in (0.1, 0.25, 0.5, 0.75, 0.9)])
dm = sorted(o["mig_bn"] - o["full_bn"] for o in out if o["mig_bn"])
print("blocks full->migration: p0/10/50/90/max", dm[0], [dm[int(len(dm) * q)] for q in (0.1, 0.5, 0.9)], dm[-1])
print("quote of graduated", collections.Counter(o["quote"] for o in out))
print("full_w examples", [o["full_w"] for o in out[:3]], "mig_w", [o["mig_w"] for o in out[:3]], "burn", [o["burn_w"] for o in out[:3]])
