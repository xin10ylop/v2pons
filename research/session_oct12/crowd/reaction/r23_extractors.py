"""wallets that do what we would do: buy before the crowd (>= 0.0005 ETH, not the + 1 bot) and sell into its wave at a profit (a sell
within 60 blocks after the crowd's first real buy returning more ETH than the position cost). Per such wallet, its pools in time order:
was the crowd's first real buy by + 78 in its later pools (after its first profitable exit) as often as in all pools launched in the same
span? A learning operator would stop sending the crowd (or pull early) once an extractor is known."""
from rlib import *
P = sorted(load(), key=lambda p: p["ts"]); BOT1 = "0x776e5a2a"
ext = collections.defaultdict(list)
for p in P:
    for o in p["outs"]:
        if o["w"].startswith(BOT1): continue
        w = p
        sells = [s for s in p["sw"] if s["k"] == "other" and s["from"] == o["w"] and s["dq"] < 0]
        into = p["frb"] is not None and any(p["frb"] <= s["off"] <= p["frb"] + 60 for s in sells)
        prof = o["eth_out"] > o["eth_in"] and into
        ext[o["w"]].append({"ts": p["ts"], "pool": p["pool"], "first": o["first_off"], "eth": o["eth_pre"], "prof": prof, "frb": p["frb"], "pull": p["pull"],
                            "held": o["held_at_crowd"], "ret": o["eth_out"] / o["eth_in"] - 1 if o["eth_in"] else None})
X = {w: v for w, v in ext.items() if sum(1 for x in v if x["prof"]) >= 2}
print(f"outside wallets that sold into the crowd's wave at a profit in >= 2 pools: {len(X)} (of {len(ext)} outside wallets that bought before the crowd)")
def base(t0, t1):
    g = [p for p in P if t0 <= p["ts"] <= t1]
    return (sum(1 for p in g if p["frb"] is not None and p["frb"] <= 78) / len(g), sum(1 for p in g if p["pull"] is not None and p["pull"] <= 150) / len(g), len(g)) if g else (None, None, 0)
tot_o = tot_e = 0.0; n_after = 0
for w, v in sorted(X.items(), key=lambda kv: -len(kv[1])):
    v = sorted(v, key=lambda x: x["ts"]); i0 = next(i for i, x in enumerate(v) if x["prof"])
    later = v[i0 + 1:]
    rs = [x["ret"] for x in v if x["ret"] is not None]
    if later:
        c = sum(1 for x in later if x["frb"] is not None and x["frb"] <= 78); bc, bp, bn = base(later[0]["ts"], later[-1]["ts"])
        pl = sum(1 for x in later if x["pull"] is not None and x["pull"] <= 150)
        tot_o += c; tot_e += bc * len(later); n_after += len(later)
        print(f"  {w[:12]} pools {len(v):>3} profitable exits {sum(1 for x in v if x['prof']):>3} median ret {pct(rs,.5)*100:+.1f}% first buy offs med {pct([x['first'] for x in v],.5)} ETH med {pct([x['eth'] for x in v],.5):.4f};"
              f" after its first profitable exit: {len(later)} pools, crowd by +78 {c} ({c/len(later):.2f}, all pools in that span {bc:.2f}), pulled <=150 {pl} ({pl/len(later):.2f}, all {bp:.2f})")
    else:
        print(f"  {w[:12]} pools {len(v):>3} profitable exits {sum(1 for x in v if x['prof']):>3}: no later pool")
if n_after:
    print(f"pooled over these wallets' later pools: crowd by +78 observed {tot_o:.0f} of {n_after}, expected {tot_e:.1f} from all pools of the same spans (O/E {tot_o/tot_e:.2f})")
