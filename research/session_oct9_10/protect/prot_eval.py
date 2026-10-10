"""Protections against a pull before our sell: every candidate rule checked against every operator launch Oct 8 00:00 -> Oct 9 12:06
UTC (94 original-launcher + 49 copies; load_all.py) and every live trade (live_all.json).
Sections: crowd families; the engine's trigger on each original launch (fingerprint, nonce, family); every non-crowd buy of any size
and the first pull after it (the operator's size threshold); the buys around our trade window; the canary (outsider buy -> pull
lags) with a chance-coincidence estimate; our own near misses. Writes prot_eval.json; prints the tables."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
OCT9 = 83719339; ARM = 6; MAXT = 150
# ---------------------------------------------------------------- crowd families (measure.py's rule)
L = collections.defaultdict(set); N = collections.defaultdict(list)
for p in pools:
    for x in p["sw"]:
        if x["from"] in cw: L[x["from"]].add(p["pid"]); N[x["from"]].append(x["nonce"])
SPECK = next(w for w in cw if w.startswith("0xb4d43149"))
w4 = next(w for w in cw if w.startswith("0x4c45af68")); B7 = L[w4]
fam = {}
for w in cw:
    if w == SPECK: fam[w] = "speck"
    elif L[w] <= B7 and len(L[w]) >= 3: fam[w] = "B"
    elif min(N[w]) <= 3 and len(L[w]) <= 2: fam[w] = "fresh"
    elif len(L[w]) >= 20: fam[w] = "A"
    else: fam[w] = "other_fp"
print("crowd families", collections.Counter(fam.values()))
for p in pools:
    for x in p["sw"]:
        x["fam"] = fam.get(x["from"]) if x["cls"] == "crowd" else x["cls"]
OUT = {}
def t_utc(p, bn): return utc(p["ts"] + round((bn - p["b0"]) * 0.1025))
# ---------------------------------------------------------------- 1. off-fingerprint buys by crowd wallets (would a fingerprint rule skip the crowd?)
off = [(p, x) for p in pools for x in p["sw"] if x["a0"] < 0 and x["from"] in cw and not crowd_fp(x) and not is_us(x)]
print(f"\n1. buys by the 862 fingerprint wallets WITHOUT the fingerprint: {len(off)}; real-size {sum(1 for p, x in off if x['a0'] <= -REAL)}")
c = collections.Counter((x["fp"] or {}).get("gas") for p, x in off); print("   their gas limits:", c.most_common(5))
gl = collections.Counter((x["fp"] or {}).get("gas") for p in pools for x in p["sw"] if x["a0"] <= -REAL and x["cls"] == "crowd")
print("   crowd real buys by gas limit:", gl.most_common())
OUT["offfp_crowd_wallet_buys"] = len(off)
# ---------------------------------------------------------------- 2. the engine's trigger on every original launch
trig = []
for p in pools:
    if p["kind"] != "orig": continue
    b0 = p["b0"]; pb = p["pull"]["bn"] if p["pull"] else None
    rb = [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and x["cls"] != "us"]
    before_arm = [x for x in rb if x["bn"] - b0 < ARM]
    t = next((x for x in rb if ARM <= x["bn"] - b0 <= MAXT), None)
    ours = [x for x in p["sw"] if x["cls"] == "us" and x["a0"] < 0]
    if t is None or before_arm:
        trig.append({"p": p, "t": None}); continue
    tv = (t["value"] or 0) >= REAL                                                      # the feed sees it: tx value >= 0.0002 ETH
    # every non-crowd, non-us buy (any size) from launch to T+4, with its block relative to T
    nc = [{"rel": x["bn"] - t["bn"], "eth": -x["a0"] / 1e18, "from": x["from"], "value": (x["value"] or 0) / 1e18, "cls": x["cls"]}
          for x in p["sw"] if x["a0"] < 0 and x["cls"] not in ("crowd", "us") and x["bn"] <= t["bn"] + 4]
    e = {"p": p, "t": t, "T": t["bn"], "off": t["bn"] - b0, "fp": crowd_fp(t), "feed_visible": tv, "nonce": t["nonce"], "fam": t["fam"], "wallet": t["from"],
         "size": -t["a0"] / 1e18, "pull_after_T": (pb - t["bn"]) if pb else None, "ours": ours[0]["bn"] - t["bn"] if ours else None,
         "react_us": (pb - ours[0]["bn"]) if (ours and pb) else None, "nc": nc}
    trig.append(e)
TR = [e for e in trig if e["t"]]
print(f"\n2. original launches {len(trig)}; with an engine trigger {len(TR)}; trigger has the crowd fingerprint {sum(e['fp'] for e in TR)}; feed-visible (value >= 0.0002) {sum(e['feed_visible'] for e in TR)}")
print("   trigger family:", collections.Counter(e["fam"] for e in TR))
print("   trigger nonce <= 3:", sum(1 for e in TR if e["nonce"] <= 3), " by family", collections.Counter(e["fam"] for e in TR if e["nonce"] <= 3))
print("   fresh-wallet triggers (nonce <= 3): launch, pull after T, our buy after T, pull after our buy")
for e in TR:
    if e["nonce"] <= 3:
        print(f"     {utc(e['p']['ts'])} {e['p']['pid'][:10]} fam {e['fam']:5s} nonce {e['nonce']} T+{e['off']} pull T+{e['pull_after_T']} ours T+{e['ours']} react {e['react_us']}")
nonfresh = [e for e in TR if e["nonce"] > 3]
pa = sorted(e["pull_after_T"] for e in nonfresh if e["pull_after_T"] is not None and e["ours"] is None)
print(f"   non-fresh triggers we did not trade: pull after T, lowest: {pa[:8]}; n {len(pa)}")
fr = sorted(e["pull_after_T"] for e in TR if e["nonce"] <= 3 and e["ours"] is None and e["pull_after_T"] is not None)
print(f"   fresh triggers we did not trade: pull after T: {fr}")
print("   our trades (follow) by trigger kind: [time, fam, nonce, pull after our buy]")
for e in TR:
    if e["ours"] is not None:
        print(f"     {utc(e['p']['ts'])} {e['p']['pid'][:10]} {e['fam']:5s} nonce {e['nonce']:5d} our buy T+{e['ours']} pull after our buy {e['react_us']}")
OUT["triggers"] = [{"launch": utc(e["p"]["ts"]), "pid": e["p"]["pid"][:10], "fam": e["fam"], "nonce": e["nonce"], "fp": e["fp"], "feed_visible": e["feed_visible"], "off": e["off"],
                    "pull_after_T": e["pull_after_T"], "our_buy_after_T": e["ours"], "pull_after_our_buy": e["react_us"]} for e in TR]
# ---------------------------------------------------------------- 3. every non-crowd, non-us buy of any size, and the first pull after it
print("\n3. every non-crowd non-us buy before the pull (any size) -> first pull after (lag) by size bucket")
allnc = []
for p in pools:
    pb = p["pull"]["bn"] if p["pull"] else None
    for x in p["sw"]:
        if x["a0"] < 0 and x["cls"] not in ("crowd", "us") and before_pull(p, x):
            allnc.append({"p": p, "x": x, "eth": -x["a0"] / 1e18, "lag": (pb - x["bn"]) if pb else None, "who": x["from"], "cls": x["cls"], "off": x["bn"] - p["b0"],
                          "idle": not any(y["cls"] == "crowd" and x["bn"] - 20 <= y["bn"] < x["bn"] and abs(y["a0"]) >= REAL for y in p["sw"]),
                          "value": (x["value"] or 0) / 1e18})
def bucket(v):
    return "<0.0001" if v < 1e-4 else ("0.0001-0.0002" if v < 2e-4 else ">=0.0002")
for b in ("<0.0001", "0.0001-0.0002", ">=0.0002"):
    xs = [a for a in allnc if bucket(a["eth"]) == b]
    lags = sorted(a["lag"] for a in xs if a["lag"] is not None)
    print(f"   {b:14s} n {len(xs):4d} launches {len({a['p']['pid'] for a in xs}):3d}  pull within 16 blocks: {sum(1 for l in lags if l <= 16):3d}  within 60: {sum(1 for l in lags if l <= 60):3d}  lowest lags {lags[:10]}")
# the sub-0.0002 buys followed by a pull within 16: who, size, was a real-size non-crowd buy also nearby?
print("   sub-0.0002 buys with a pull within 16 blocks after (and any real-size non-crowd/us buy within 16 before that pull):")
for a in allnc:
    if a["eth"] < 2e-4 and a["lag"] is not None and a["lag"] <= 16:
        p = a["p"]; pb = p["pull"]["bn"]
        near = [(y["cls"], round(-y["a0"] / 1e18, 5), pb - y["bn"]) for y in p["sw"] if y["a0"] <= -REAL and y["cls"] in ("us", "outsider") and 0 < pb - y["bn"] <= 16]
        print(f"     {t_utc(p, a['x']['bn'])} {p['pid'][:10]} {p['kind']} {a['who'][:10]} {a['eth']:.6f} ETH +{a['off']} lag {a['lag']} idle {a['idle']} | real non-crowd near the pull: {near}")
whos = collections.Counter(a["who"][:10] for a in allnc if a["eth"] < 2e-4)
print("   sub-0.0002 buyers:", whos.most_common(8))
OUT["noncrowd_any_size"] = [{"t": t_utc(a["p"], a["x"]["bn"]), "pid": a["p"]["pid"][:10], "kind": a["p"]["kind"], "who": a["who"], "eth": a["eth"], "value": a["value"], "off": a["off"], "lag": a["lag"], "idle": a["idle"]} for a in allnc]
# ---------------------------------------------------------------- 4. non-crowd buys around the trade window on every trigger
print("\n4. non-crowd non-us buys near the trigger T (T-10..T+4), per triggered original launch")
for lo_size in (0.0, 1e-4, 2e-4):
    pre = [e for e in TR if any(-10 <= n["rel"] < 0 and n["eth"] >= lo_size for n in e["nc"])]
    win = [e for e in TR if any(0 <= n["rel"] <= 4 and n["eth"] >= lo_size for n in e["nc"])]
    print(f"   size >= {lo_size:.4f}: launches with one in T-10..T-1: {len(pre):2d}; in T..T+4: {len(win):2d}  (of {len(TR)})")
    for e in win:
        if lo_size >= 1e-4:
            print(f"      {utc(e['p']['ts'])} {e['p']['pid'][:10]} {[(n['rel'], round(n['eth'], 6), n['from'][:10]) for n in e['nc'] if 0 <= n['rel'] <= 4 and n['eth'] >= lo_size]} pull T+{e['pull_after_T']}")
first_nc_before_T = [min((n for n in e["nc"] if n["rel"] < 0 and n["eth"] >= 2e-4), key=lambda n: -n["rel"], default=None) for e in TR]
print("   real-size (>= 0.0002) non-crowd buy anywhere before the trigger:", sum(1 for f in first_nc_before_T if f))
# ---------------------------------------------------------------- 5. the canary: outsider real-size buys and the pull after them
print("\n5. CANARY: outsider buys >= 0.0002 ETH (non-crowd, non-us, before the pull) -> the first pull after; feed-visible = tx value >= 0.0002")
can = [a for a in allnc if a["eth"] >= 2e-4]
can.sort(key=lambda a: (a["p"]["b0"], a["x"]["bn"]))
for a in can:
    print(f"   {t_utc(a['p'], a['x']['bn'])} {a['p']['kind']:4s} {a['p']['pid'][:10]} {a['who'][:10]} {a['eth']:.6f} value {a['value']:.6f} +{a['off']:5d} idle {str(a['idle']):5s} lag {a['lag']}")
vis = [a for a in can if a["value"] >= 2e-4]
lv = sorted(a["lag"] for a in vis if a["lag"] is not None and a["lag"] <= 60)
print(f"   canary events (feed-visible, pull within 60): {len(lv)} lags {lv}")
print(f"   all (incl. value-0 contract buys) within 60: {sorted(a['lag'] for a in can if a['lag'] is not None and a['lag'] <= 60)}")
for thr in (3, 4, 5, 6):
    print(f"   canary lag <= {thr}: {sum(1 for l in lv if l <= thr)} (feed-visible), {sum(1 for a in can if a['lag'] is not None and a['lag'] <= thr)} (all)")
# chance coincidence: a SCHEDULED pull (no non-crowd real buy within 60 before it) landing within 1..k blocks after a buy
sched = [p for p in pools if p["pull"] and not any(y["cls"] in ("us", "outsider", "?") and y["a0"] <= -REAL and 0 <= p["pull"]["bn"] - y["bn"] <= 60 for y in p["sw"])]
cb = [(p, y) for p in sched for y in p["sw"] if y["cls"] == "crowd" and y["a0"] <= -REAL and before_pull(p, y)]
for k in (4, 6):
    hit = sum(1 for p, y in cb if 0 <= p["pull"]["bn"] - y["bn"] <= k)
    print(f"   chance: crowd real buys on {len(sched)} scheduled-pull launches with the pull within 0..{k} blocks after them: {hit} of {len(cb)} ({100 * hit / len(cb):.2f}%)")
life = [p["pull"]["bn"] - p["b0"] for p in sched]
print(f"   scheduled launch life (launch -> pull): median {st.median(life):.0f} blocks; a uniformly timed buy has the pull within 4 blocks with p = {st.mean([min(1, 5 / l) for l in life]):.4f}")
hrs = (head - 82878144) * 0.1025 / 3600
print(f"   outsider real-size buys per hour (feed-visible): {len(vis) / hrs:.2f} over {hrs:.1f} h; canary events (lag <= 60) per hour {len(lv) / hrs:.2f}")
OUT["canary"] = {"events_lags": lv, "hours": hrs, "n_visible": len(vis), "chance_crowdbuy_proxy_k4": None}
# ---------------------------------------------------------------- 6. our own trades: near misses
LA = json.load(open(HERE + "live_all.json"))["trades"]
print("\n6. our live trades: pull after our buy, sell after our buy, margin (pull - sell)")
for r in LA:
    sab = r["sell_after_buy"]; pab = r["pull_after_buy"]
    print(f"   {r['utc']} {r['pid']} buy T+{r['buy_after_T']} sell B+{sab} pull B+{pab} margin {(pab - sab) if (pab is not None and sab is not None) else None} "
          f"ret {(r['eth_out'] - r['eth_in']) / r['eth_in']:+.4f} trig {r['trigger'] and (r['trigger']['from'][:10], r['trigger']['nonce'])}")
json.dump(OUT, open(HERE + "prot_eval.json", "w"), indent=1, default=str)
