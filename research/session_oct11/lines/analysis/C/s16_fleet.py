"""tok:0f34e3b5: the swapExactETHForTokens fleet (router 0x89e5db8b, 7ff36ab5, 228 bytes, tip 0). Wallet reuse, nonce, buy size, buys per
pool, spacing, total ETH, the price path, the pull (offset, who, share pulled before/after the fleet's buys), and the funding of fleet
wallets found in the census's full-block cache (cache/fblocks.jsonl: a transfer to the wallet or a call carrying its address)."""
import sys, os, pickle, json, statistics as st, subprocess
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
R = load_rows(); FP = fam_pools(R); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb")); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def q(xs, ps=(.1, .5, .9), f="%.4g"):
    xs = sorted(xs); return "/".join(f % xs[min(len(xs)-1, int(p*len(xs)))] for p in ps) if xs else "-"
rs = FP["tok:0f34e3b5"]
fleet = {}; nonces = []; sizes = []; per_pool_n = []; per_pool_eth = []; gaps = []; price_mult = []; first_fleet_off = []
wallet_pools = defaultdict(set)
for r in rs:
    o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]; n = 0; tot = 0.0; offs = []
    X = Y = 0; px0 = None; pull_off = r["first_pull_off"]
    for e in o["ev"]:
        if e[0] == "mi": X += e[6 + qs]; Y += e[7 - qs]; px0 = px0 or X / Y; continue
        if e[0] == "b": break
        qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
        X += qin - qout; Y += tin - tout
        if qin >= 5e15 and tout > 0:
            n += 1; tot += qin / 1e18; offs.append(e[1] - lb); sizes.append(qin / 1e18)
            t = T.get(e[-1])
            if t and t["selector"] == "7ff36ab5" and t["calldata_len"] == 228:
                fleet[t["from"]] = t; nonces.append(t["nonce"]); wallet_pools[t["from"]].add(r["pool"])
    per_pool_n.append(n); per_pool_eth.append(tot)
    gaps += [b - a for a, b in zip(offs, offs[1:])]
    if px0 and Y: price_mult.append((X / Y) / px0)
print(f"pools {len(rs)}; fleet wallets seen (fetched txs) {len(fleet)}; pools per fleet wallet {Counter(len(v) for v in wallet_pools.values()).most_common(3)}")
print(f"fleet tx nonce {Counter(nonces).most_common(5)}  buy size ETH p10/50/90 {q(sizes)}  real buys per pool before the pull (3,000 blocks) p10/50/90 {q(per_pool_n, f='%d')}")
print(f"ETH bought per pool before the pull p10/50/90 {q(per_pool_eth)}  blocks between real buys p10/50/90 {q(gaps, f='%d')}  price at the pull or +3000 / launch price p10/50/90 {q(price_mult)}")
pl = [r for r in rs if r["n_pulls"]]
print(f"pulled {len(pl)}/{len(rs)} at p10/50/90 {q([r['first_pull_off'] for r in pl], f='%d')}  by the launch wallet {sum(1 for r in pl if r['pull_by_launch_wallet'])}  via {Counter((r['pulls'][0][2][:10], r['pulls'][0][3]) for r in pl).most_common(2)}  pull before frb {sum(1 for r in pl if r['pull_before_frb'])}")
print(f"real buys before the pull in pulled pools p10/50/90 {q([n for r, n in zip(rs, per_pool_n) if r['n_pulls']], f='%d')} vs never-pulled pools (whole window) {q([n for r, n in zip(rs, per_pool_n) if not r['n_pulls']], f='%d')}")
gp = [t.get("gas_price") for t in fleet.values() if t.get("gas_price")]
print(f"fleet gas price p10/50/90 {q(gp, f='%d')}  type {Counter(t.get('type') for t in fleet.values()).most_common(3)}")
# launch wallets: nonce, gas
lw = [r["launch"] for r in rs]
print(f"launch wallets {len(set(l['from'] for l in lw))} nonce {Counter(l['nonce'] for l in lw).most_common(3)} value {Counter(l['value_eth'] for l in lw).most_common(2)}")
# funding of fleet wallets in the full-block cache: grep the wallets (no 0x) in fblocks.jsonl
pat = os.path.join(OUT, "fleet_pat.txt")
open(pat, "w").write("\n".join(w[2:] for w in fleet) + "\n")
hits = subprocess.run(["grep", "-F", "-f", pat, os.path.join(CEN, "cache", "fblocks.jsonl")], capture_output=True, text=True).stdout.splitlines()
fund = []; seen_blocks = 0
fl = set(fleet)
for line in hits:
    b = json.loads(line); seen_blocks += 1
    for tx in b["txs"]:
        h, frm, to, val, nonce, inp = tx[0], tx[1], tx[2], tx[3], tx[4], tx[5]
        if to in fl and val and int(val) > 0 and frm not in fl:
            fund.append(("direct", frm, to, int(val) / 1e18, b["bn"], nonce))
        elif frm not in fl and inp and any(w[2:] in inp for w in fl if w[2:] in line):
            ws = [w for w in fl if w[2:] in inp]
            fund.append(("calldata", frm, to, int(val or 0) / 1e18, b["bn"], nonce, len(ws)))
print(f"fblocks lines mentioning a fleet wallet {seen_blocks}; funding-like txs {len(fund)}")
print(" funders:", Counter(f[1] for f in fund).most_common(5), " via:", Counter((f[0], f[2]) for f in fund).most_common(5))
print(" values:", q([f[3] for f in fund]) if fund else "-")
pickle.dump({"fund": fund, "fleet": list(fleet)}, open(os.path.join(OUT, "fleet_funding.pkl"), "wb"))
