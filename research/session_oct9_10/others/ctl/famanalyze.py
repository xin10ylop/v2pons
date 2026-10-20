#!/usr/bin/env python3
"""The original-launcher family (94 pools): crowd (fingerprint, wallets, recurring), deployer (nonce, next tx = pull?), reaction (pull after
the first outsider buy), per sub-scheme. Writes famanalyze.json."""
import sys, os, json, pickle, collections, statistics as st, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, SCR)
from chain import T_SWAP, T_ML, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = [json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))]
o = sorted([r for r in R if r["ours"] == "orig"], key=lambda r: r["b0"])
pl = pickle.load(open(os.path.join(HERE, "..", "cache_plogs.pkl"), "rb"))
C = pickle.load(open(os.path.join(HERE, "cache_famtx.pkl"), "rb")); TX = C["tx"]
P = json.load(open(os.path.join(SCR, "money", "pots.json")))["pots"]; A = set(P["A_7.01"]["crowd"]); B = set(P["B_4.86"]["crowd"])
US = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
def kind(t):
    if t["from"] == US or t["to"] == RELAY: return "OURS"
    if t["to"] == UR and t["inlen"] == 1124 and t["prio"] == 20_000_000: return "SIG"
    return "OTHER"
rows = []; wallet_pools = collections.Counter(); sig_gas = collections.Counter(); sig_value = []
for r in o:
    pb = r["b0"] + r["pull"] if r["pull"] is not None else None
    end = pb if pb is not None else r["b0"] + 3000
    buys = []
    for bn, li, t0, snd, d, th in sorted(pl[r["pid"]], key=lambda x: (x[0], x[1])):
        if t0 == T_SWAP and s128(W(d, 0)) <= -2 * 10**14 and bn <= end:
            t = TX.get(th)
            if t: buys.append((bn - r["b0"], kind(t), t["from"], -s128(W(d, 0)) / 1e18, t))
    sigw = {b[2] for b in buys if b[1] == "SIG"}
    for w in sigw: wallet_pools[w] += 1
    for b in buys:
        if b[1] == "SIG": sig_gas[b[4]["gas"]] += 1; sig_value.append(b[3])
    nA = len(sigw & A); nB = len(sigw & B)
    pt = C["pull"].get(r.get("pull_tx"))
    out_b = [b for b in buys if b[1] != "SIG"]
    first_out = out_b[0] if out_b else None
    sig_b = [b for b in buys if b[1] == "SIG"]
    rows.append({"b0": r["b0"], "pid": r["pid"], "deployer": r["from"], "nonce": r["nonce"], "fee": r["fee"], "value": r["value"], "trig": r.get("trig"), "pull": r["pull"],
                 "paper": (r.get("paper") or {}).get("land1_fast"), "gates": r["gates"],
                 "n_real_before_pull": len(buys), "n_sig": len(sig_b), "n_ours": sum(1 for b in buys if b[1] == "OURS"), "n_other": sum(1 for b in buys if b[1] == "OTHER"),
                 "sig_wallets": len(sigw), "crowdA": nA, "crowdB": nB,
                 "first_sig": sig_b[0][0] if sig_b else None, "last_sig": sig_b[-1][0] if sig_b else None,
                 "first_outsider": (first_out[0], first_out[1], first_out[2], round(first_out[3], 5)) if first_out else None,
                 "pull_after_first_outsider": (r["pull"] - first_out[0]) if (first_out and r["pull"] is not None) else None,
                 "pull_after_last_buy": (r["pull"] - buys[-1][0]) if (buys and r["pull"] is not None) else None,
                 "pull_from_deployer": (pt["from"] == r["from"].lower()) if pt else None, "pull_nonce": pt["nonce"] if pt else None,
                 "pull_to": pt["to"] if pt else None, "pull_sel": pt["sel"] if pt else None, "deployer_nonce_now": C["nonce"].get(r["from"].lower()),
                 "outsiders": [(b[0], b[1], b[2][:10], round(b[3], 5)) for b in out_b][:8]})
