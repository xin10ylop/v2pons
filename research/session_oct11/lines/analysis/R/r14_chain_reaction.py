"""Chain (last 6 h) reaction evidence (task 3).
Wallet classes: bot (r11), ours, sentinel 0xe71a69f4, decoy = a buy before the bot's first buy of 0.0049-0.0050 ETH (the 0.00495 decoy) or from a
wallet seen buying in >= 5 line pools of the window at a fixed small size (dust; 0x8cf143dd / the 0x65050a9b router also counted), stranger =
everything else. Lists every stranger buy with its pull lag (r14_cases.txt); compares pull timing with / without a stranger after T; our pools
where the bot's buy did not land (its reverted transaction found in the blocks); the 3.0 line's pulls after a stranger before / after the bot.
Census 3.0 new-regime cases are added for the 3.0 line."""
import pickle, collections, json
from common import *
from rpc import batch
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]; botw = D["botw"]
DUST_EXTRA = {"0x8cf143dd"}; DUST_TO = {"0x65050a9b"}
seen = collections.defaultdict(set); sizes = collections.defaultdict(list)
for p in P:
    for s in p["sw"]:
        if s["buy"] and s["who"] == "w": seen[s["eoa"]].add(p["pid"]); sizes[s["eoa"]].append(round(s["q"] / 1e18, 6))
recurring = {w for w, ps in seen.items() if len(ps) >= 5}
print("recurring non-bot wallets (>= 5 pools):", [(w[:10], len(seen[w]), collections.Counter(sizes[w]).most_common(2)) for w in sorted(recurring, key=lambda w: -len(seen[w]))])
def cls(p, s):
    if s["who"] != "w": return s["who"]
    if s["eoa"][:10] in DUST_EXTRA or s["to"][:10] in DUST_TO or s["eoa"] in recurring: return "dust"
    if (p["T"] is None or s["off"] <= p["T"]) and 0.0049e18 <= s["q"] <= 0.0050e18: return "decoy"
    return "stranger"
cases = []; rows = []
for p in P:
    T = p["T"]; sw = p["sw"]
    for s in sw: s["cls"] = cls(p, s)
    ib = next((i for i, s in enumerate(sw) if s["who"] == "bot"), None)
    bots = [s for s in sw if s["who"] == "bot"]
    b2 = bots[1]["off"] if len(bots) > 1 else None
    after = [s for i, s in enumerate(sw) if ib is not None and i > ib and s["buy"] and s["cls"] == "stranger" and s["off"] < (b2 if b2 else T + 60)]
    after_any = [s for i, s in enumerate(sw) if ib is not None and i > ib and s["buy"] and s["cls"] == "stranger"]
    before = [s for i, s in enumerate(sw) if s["buy"] and s["cls"] == "stranger" and (ib is None or i < ib)]
    rows.append({"p": p, "after": after, "after_any": after_any, "before": before, "b2": b2})
    for kind, ss in (("AFTER-T", after_any), ("BEFORE-T", before)):
        for s in ss:
            lag = None if p["pull"] is None else p["pull"] - s["off"]
            cases.append(f"{kind:8s} {p['regime']:20s} {utc(p['ts'])} pool {p['pid'][:12]} ours {int(p['ours'])} T {T} stranger {s['eoa'][:10]} (nonce {s['nonce']}) via {s['to'][:10]} buy {s['q']/1e18:.6f} at +{s['off']}"
                         f" | 2nd bot buy {b2} | pull {p['pull']} (lag {lag}) span {p['span']}")
open("r14_cases.txt", "w").write("\n".join(cases) + "\n")
def stat(rr):
    v = [None if r["p"]["pull"] is None or r["p"]["T"] is None else r["p"]["pull"] - r["p"]["T"] for r in rr]
    k = lambda d: sum(1 for x in v if x is not None and x <= d)
    return f"n {len(rr):3d} pulled by T+10 {k(10):3d}, T+30 {k(30):3d}, T+60 {k(60):3d}, T+400 {k(400):3d}; pull-T p50 {pct([x for x in v if x is not None], .5)}"
