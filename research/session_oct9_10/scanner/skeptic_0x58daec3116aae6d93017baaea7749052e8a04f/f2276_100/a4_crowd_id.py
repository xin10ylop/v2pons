"""Skeptic f2276/100 step 4: who the crowd is. Every crowd-router tx in the 66 fully attributed pools: wallets, nonces, pools per wallet,
buy and sell counts per wallet, calldata minOut (word 3) and recipient (word 1), gas fingerprint; overlap with operator A's and the
volume bot's known addresses (HANDOFF section 1, money/loop.json); the launchers vs the crowd wallets."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
pools, TX = load_sample()
cw = collections.defaultdict(lambda: {"pools": set(), "buys": 0, "sells": 0, "eth_in": 0, "eth_out": 0, "nonces": []})
mino = collections.Counter(); recip = collections.Counter(); gasfp = collections.Counter(); amounts = collections.Counter()
for pl in pools:
    for s in pl["swaps"]:
        if not s["crowd"]: continue
        t = TX[s["tx"]]; w = cw[s["from"]]; w["pools"].add(pl["pid"]); w["nonces"].append(t["nonce"])
        if s["buy"]: w["buys"] += 1; w["eth_in"] += s["eth"]
        else: w["sells"] += 1; w["eth_out"] += s["eth"]
        inp = t["input"]; mino[int(inp[10 + 64 * 3: 10 + 64 * 4], 16) == 0] += 1
        r = "0x" + inp[10 + 64 * 1 + 24: 10 + 64 * 2]
        recip[("buy" if s["buy"] else "sell", "self" if r == s["from"] else ("router" if r == CROWD else "other"))] += 1
        gasfp[(t["gp"] == t["prio"], t["gas"])] += 1
        if s["buy"]: amounts[round(int(inp[10 + 64 * 2: 10 + 64 * 3], 16) / 1e18, 4)] += 1
print("crowd wallets", len(cw), "minOut==0:", dict(mino), "recipient:", dict(recip))
print("gas fingerprint (gasPrice==prio, gas limit) top:", gasfp.most_common(5))
print("buy amounts top:", amounts.most_common(15))
npools = collections.Counter(min(len(w["pools"]), 10) for w in cw.values()); print("pools per wallet (10=10+):", sorted(npools.items()))
nonce_max = [max(w["nonces"]) for w in cw.values()]; print("wallet max nonce quantiles", q(nonce_max))
both = sum(1 for w in cw.values() if w["buys"] and w["sells"]); print("wallets that buy and sell:", both, "buy only:", sum(1 for w in cw.values() if w["buys"] and not w["sells"]),
      "sell only:", sum(1 for w in cw.values() if w["sells"] and not w["buys"]))
# known addresses
kn = set()
txt = open("/home/user/v2pons/docs/HANDOFF.md").read()
kn |= set(a.lower() for a in re.findall(r"0x[0-9a-fA-F]{40}", txt))
lp = json.load(open("/home/user/v2pons/research/session_oct9_10/money/loop.json"))
def walk(o):
    if isinstance(o, str) and re.fullmatch(r"0x[0-9a-fA-F]{40}", o): kn.add(o.lower())
    elif isinstance(o, dict): [walk(v) for v in o.values()]; [walk(k) for k in o.keys()]
    elif isinstance(o, list): [walk(v) for v in o]
walk(lp)
prefixes = set(m.lower() for m in re.findall(r"`(0x[0-9a-fA-F]{8})…", txt))
print("known full addresses", len(kn), "known 8-hex prefixes", len(prefixes))
fam_addrs = {"crowd": set(cw), "launchers": set(pl["launcher"] for pl in pools),
             "pullers": set(x["from"] for pl in pools for x in pl["pulls"] if x.get("from")),
             "other_buyers": set(s["from"] for pl in pools for s in pl["swaps"] if not s["crowd"] and s["from"]),
             "routers": set(s["to"] for pl in pools for s in pl["swaps"] if s["to"])}
for k, v in fam_addrs.items():
    hit = v & kn; hitp = [a for a in v if a[:10] in prefixes]
    print("overlap", k, len(v), "full:", sorted(hit), "prefix:", sorted(hitp))
print("launchers that are crowd wallets:", len(fam_addrs["launchers"] & fam_addrs["crowd"]), "pullers == launcher:",
      all(x["from"] == pl["launcher"] for pl in pools for x in pl["pulls"][:1]))
# does a launcher ever trade its own pool or other pools?
lt = collections.Counter()
for pl in pools:
    for s in pl["swaps"]:
        if s["from"] in fam_addrs["launchers"]: lt["own" if s["from"] == pl["launcher"] else "other pool"] += 1
print("launcher wallets trading:", dict(lt))
# the first crowd buyer per pool
fb = collections.Counter(); fbn = []
for pl in pools:
    c = [s for s in pl["swaps"] if s["crowd"] and s["buy"]]
    if c: fb[c[0]["from"]] += 1; fbn.append(TX[c[0]["tx"]]["nonce"])
print("first crowd buyer wallets:", len(fb), fb.most_common(8), "nonce q", q(fbn))
json.dump({"n_wallets": len(cw), "minout0": dict((str(k), v) for k, v in mino.items()), "recipient": {str(k): v for k, v in recip.items()},
           "pools_per_wallet": sorted(npools.items()), "nonce_q": q(nonce_max), "first_buyers": fb.most_common(20)}, open(os.path.join(HERE, "a4_crowd_id.json"), "w"), indent=1)
