#!/usr/bin/env python3
"""react1380.py: does operator A's 1,380 B line turn on a TRUE outsider? Pools of the line (modifyLiquidities 1,380 B, 4,655 B tokens) in
the given buyerlab dumps. crowd = a wallet buying in 3+ pools across ALL the dumps; outsider = a wallet buying (0.001 ETH+) in only 1-2 pools,
not the launcher. For each pool with an outsider: its entry offset (and whether it came before the crowd's first buy), blocks to the pull
(and pulled within 5 s?), crowd net native after its buy vs clean pools after the same offset, and whether it sold and at what return.
Read-only (dumps, census, caches)."""
import sys, json, os, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
DUMPS = sys.argv[1].split(","); DAYS = sys.argv[2].split(",")
lc = json.load(open(os.path.join(HERE, "out/struct_launch_rh.json"))); cc = json.load(open(os.path.join(HERE, "out/token_code_rh.json")))
created = {}
for d in DAYS:
    for k, tok, bn, tx, nin in json.load(open(os.path.join(HERE, f"out/rh_{d}_00.json")))["chains"]["rh"]["created"]:
        created[k] = tx
allp = {}
for f in DUMPS:
    allp.update(json.load(open(f))["pools"])
cnt = collections.Counter()
for p in allp.values():
    for w in {s[3] for s in p.get("swaps", []) if s[1] > 0 and s[3] not in ("?", None)}:
        cnt[w] += 1
crowd = {w for w, n in cnt.items() if n >= 3}
line = []
for k, p in allp.items():
    t = lc.get(created.get(k))
    if t and t[1].startswith("0x58daec31") and t[2] == "0xdd46508f" and t[3] == 1380 and cc.get(p["tok"], ["?", 0])[1] == 4655:
        line.append((k, p))
def net_after(p, off):
    return sum(s[1] for s in p["swaps"] if s[3] in crowd and s[0] - p["bn"] > off)
out = []; clean = []
for k, p in line:
    sw = sorted(p.get("swaps", [])); bn = p["bn"]; pull = p["pull"]
    c0 = next((s[0] - bn for s in sw if s[3] in crowd and s[1] >= 0.005), None)
    o = next((s for s in sw if s[1] >= 0.001 and s[3] not in crowd and s[3] not in ("?", None) and s[3] != p["launcher"]), None)
    if o is None:
        clean.append((k, p)); continue
    w = o[3]; off = o[0] - bn
    nin = sum(s[1] for s in sw if s[3] == w and s[1] > 0); tb = sum(s[2] for s in sw if s[3] == w and s[1] > 0)
    nout = sum(-s[1] for s in sw if s[3] == w and s[1] < 0); ts = sum(-s[2] for s in sw if s[3] == w and s[1] < 0)
    ref = [net_after(q, off) for _, q in clean] or [0]
    out.append({"id": k, "off": off, "early": c0 is None or off < c0, "c0": c0, "eth": o[1], "lag": (pull - o[0]) if pull is not None else None,
                "net_after": net_after(p, off), "sold": ts >= 0.8 * tb and tb > 0, "ret": (nout / nin - 1) if nin > 0 and tb > 0 and ts >= 0.8 * tb else None})
# clean reference computed after all pools are sorted into clean/outsider
for r in out:
    ref = [net_after(q, r["off"]) for _, q in clean]
    r["ref"] = st.median(ref) if ref else None
print(f"{len(line)} pools of the line; crowd (3+ pools anywhere) {len(crowd)}; pools with a true outsider {len(out)}, clean {len(clean)}")
lags = [r["lag"] for r in out if r["lag"] is not None]
print(f"pull within 5 s (50 blocks) of the outsider's buy: {sum(1 for l in lags if l <= 50)}/{len(out)}; not pulled within 2 h: {sum(1 for r in out if r['lag'] is None)}/{len(out)}")
cp = sorted(q["pull"] - q["bn"] for _, q in clean if q["pull"] is not None)
print(f"clean pools: pull median +{st.median(cp) if cp else '-'}; p10 +{cp[len(cp)//10] if cp else '-'}")
print(f"outsiders that sold 80%+: {sum(1 for r in out if r['sold'])}/{len(out)}; their median return {st.median([r['ret'] for r in out if r['ret'] is not None]):+.1%}" if any(r['ret'] is not None for r in out) else f"outsiders that sold 80%+: 0/{len(out)}")
print("\neach outsider pool: entry offset (before the crowd?), ETH | pull lag | crowd net native after it vs clean pools after the same offset | sold? return")
for r in sorted(out, key=lambda r: r["off"]):
    print(f"  {r['id'][:14]} +{r['off']:<5} {'EARLY' if r['early'] else 'late '} {r['eth']:.4f} | lag {r['lag']} | net after {r['net_after']:+.2f} vs clean {r['ref'] if r['ref'] is None else format(r['ref'], '+.2f')} | sold {r['sold']} {'' if r['ret'] is None else format(r['ret'], '+.0%')}")