print("\n== pull timing, untouched pools with a bot buy: a stranger after T (before the 2nd bot buy) vs none")
for reg in ("2.433 fee2500", "2.433 fee5000<16:28", "2.433 fee5000>=16:28", "3.0 new"):
    G = [r for r in rows if r["p"]["regime"] == reg and not r["p"]["ours"] and r["p"]["T"] is not None]
    print(f"{reg:21s} STRANGER-after-T {stat([r for r in G if r['after']])}\n{'':21s} no stranger      {stat([r for r in G if not r['after'] and not r['before']])}\n{'':21s} stranger before  {stat([r for r in G if r['before'] and not r['after']])}")
print("\n== stranger buys after T: pull lag after the buy (all chain pools incl. no-2nd-buy window)")
lags = collections.defaultdict(list)
for r in rows:
    if r["p"]["ours"]: continue
    for s in r["after_any"]: lags[r["p"]["line"]].append(None if r["p"]["pull"] is None else r["p"]["pull"] - s["off"])
for k, v in lags.items(): print(k, "n", len(v), "lags:", sorted(v, key=lambda x: (x is None, x)))
print("\n== stranger buys before T (fronts): pull lag after the buy")
lags = collections.defaultdict(list)
for r in rows:
    if r["p"]["ours"]: continue
    for s in r["before"][-1:]: lags[(r["p"]["regime"], r["p"]["T"] is not None)].append(None if r["p"]["pull"] is None else r["p"]["pull"] - s["off"])
for k, v in sorted(lags.items()): print(k, "n", len(v), "lags:", sorted(v, key=lambda x: (x is None, x)))
# our pools today: did the bot buy land? find its reverted transaction in the blocks L+1..L+20 when no bot Swap
print("\n== our pools (2.433): bot Swap present? pull offset; reverted bot tx found in blocks")
ours = [p for p in P if p["ours"]]
need = [p for p in ours if not any(s["who"] == "bot" for s in p["sw"] if s["off"] <= 30)]
blk = {}
bl = sorted(set(b for p in need for b in range(p["lb"] + 1, p["lb"] + 21)))
res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in bl]) if bl else []
for b, r in zip(bl, res): blk[b] = r
for p in sorted(ours, key=lambda p: p["lb"]):
    our = [s for s in p["sw"] if s["who"] == "ours"]
    bot = [s for s in p["sw"] if s["who"] == "bot"]
    rev = []
    if p in need:
        tok = p["token"][2:].lower()
        for b in range(p["lb"] + 1, p["lb"] + 21):
            for t in (blk.get(b) or {}).get("transactions", []):
                if (t.get("to") or "").lower() == BOT and tok in (t.get("input") or "").lower(): rev.append(b - p["lb"])
    print(f"{utc(p['ts'])} {p['line']} fee {p['fee']} our buys {[(s['off'], round(s['q']/1e18,4)) for s in our if s['buy']]} our sells {[s['off'] for s in our if not s['buy']]} "
          f"bot swaps {[(s['off'], round(s['q']/1e18,4)) for s in bot[:3]]} bot txs w/o Swap (reverted) at {rev} | pull {p['pull']}")
# census 3.0 new regime: strangers before / after T and pull lag
C = pickle.load(open("cpools.pkl", "rb"))
print("\n== census 3.0 new regime (>= 04:22 Oct 11): one-off wallets buying before / after T, pull lag")
for p in C:
    if p["line"] != "3.0" or p["ts"] < NEW30: continue
    ib = next((i for i, s in enumerate(p["sw"]) if s["who"] == "bot"), None)
    for i, s in enumerate(p["sw"]):
        if s["buy"] and s["who"] == "x" and s["eoa"] != SENTINEL:
            kind = "before" if ib is None or i < ib else "after"
            print(f"  {utc(p['ts'])} pool {p['pool'][:12]} {kind} T {p['T']} {s['eoa'][:10]} via {s['to'][:10]} {s['q']/1e18:.6f} at +{s['off']} pull {p['pull']} lag {None if p['pull'] is None else p['pull']-s['off']}")
