"""Skeptic 1: the reaction regime with my own classes (k01) and replay (k02).
Regime pools: (a) our 5 real fills; (b) an outside wallet (class 'out': not router, launcher, router EOA or ours) bought >= 0.001 ETH at
or before T+10 and still held at T+2 (bought <= T+2) or bought in (T+2, T+10] (it then holds from at most 8 blocks after our entry).
'Held' = no sell by that wallet before E + 62 (else listed as 'sold at ...'). T = the engine's trigger (first router buy >= 0.005 ETH
within 400 blocks; Teng), the analyst's T shown when it differs.
For each regime pool: our entry E, every router buy after E up to the pull or E + 200 (offset from E, ETH), the pull (offset from E),
and the gross return at 0.002 ETH for hold 5..60 and the analyst's best take-profits (strict pull rule; lenient in brackets if different)."""
import json, collections
from k02_sim import *
D = load(); P = D["pools"]; HEAD = D["head"]
HOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60]
def out_holders(p, T, upto):
    """out-class wallets with a >= 0.001 ETH buy at offset <= upto (before the pull): (wallet, first such buy, first later sell or None)"""
    res = {}
    for s in p["sw"]:
        if s["c"] != "out" or not s["buy"] or s["eth_wei"] < 10 ** 15 or s["off"] > upto: continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        if s["from"] in res: continue
        sl = next((x for x in p["sw"] if not x["buy"] and x["from"] == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"])), None)
        res[s["from"]] = (s, sl)
    return res
def fmt(x): return "  -100%" if x <= -1 else f"{x:+7.2%}"
rows = []
for p in sorted(P, key=lambda p: p["ts"]):
    T = p["Teng"]; ours = any(s["c"] == "ours" and s["buy"] for s in p["sw"])
    if T is None and not ours: continue
    if ours and T is None: T = p["T"]
    if p["sqrtP0"] != 792280926924313289846529216293289 or p["sw"][0]["liq"] != 100000088127620690885293: continue
    if p["pull"] is not None and p["pull"] <= T + 2: continue
    if HEAD - p["lb"] < T + 70: continue
    hs = out_holders(p, T, T + 10)
    E = p["lb"] + T + 2
    held = {w: (b, s) for w, (b, s) in hs.items() if (s is None or s["bn"] > E) and b["off"] <= T + 10}
    if not ours and not held: continue
    sim = Sim(p, T, 2 * 10 ** 15)
    E = sim.E
    rb = [(s["bn"] - E, round(s["eth_wei"] / 1e18, 4)) for s in p["sw"] if s["c"] == "router" and s["buy"] and s["bn"] > E
          and s["bn"] <= E + 200 and (p["pullpos"] is None or (s["bn"], s["li"]) < tuple(p["pullpos"]))]
    rs = [(s["bn"] - E, round(s["eth_wei"] / 1e18, 4)) for s in p["sw"] if s["c"] == "router" and not s["buy"] and E < s["bn"] <= E + 200]
    r = {"pid": p["pid"], "ts": p["ts"], "T": T, "Tan": p["T"], "ours": ours, "E_off": E - p["lb"],
         "holders": [(w[:10], b["off"] - T, round(b["eth_wei"] / 1e18, 5), None if s is None else s["off"] - T) for w, (b, s) in held.items()],
         "pull_E": None if p["pullpos"] is None else p["pullpos"][0] - E, "router_buys": rb, "router_sells": rs,
         "hold": {N: sim.hold(N) for N in HOLDS}, "hold_len": {N: sim.hold(N, True) for N in HOLDS},
         "tp": {f"tp{int(tp * 100)} cap{c}": sim.tp(tp, c) for tp in (0.02, 0.04, 0.06, 0.08) for c in (30, 45, 50, 60)}}
    rows.append(r)
json.dump(rows, open(os.path.join(H, "k04_regime.json"), "w"))
import time
for r in rows:
    print(f"\n{time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))} {r['pid'][:10]} {'OURS' if r['ours'] else 'holder'} T(engine) launch+{r['T']}"
          f"{'' if r['T'] == r['Tan'] else ' (analyst T ' + str(r['Tan']) + ')'} entry launch+{r['E_off']} pull at entry+{r['pull_E']}")
    for h in r["holders"]: print(f"   outsider {h[0]} bought {h[2]} ETH at T{h[1]:+d}, first sell {'never' if h[3] is None else f'T+{h[3]}'}")
    print(f"   router buys after our entry (entry+offset, ETH): {r['router_buys'][:12]}{' ...' if len(r['router_buys']) > 12 else ''}")
    if r["router_sells"]: print(f"   router sells: {r['router_sells'][:6]}")
    print("   hold " + " ".join(f"{N}:{fmt(r['hold'][N])}" for N in HOLDS))
    print("   tp   " + " ".join(f"{k}:{fmt(v[0])}@{v[1]}" for k, v in r["tp"].items() if k.endswith(("cap30", "cap50"))))