def scheme(x):
    if x["crowdA"] >= 3 and x["crowdA"] >= 2 * x["crowdB"]: return "A"
    if x["crowdB"] >= 3: return "B"
    if x["n_sig"] == 0: return "no_crowd"
    return "other_crowd"
for x in rows: x["scheme"] = scheme(x)
recurring = {w for w, n in wallet_pools.items() if n >= 2}
print("SIG wallets", len(wallet_pools), "recurring (>=2 pools)", len(recurring), "in crowd A", len(recurring & A), "in crowd B", len(recurring & B), "neither", len(recurring - A - B))
print("SIG gas limits", sig_gas.most_common(5), "SIG buy size p10/50/90", [round(sorted(sig_value)[int(q * (len(sig_value) - 1))], 4) for q in (.1, .5, .9)])
allb = sum(x["n_real_before_pull"] for x in rows); print("real buys before pull", allb, "SIG", sum(x["n_sig"] for x in rows), "OURS", sum(x["n_ours"] for x in rows), "OTHER", sum(x["n_other"] for x in rows))
nw = collections.Counter(x["nonce"] for x in rows); print("launch nonce", dict(nw))
print("pull from deployer", collections.Counter(x["pull_from_deployer"] for x in rows), "pull nonce - launch nonce", collections.Counter((x["pull_nonce"] - x["nonce"]) if x["pull_nonce"] is not None else None for x in rows))
print("pull to/sel", collections.Counter((x["pull_to"], x["pull_sel"]) for x in rows))
print("deployer nonce now", collections.Counter(x["deployer_nonce_now"] for x in rows))
for sc in ("A", "B", "other_crowd", "no_crowd"):
    xs = [x for x in rows if x["scheme"] == sc]
    if not xs: continue
    pp = [x["paper"]["ret"] for x in xs if x["paper"] and not x["gates"]]
    print(f"\nscheme {sc}: {len(xs)} pools, blocks {xs[0]['b0']}-{xs[-1]['b0']}, fee p10/50/90 {[sorted(x['fee'] for x in xs)[int(q*(len(xs)-1))] for q in (.1,.5,.9)]}, value p50 {st.median(x['value'] for x in xs):.2f}"
          f", trig {sorted(x['trig'] for x in xs if x['trig'] is not None)}"
          f"\n   pull {sorted(x['pull'] for x in xs if x['pull'] is not None)} no-pull-in-3000 {sum(1 for x in xs if x['pull'] is None)}"
          f"\n   tradable paper land1_fast n {len(pp)} mean {100*st.mean(pp) if pp else 0:+.2f}% pos {sum(1 for v in pp if v > 0)}")
    print("   pools with an outsider (non-crowd, incl. ours) real buy before the pull:", sum(1 for x in xs if x["first_outsider"]),
          "| pull after it (blocks):", sorted(x["pull_after_first_outsider"] for x in xs if x["pull_after_first_outsider"] is not None))
    print("   pull after the last real buy:", sorted(x["pull_after_last_buy"] for x in xs if x["pull_after_last_buy"] is not None))
json.dump({"rows": rows, "wallet_pools": wallet_pools, "recurring": sorted(recurring)}, open(os.path.join(HERE, "famanalyze.json"), "w"), indent=1)
print()
for x in rows:
    print(x["b0"], x["pid"][:10], x["scheme"], "n", x["nonce"], "fee", x["fee"], "v", round(x["value"], 2), "trig", x["trig"], "pull", x["pull"], "sig", x["n_sig"], "A", x["crowdA"], "B", x["crowdB"], "ours", x["n_ours"], "oth", x["n_other"],
          "| 1st out", x["first_outsider"], "pull-after", x["pull_after_first_outsider"], "| pullnonce", x["pull_nonce"], "now", x["deployer_nonce_now"])
