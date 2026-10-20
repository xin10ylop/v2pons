"""Skeptic step 2: who trades before the bot's first buy (buys and sells), by (to, from) and size; per-sub counts."""
import json, collections
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
rows = json.load(open(HERE + "/rows.json"))
for sub in ("v3.0", "v5.0"):
    R = [r for r in rows if r["sub"] == sub]
    c = collections.Counter(); pools = collections.defaultdict(set); eth = collections.defaultdict(list); offs = collections.defaultdict(list)
    for r in R:
        for x in r["pre_bot"]:
            k = (x["to"], x["from"] if x["to"] != "0x8876789976decbfcbbbe364623c63652db8c0904" or x["eth"] > 1e-5 else "UR-dust", "buy" if x["buy"] else "sell")
            c[k] += 1; pools[k].add(r["pid"]); eth[k].append(x["eth"]); offs[k].append(x["off"])
    print(sub, len(R))
    for k, n in c.most_common(40):
        e = sorted(eth[k]); o = sorted(offs[k])
        print(f"  {k[0]} {k[1]} {k[2]} n={n} pools={len(pools[k])} eth {e[0]:.3g}/{e[len(e)//2]:.3g}/{e[-1]:.3g} off {o[0]}/{o[len(o)//2]}/{o[-1]}")
