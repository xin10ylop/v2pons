"""s05: the exit test table. For each family launch: buys (Portal TokenBought for the token, from the tx receipts), the holder each buy
paid (the tx's net token receiver), the class of the buy (dev / crowd / outsider; the crowd is re-derived as in the grid's g07:
a buy fingerprint tx.to:selector:calldata_len:priority used in >= max(3, 10% of launches) launches by >= 5 wallets, Portal-direct),
and every later token move out of that holder (TokenSold through the Portal or any Transfer out). One row per (token, holder).
-> data/s05_holders.json, prints the table."""
import sys, os, json, collections as C
sys.path.insert(0, os.path.dirname(__file__))
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
Z = "0x" + "0" * 40
TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TA = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
TX2 = "0xc4f02cd43bed595a7c3ee13e0ee1ec639470a7a0f374837ee7b910779d55f5ba"
HOLD = 200; EARLY = 100
fam = {r["token"]: r for r in json.load(open(os.path.join(D, "s02_family.json")))["family"]}
TX = {}
for l in open(os.path.join(D, "tx_cache.jsonl")):
    j = json.loads(l); TX[j["h"]] = j
LOGS = {}
for l in open(os.path.join(D, "toklogs_cache.jsonl")):
    j = json.loads(l); LOGS[j["token"]] = j
HEAD = min(j["to"] for j in LOGS.values())
def fp(t): return f"{t['to'][:10]}:{t['sel']}:{t['clen']}:{t['prio']}"
# --- pass 1: buys per token, fingerprints
buys = C.defaultdict(list)          # token -> [(off, b, ti, li, tx, buyer_evt, amount, eth, fee)]
sells = C.defaultdict(list)
anomalies = C.Counter()
for tok, j in LOGS.items():
    L = fam[tok]["b"]
    tr = [x for x in j["logs"] if x[4][0] == TT]; tx2 = [x for x in j["logs"] if x[4][0] == TX2]
    if len(tr) != len(tx2): anomalies["transfer_vs_c4f0_count"] += 1
    other = C.Counter(x[4][0] for x in j["logs"] if x[4][0] not in (TT, TA, TX2))
    for k, v in other.items(): anomalies["topic " + k[:10]] += v
    for h in sorted(set(x[3] for x in j["logs"])):
        t = TX.get(h)
        if not t: anomalies["missing_tx"] += 1; continue
        for kind, li, tk, who, amt, eth, fee, pp in t["portal"]:
            if tk != tok: continue
            row = (t["b"] - L, t["b"], t["ti"], li, h, who, amt, eth, fee)
            (buys if kind == "B" else sells)[tok].append(row)
# fingerprints of non-dev buys after the launch tx
fpl = C.defaultdict(set); fpw = C.defaultdict(set)
for tok, bl in buys.items():
    f = fam[tok]; dev = {f["from"], f["creator"]}
    for off, b, ti, li, h, who, amt, eth, fee in bl:
        t = TX[h]
        if h == f["tx"] or t["from"] in dev or who in dev: continue
        fpl[fp(t)].add(tok); fpw[fp(t)].add(t["from"])
NL = len(LOGS)
CROWD_RESEARCH = {f"{PORTAL[:10]}:ef7ec2e7:228:{p}" for p in (74750000, 71500000, 600000000)}
crowd_fp = {k for k in fpl if len(fpl[k]) >= max(3, 0.1 * NL) and len(fpw[k]) >= 5 and k.startswith(PORTAL[:10])}
print("launches", NL, "head", HEAD)
print("fingerprints (launches, wallets) top 14:")
for k in sorted(fpl, key=lambda k: -len(fpl[k]))[:14]:
    print(f"  {k:48s} {len(fpl[k]):3d} {len(fpw[k]):4d}", "CROWD" if k in crowd_fp else "", "research-crowd" if k in CROWD_RESEARCH else "")
CROWD = crowd_fp | CROWD_RESEARCH
crowd_wallets = set()
for k in CROWD: crowd_wallets |= fpw.get(k, set())
# --- pass 2: holders and their exits
def transfers(tok):
    out = []
    for b, ti, li, h, tps, d in LOGS[tok]["logs"]:
        if tps[0] != TT: continue
        out.append((b, ti, li, h, "0x" + tps[1][-40:], "0x" + tps[2][-40:], int(d, 16)))
    return sorted(out)
