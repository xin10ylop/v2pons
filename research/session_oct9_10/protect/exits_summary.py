"""compact tables from exits_bt.json (fast landing = as every live sell), and where V0's edge over V1 comes from"""
import json, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "exits_bt.json")))
S = D["summary"]; LAGS = ["2", "3", "4", "5", "6"]; TL = ["T3", "T4", "T5", "T6", "T7"]
names = ["V0 current", "V1 deadline B+1", "V2 split 1/2 at B+1", "V3 TP 1%/0.3%", "V4d deadline at T+3", "V4a quiet-out", "V4b TP 0% at B+1", "V4c quiet-out + TP 0%"]
for sp in ("fast", "slow"):
    for stake in ("0.0012", "0.1"):
        for land in (1, 2, 3):
            v0 = S[f"{stake}|trig+{land}|{sp}|V0 current"]["paper"]["mean"]
            print(f"\n{stake} ETH, buy at T+{land}, sell lands send+{1 if sp == 'fast' else 2} ({sp})")
            print(f"  {'variant':24s} {'paper':>7s} {'median':>7s} {'ex-outl':>7s} {'vs V0':>6s}  TP%  last-land  safe-if-lag>=  " + "  ".join(f"lag{l}: mean  pf" for l in LAGS))
            for n in names:
                s = S[f"{stake}|trig+{land}|{sp}|{n}"]
                safe = next((int(l) for l in LAGS if all(s[m]["pull_first"] + s[m]["partly_pulled"] == s["6"]["pull_first"] + s["6"]["partly_pulled"] for m in LAGS[LAGS.index(l):])), None)
                cells = "  ".join(f"{100 * s[l]['mean']:+8.2f}% {s[l]['pull_first']:2d}{'+' + str(s[l]['partly_pulled']) if s[l]['partly_pulled'] else '  '}" for l in LAGS)
                print(f"  {n:24s} {100 * s['paper']['mean']:+6.2f}% {100 * s['paper']['median']:+6.2f}% {100 * s['paper']['mean_ex_outlier']:+6.2f}% {100 * (s['paper']['mean'] - v0):+5.2f}  {100 * s['tp_rate']:3.0f}%  B+{s['max_land_after_buy']}  {s.get('land_dist')}  {safe}   {cells}")
            print("  trigger-anchored reaction (pull at T+k): " + " | ".join(f"{n.split()[0]} " + " ".join(f"T+{l[1:]}:{100 * S[f'{stake}|trig+{land}|{sp}|{n}'][l]['mean']:+.1f}%/{S[f'{stake}|trig+{land}|{sp}|{n}'][l]['pull_first']}" for l in TL) for n in names[:3]))
# where V0 beats V1 at T+1, 0.1 ETH fast
print("\nper launch, 0.1 ETH, buy T+1, fast: V0 vs V1 (paper)")
d = collections.Counter(); diffs = []
for r in D["per_launch"]:
    if r["stake"] == 0.1 and r["land"] == 1 and r["dl"] == 1:
        a = r["variants"]["V0 current"]; b = r["variants"]["V1 deadline B+1"]
        diffs.append((a["paper"] - b["paper"], r["block"], a["sends"], round(a["paper"], 4), round(b["paper"], 4)))
diffs.sort(reverse=True)
for x in diffs[:12]:
    print("  ", x)
print("  sum of V0-V1 over 46:", round(sum(x[0] for x in diffs), 4), " from trades V0 sold at B+2 (lands B+3):", round(sum(x[0] for x in diffs if x[2][0][0] == 2), 4))
