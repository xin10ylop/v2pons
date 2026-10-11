"""Census: pools of the V3 crowd line where a stranger (not crowd-shaped, not the launch wallet) bought >= X ETH in the first 10 blocks
(where our +1/+2 buy would sit), against the rest: does the crowd still come (frb by +80, ETH bought in [+2, +80]), does the operator
pull earlier (first pull <= 80, <= 150), and what does the rule return? (tx shapes from analyst C's tx.pkl: the first 12 swaps of every
pool are fetched, so the first 10 blocks are covered.)"""
import pickle, sys, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb")); T = pickle.load(open(C + "/tx.pkl", "rb"))
L = [r for r in R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; CROWD = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
def buys(r):
    o = E[r["pool"]]; qs = r["quote_side"]
    return [(e[1] - o["lb"], e[7] if qs == 0 else e[8], e) for e in o["ev"] if e[0] == "s" and (e[7] if qs == 0 else e[8]) > 0]
def crowd(e):
    t = T.get(e[-1]); return bool(t) and (t["selector"], t["calldata_len"]) in CROWD and (t["to"] or "") != UR
for X in (0.001, 0.003, 0.005):
    grp = {True: [], False: []}
    for r in L:
        early = [(off, dq, e) for off, dq, e in buys(r) if off <= 10 and dq >= X * 1e18 and not crowd(e) and (T.get(e[-1]) or {}).get("from") != r["launch"]["from"]]
        bs = buys(r); real = [off for off, dq, e in bs if dq >= 5e15 and off >= 2]
        trig = [off for off in real]; b = trig[0] + 20 if trig and trig[0] + 20 <= 80 else 80
        x = replay(r, E[r["pool"]], 2, b, 0.0058)
        eth80 = sum(dq for off, dq, e in bs if 2 <= off <= 80 and crowd(e)) / 1e18
        grp[bool(early)].append({"frb80": bool(real) and real[0] <= 80, "eth80": eth80, "pull": r["first_pull_off"], "ret": x["ret"] if x["ok"] else None})
    print(f"stranger buy >= {X} ETH in blocks 0..10:")
    for k, v in grp.items():
        if not v: continue
        p80 = sum(1 for z in v if z["pull"] is not None and z["pull"] <= 80); p150 = sum(1 for z in v if z["pull"] is not None and z["pull"] <= 150)
        rs = [z["ret"] for z in v if z["ret"] is not None]
        print(f"  {'with' if k else 'without':>7}: n {len(v)}  crowd real buy by +80 {sum(z['frb80'] for z in v)/len(v):.2f}  crowd ETH in [+2,+80] mean {st.mean(z['eth80'] for z in v):.3f} "
              f"median {st.median(z['eth80'] for z in v):.3f}  pulled <= +80 {p80}  <= +150 {p150} ({p150/len(v):.2f})  rule mean {st.mean(rs)*100:+.2f}%")
