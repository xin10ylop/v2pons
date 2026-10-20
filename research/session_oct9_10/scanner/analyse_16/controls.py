"""control families (vbot-v2.433, operator A) described with the same fields as my families: scheduled buy, pull, outsiders, capacity"""
import sys, json, statistics as st, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16")
from common16 import *
P0 = load_pools()
G = {"vbot-v2.433": [p for p in P0.values() if p["known"] == "vbot-v2.433"], "operator-A": [p for p in P0.values() if p["known"] == "operator-A"]}
ctx = Ctx([p["pid"] for v in G.values() for p in v]); T = ctx.T
DECOY = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", DUST}
out = {}
for g, ps in G.items():
    rows = []
    for p in ps:
        lb = p["launch_block"]; bs = buys(ctx, p)
        if g == "vbot-v2.433":
            sb = next((s for s in bs if is_bot_buy(T.get(s["tx"]))), None)
        else:
            sb = next((s for s in bs if -s["a0"] >= MIN_REAL), None)
        pl = first_pull(ctx, p)
        t = T.get(sb["tx"]) if sb else None
        ahead = [s for s in bs if sb and (s["bn"], s["li"]) < (sb["bn"], sb["li"])]
        ahead_real = [s for s in ahead if -s["a0"] >= MIN_REAL]
        rows.append({"sb_off": (sb["bn"] - lb) if sb else None, "sb_eth": (-sb["a0"] / 1e18) if sb else None, "sb_to": t["to"] if t else None,
                     "sb_from": t["from"] if t else None, "pull_off": (pl["bn"] - lb) if pl else None,
                     "pull_from_sb": (pl["bn"] - sb["bn"]) if pl and sb else None, "pull_by_launch_wallet": p["first_pull_from"] == p["launch_from"] if pl else None,
                     "pull_to": p["first_pull_to"], "ahead_real": len(ahead_real), "ahead_eth": sum(-s["a0"] for s in ahead) / 1e18,
                     "cap": (capacity(ctx, p, sb) or {}).get("cap_eth") if sb else None})
    sbs = [r for r in rows if r["sb_off"] is not None]; pls = [r for r in rows if r["pull_off"] is not None and r["pull_off"] <= 3000]
    o = {"count": len(ps), "per_day": round(len(ps) / DAYS, 1), "with_sched": len(sbs), "sb_off_p10_50_90": pct([r["sb_off"] for r in sbs]),
         "sb_eth_p10_50_90": pct([r["sb_eth"] for r in sbs]), "sb_to": collections.Counter(r["sb_to"] for r in sbs).most_common(3),
         "sb_from_distinct": len(set(r["sb_from"] for r in sbs)), "pulled_3000": len(pls), "pull_off_p10_50_90": pct([r["pull_off"] for r in pls]),
         "pull_from_sb_p10_50_90": pct([r["pull_from_sb"] for r in pls if r["pull_from_sb"] is not None]),
         "pull_by_launch_wallet": sum(1 for r in pls if r["pull_by_launch_wallet"]), "pull_to": collections.Counter(r["pull_to"] for r in pls).most_common(3),
         "pools_with_real_buy_ahead_of_sched": sum(1 for r in sbs if r["ahead_real"]),
         "cap_p10_50_90": pct([r["cap"] for r in sbs if r["cap"] is not None])}
    # trap test for the controls: pull delay after the scheduled buy, pools with vs without a real buy ahead of it
    w = [r["pull_from_sb"] for r in sbs if r["ahead_real"] and r["pull_from_sb"] is not None]
    wo = [r["pull_from_sb"] for r in sbs if not r["ahead_real"] and r["pull_from_sb"] is not None]
    o["trap"] = {"with_real_ahead": len(w), "pull_from_sb_with": pct(w), "without": len(wo), "pull_from_sb_without": pct(wo)}
    out[g] = o
    print(g, json.dumps(o, default=str))
json.dump(out, open(OUT + "/controls.json", "w"), indent=1, default=str)