rows = []
for tok in LOGS:
    f = fam[tok]; L = f["b"]; dev = {f["from"], f["creator"]}
    TR = transfers(tok)
    bytx = C.defaultdict(list)
    for x in TR: bytx[x[3]].append(x)
    holders = {}                       # holder -> dict
    for off, b, ti, li, h, who, amt, eth, fee in sorted(buys[tok]):
        t = TX[h]
        net = C.Counter()
        for x in bytx[h]: net[x[5]] += x[6]; net[x[4]] -= x[6]
        recv = [a for a, v in net.items() if v > 0 and a not in (PORTAL, Z)]
        if not recv: anomalies["buy_without_receiver"] += 1; continue
        holder = max(recv, key=lambda a: net[a])
        if h == f["tx"]: cls = "dev"
        elif t["from"] in dev or who in dev or holder in dev: cls = "dev"
        elif fp(t) in CROWD: cls = "crowd"
        elif t["from"] in crowd_wallets: cls = "crowd_wallet_other_fp"
        else: cls = "outsider"
        o = holders.setdefault(holder, {"token": tok, "holder": holder, "L": L, "buys": [], "cls": set(), "eoa": set(), "via": set()})
        o["buys"].append({"off": off, "b": b, "h": h, "eth": eth, "amt": amt, "fp": fp(t), "from": t["from"], "who": who})
        o["cls"].add(cls); o["eoa"].add(t["from"]); o["via"].add(t["to"])
    # exits: every Transfer out of the holder after its first buy
    for a, o in holders.items():
        b0 = o["buys"][0]["b"]
        outs = [x for x in TR if x[4] == a and x[0] >= b0]
        ins = [x for x in TR if x[5] == a]
        bal = sum(x[6] for x in ins) - sum(x[6] for x in TR if x[4] == a)
        o["first_out"] = None; o["outs"] = []
        for x in outs:
            t = TX.get(x[3]) or {}
            sold = any(k == "S" and tk == tok for k, li, tk, *_ in t.get("portal", []))
            o["outs"].append({"b": x[0], "off": x[0] - L, "after_buy": x[0] - b0, "to": x[5], "amt": x[6], "h": x[3], "sold_portal": sold,
                              "tx_from": t.get("from"), "tx_to": t.get("to"), "sel": t.get("sel"), "status": t.get("status")})
        if o["outs"]: o["first_out"] = o["outs"][0]["after_buy"]
        o["bal_logs"] = bal; o["n_in"] = len(ins)
        o["cls"] = sorted(o["cls"]); o["eoa"] = sorted(o["eoa"]); o["via"] = sorted(o["via"])
        o["first_off"] = o["buys"][0]["off"]
        o["can_hold"] = b0 + HOLD <= HEAD
        rows.append(o)
json.dump({"head": HEAD, "crowd_fp": sorted(CROWD), "crowd_fp_derived": sorted(crowd_fp), "anomalies": dict(anomalies), "rows": rows},
          open(os.path.join(D, "s05_holders.json"), "w"))
print("anomalies", dict(anomalies))
def cat(o):
    if not o["can_hold"]: return "too recent"
    fo = o["first_out"]
    if fo is None: return "still holding (no move out)"
    if fo < HOLD: return "moved out < 200 blocks"
    return "held >= 200, then moved out"
for grp, sel in (("OUTSIDERS bought < +100", lambda o: o["cls"] == ["outsider"] and o["first_off"] < EARLY),
                 ("OUTSIDERS bought >= +100", lambda o: o["cls"] == ["outsider"] and o["first_off"] >= EARLY),
                 ("CROWD", lambda o: "crowd" in o["cls"]), ("DEV", lambda o: "dev" in o["cls"]),
                 ("other/mixed", lambda o: o["cls"] not in (["outsider"],) and "crowd" not in o["cls"] and "dev" not in o["cls"])):
    g = [o for o in rows if sel(o)]
    c = C.Counter(cat(o) for o in g)
    print(f"\n{grp}: {len(g)} (token, holder) pairs in {len(set(o['token'] for o in g))} launches, {len(set(o['holder'] for o in g))} addresses")
    for k, v in c.most_common(): print(f"   {k:32s} {v}")
    sold = [o for o in g if o["outs"]]
    print("   exits via Portal sell:", sum(1 for o in sold if o["outs"][0]["sold_portal"]), "via transfer:", sum(1 for o in sold if not o["outs"][0]["sold_portal"]))
