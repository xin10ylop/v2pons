#!/usr/bin/env python3
"""Build the census outputs from cache/ (no RPC): pools.jsonl (one row per pool: launch, codes, first swaps, pulls, behavioural features),
families_tok.json / families_lc.json / families_fund.json / families_tokm.json, overlap.json, summary.json. See README.md for the schema."""
import sys, os, time, bisect, statistics as stt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evload import *

OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; OUR_RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
REAL = 0.005          # a "real" buy, ETH-equivalent
OUT_MIN = 0.0001      # an outsider buy counts from this size (ETH-equivalent); smaller = dust
OUT_POOLS = 3         # an outsider = an EOA seen swapping in fewer than 3 pools of the census (fetched transactions)
REACT = 30            # a pull within REACT blocks after an outsider buy = a reaction
NF = 12
t0 = time.time()
def el(): return f"{time.time() - t0:.0f}s"

W_ = window(); G = sorted((int(k), v) for k, v in jget("tsgrid.json").items()); GB = [g[0] for g in G]
def ts_of(bn):
    i = bisect.bisect_left(GB, bn)
    if i <= 0: return G[0][1]
    if i >= len(G): return G[-1][1] + (bn - G[-1][0]) * 0.1026
    (b0, t0_), (b1, t1) = G[i - 1], G[i]
    return round(t0_ + (t1 - t0_) * (bn - b0) / (b1 - b0), 1)
utc = lambda ts: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))

P = base_pools(); log("pools", len(P), el())
TL = {x["hash"]: x for x in jl_iter("tx_launch.jsonl")}
TS = {x["hash"]: x for x in jl_iter("tx_swap.jsonl")}
for x in jl_iter("tx_swap_b.jsonl"): TS[x["hash"]] = x
R = {x["hash"]: x for x in jl_iter("rcpt.jsonl")}
C = {x["addr"]: x for x in jl_iter("codes.jsonl")}
FUND = {}
for x in jl_iter("funding.jsonl"): FUND[x["wallet"]] = x
for x in jl_iter("funding_cache.jsonl"): FUND.setdefault(x["wallet"], x)
FUND2 = {}
for x in jl_iter("funding_hop2.jsonl"): FUND2[x["wallet"]] = x
log("txs launch", len(TL), "swap", len(TS), "codes", len(C), "funding", len(FUND), el())
def tx(h): return TS.get(h) or TL.get(h)
ntx = collections.Counter(p["launch_tx"] for p in P)
QF = {"ETH": 1e-18, "WETH": 1e-18, "USDG2": ETH_PER_USDG * 1e-18, "USDG": ETH_PER_USDG * 1e-6}


def known_fp(p, t, tgt_hash):
    """annotation only: the first census's fingerprints (not used for grouping)"""
    if not t: return None
    v = t["value_wei"]; to = t["to"]; s = t["selector"]; n = t["calldata_len"]
    if to == "0x3194e32622c5d860a0572c74edda99dcfd8fc827" or s == "2fcb9108" or (tgt_hash or "").startswith(("2793923d", "42544ef5")): return "operatorA"
    if to == POSM and s == "ac9650d8" and n == 1444:
        if v == 2433328500000000000: return "vbot-v2.433"
        if p["fee"] == 10000 and p["tick_spacing"] == 200 and v in (3 * 10 ** 18, 5 * 10 ** 18): return f"vbot-v{v // 10 ** 18}.0"
        if p["fee"] in (100, 500) and 1.5e18 <= v <= 2.5e18: return "smallpot"
    if to == POSM and s == "ac9650d8" and n == 2276 and v == 0 and p["fee"] == 100: return "C-1"
    if to == PM and s == "6276cbbe" and n == 196 and p["fee"] == 500: return "C-2"
    if (tgt_hash or "").startswith("f07d1c53") and s == "e1e75b94": return "hooked-f07d1c53"
    return None


# ---------------- per pool: events -> swaps/pulls with transactions
rows = {}; swaps_by_pool = {}
seen_pools = collections.defaultdict(set); bought_pools = collections.defaultdict(set)
EV = load_events(); log("events loaded", len(EV), el())
for p in P:
    i = p["pool"]; t = TL.get(p["launch_tx"]); o = EV.get(i)
    created = (R.get(p["launch_tx"]) or {}).get("contract")
    tgt = (t or {}).get("to") or created
    tc = C.get(tgt) or {}; kc = C.get(p["token"]) or {}
    lb = p["launch_block"]; ts = ts_of(lb); qf = QF[p["quote"]]
    r = {"dex": p["dex"], "pool": i, "factory": p.get("factory", PM), "token": p["token"], "quote": p["quote"], "quote_side": p["quote_side"],
         "quote_pair": p["quote_pair"], "fee": p["fee"], "tick_spacing": p["tick_spacing"], "hooks": p.get("hooks"), "sqrt_p0": p.get("sqrt_p0"),
         "tick0": p.get("tick0"), "launch_block": lb, "launch_ts": ts, "launch_utc": utc(ts), "launch_tx": p["launch_tx"], "launch_ti": p["ti"]}
    r["launch"] = None if not t else {
        "from": t["from"], "to": t["to"], "nonce": t["nonce"], "value_wei": t["value_wei"], "value_eth": round(t["value_wei"] / 1e18, 9),
        "selector": t["selector"], "calldata_len": t["calldata_len"], "gas_price": t["gas_price"], "max_prio": t["max_prio"], "type": t["type"],
        "created_contract": created, "target": tgt, "target_code_hash": tc.get("h"), "target_code_size": tc.get("size"), "n_pools_in_tx": ntx[p["launch_tx"]]}
    r["token_code"] = {"hash": kc.get("h"), "mask32": kc.get("m"), "skel": kc.get("sk"), "size": kc.get("size")}
    r["known_fp"] = known_fp(p, t, tc.get("h"))
    if o is None:
        r["has_events"] = False; rows[i] = r; continue
    sw, adds, pulls = norm(p, o)
    r["has_events"] = True; r["ev_to"] = o["ev_to"]; r["ev_complete"] = o["ev_to"] >= lb + SPAN
    buys = [x for x in sw if x["buy"]]
    r["n_swaps"] = len(sw); r["n_buys"] = len(buys); r["n_sells"] = len(sw) - len(buys)
    r["buy_eth_total"] = round(sum(x["q"] for x in buys) * qf, 9)
    r["n_adds"] = len(adds); r["liq_off"] = adds[0]["bn"] - lb if adds else None
    r["liq_in_launch_tx"] = any(a["tx"] == p["launch_tx"] for a in adds)
    # liquidity accounting for full / partial pulls
    seq = sorted([(a["bn"], a["li"], "a", a) for a in adds] + [(x["bn"], x["li"], "p", x) for x in pulls] +
                 ([(x["bn"], x["li"], "s", x) for x in sw] if o["kind"] == "v2" else []), key=lambda z: (z[0], z[1]))
    level = 0; peak = 0; pl_out = []
    for bn, li, k, x in seq:
        amt = x.get("L") if o["kind"] != "v2" else x.get("q")
        if k == "a": level += amt; peak = max(peak, level)
        elif k == "s": level += x["q"] if x["buy"] else -x["q"]; peak = max(peak, level)
        else:
            before = level; level = max(0, level - amt)
            frac = (amt / before) if before > 0 else None
            full = level <= 0.01 * peak if peak > 0 else None
            tt = tx(x["tx"])
            pl_out.append([bn - lb, tt["from"] if tt else None, tt["to"] if tt else None, tt["selector"] if tt else None, full,
                           round(min(frac, 1.0), 4) if frac is not None else None, x.get("via"), x["tx"]])
    r["pulls"] = pl_out; r["n_pulls"] = len(pl_out)
    r["first_pull_off"] = pl_out[0][0] if pl_out else None
    r["first_pull_full"] = pl_out[0][4] if pl_out else None
    fulls = [x for x in pl_out if x[4]]
    r["first_full_pull_off"] = fulls[0][0] if fulls else None
    r["pull_by_launch_wallet"] = (pl_out[0][1] == r["launch"]["from"]) if (pl_out and r["launch"]) else None
    # swaps with their transactions
    S12 = []; enriched = []
    for k, x in enumerate(sw):
        tt = tx(x["tx"])
        e = {"k": k, "bn": x["bn"], "li": x["li"], "buy": x["buy"], "eth": x["q"] * qf, "eoa": tt["from"] if tt else None, "to": tt["to"] if tt else None,
             "sel": tt["selector"] if tt else None, "clen": tt["calldata_len"] if tt else None, "gp": tt["gas_price"] if tt else None,
             "prio": tt["max_prio"] if tt else None, "router": x["router"], "tx": x["tx"]}
        enriched.append(e)
        if e["eoa"]:
            seen_pools[e["eoa"]].add(i)
            if e["buy"]: bought_pools[e["eoa"]].add(i)
    for e in enriched[:NF]:
        S12.append([e["bn"] - lb, "B" if e["buy"] else "S", round(e["eth"], 9), e["eoa"], e["to"], e["sel"], e["clen"], e["gp"], e["prio"], e["router"],
                    e["tx"] == p["launch_tx"]])
    r["swaps12"] = S12
    r["first_buys"] = [[e["bn"] - lb, round(e["eth"], 9)] for e in enriched if e["buy"]][:5]
    r["first_buy_off"] = r["first_buys"][0][0] if r["first_buys"] else None
    r["first_buy_eth"] = r["first_buys"][0][1] if r["first_buys"] else None
    ours = [e for e in enriched if e["eoa"] == OUR_WALLET or e["to"] == OUR_RELAY]
    r["ours"] = {"bought": any(e["buy"] for e in ours), "first_off": ours[0]["bn"] - lb} if ours else None
    real = [e for e in enriched if e["buy"] and e["eth"] >= REAL and e["eoa"] != OUR_WALLET and e["to"] != OUR_RELAY]
    r["first_real_buys"] = [[e["bn"] - lb, round(e["eth"], 9), e["eoa"]] for e in real[:3]]
    if real:
        f = real[0]
        r["frb"] = {"off": f["bn"] - lb, "eth": round(f["eth"], 9), "eoa": f["eoa"], "to": f["to"], "sel": f["sel"], "clen": f["clen"],
                    "router": f["router"], "idx": f["k"], "gp": f["gp"], "prio": f["prio"], "eoa_is_launch_wallet": (f["eoa"] == r["launch"]["from"]) if r["launch"] else None}
        r["pull_minus_frb"] = (pl_out[0][0] - (f["bn"] - lb)) if pl_out else None
        r["pull_before_frb"] = (pl_out[0][0] < f["bn"] - lb) if pl_out else None
    else:
        r["frb"] = None; r["pull_minus_frb"] = None; r["pull_before_frb"] = None
    swaps_by_pool[i] = [(e["bn"], e["li"], e["buy"], e["eth"], e["eoa"], e["to"], f"{e['to']}:{e['sel']}:{e['clen']}:{e['prio']}") for e in enriched]
    pb = (pulls[0]["bn"], pulls[0]["li"]) if pulls else None
    r["_pb"] = pb
    rows[i] = r
del EV
log("pools built", len(rows), "eoas", len(seen_pools), el())

# ---------------- shared fingerprints of single-use wallets (an operator's fresh-wallet crowd or decoys look like outsiders by the wallet rule)
SFP_MIN = 25
fpw = collections.defaultdict(set); fpp = collections.defaultdict(set); fps_eth = collections.defaultdict(list)
for i, sw in swaps_by_pool.items():
    for x in sw:
        if x[2] and x[4] and len(seen_pools[x[4]]) < OUT_POOLS and x[4] != OUR_WALLET:
            fpw[x[6]].add(x[4]); fpp[x[6]].add(i); fps_eth[x[6]].append(x[3])
SHARED = {fp for fp, w in fpw.items() if len(w) >= SFP_MIN}
shared_rows = sorted([{"fp": fp, "single_use_wallets": len(fpw[fp]), "pools": len(fpp[fp]), "buys": len(fps_eth[fp]),
                       "eth_p10_50_90": [sorted(fps_eth[fp])[len(fps_eth[fp]) // 10], sorted(fps_eth[fp])[len(fps_eth[fp]) // 2], sorted(fps_eth[fp])[9 * len(fps_eth[fp]) // 10]]}
                      for fp in SHARED], key=lambda x: -x["single_use_wallets"])
log("shared single-use fingerprints", len(SHARED))

# ---------------- outsiders
for i, r in rows.items():
    if not r.get("has_events"): continue
    lb = r["launch_block"]; pb = r.pop("_pb"); sw = swaps_by_pool[i]
    pre = [s for s in sw if s[2] and (pb is None or (s[0], s[1]) < pb)]
    known = [s for s in pre if s[4]]
    outs = [s for s in known if len(seen_pools[s[4]]) < OUT_POOLS and s[4] != OUR_WALLET and s[5] != OUR_RELAY and s[3] >= OUT_MIN]
    o = {"n_buys_before_pull": len(pre), "n_with_eoa": len(known), "n_outsider_buys": len(outs),
         "outsider_eth": round(sum(s[3] for s in outs), 9)}
    if outs:
        o["first_off"] = outs[0][0] - lb; o["last_off"] = outs[-1][0] - lb; o["last_eoa"] = outs[-1][4]; o["last_eth"] = round(outs[-1][3], 9)
        o["max_eth"] = round(max(s[3] for s in outs), 9)
        o["last_fp"] = outs[-1][6]; o["fps"] = sorted({s[6] for s in outs})[:5]
        if pb is not None:
            o["pull_after_first"] = pb[0] - outs[0][0]; o["pull_after_last"] = pb[0] - outs[-1][0]
            o["reaction"] = o["pull_after_last"] <= REACT
        else:
            o["pull_after_first"] = o["pull_after_last"] = None; o["reaction"] = False if r.get("ev_complete") else None
    if pb is not None:
        w200 = [x for x in pre if pb[0] - x[0] <= 200]
        o["n_win200"] = len(w200); o["n_win200_with_eoa"] = sum(1 for x in w200 if x[4])
    nf = [x for x in outs if x[6] not in SHARED]
    o["nf_n"] = len(nf)
    if nf:
        o["nf_last_off"] = nf[-1][0] - lb; o["nf_last_fp"] = nf[-1][6]
        o["nf_pull_after_last"] = (pb[0] - nf[-1][0]) if pb is not None else None
        o["nf_reaction"] = (o["nf_pull_after_last"] <= REACT) if pb is not None else (False if r.get("ev_complete") else None)
    r["outsider"] = o
    r["pull_after_last_buy"] = (pb[0] - pre[-1][0]) if (pb is not None and pre) else None
    # the same on the first 12 swaps only (fetched for every pool, so not biased by whether the pool was pulled)
    pre12 = [x for x in sw[:NF] if x[2] and (pb is None or (x[0], x[1]) < pb)]
    out12 = [x for x in pre12 if x[4] and len(seen_pools[x[4]]) < OUT_POOLS and x[4] != OUR_WALLET and x[5] != OUR_RELAY and x[3] >= OUT_MIN]
    o12 = {"n": len(out12), "n_buys12_before_pull": len(pre12)}
    if out12:
        o12["last_off"] = out12[-1][0] - lb; o12["last_eth"] = round(out12[-1][3], 9); o12["last_fp"] = out12[-1][6]
        o12["pull_after_last"] = (pb[0] - out12[-1][0]) if pb is not None else None
        o12["reaction"] = (o12["pull_after_last"] <= REACT) if pb is not None else (False if r.get("ev_complete") else None)
    nf12 = [x for x in out12 if x[6] not in SHARED]
    o12["nf_n"] = len(nf12)
    if nf12:
        o12["nf_last_off"] = nf12[-1][0] - lb; o12["nf_last_eth"] = round(nf12[-1][3], 9)
        o12["nf_pull_after_last"] = (pb[0] - nf12[-1][0]) if pb is not None else None
        o12["nf_reaction"] = (o12["nf_pull_after_last"] <= REACT) if pb is not None else (False if r.get("ev_complete") else None)
    r["outsider12"] = o12
    r["pull_after_last_buy12"] = (pb[0] - pre12[-1][0]) if (pb is not None and pre12) else None
    ours_pre = [s for s in pre if s[4] == OUR_WALLET or s[5] == OUR_RELAY]
    if r.get("ours") is not None:
        r["ours"]["bought_before_pull"] = bool(ours_pre)
        r["ours"]["pull_after_ours"] = (pb[0] - ours_pre[-1][0]) if (ours_pre and pb) else None

# ---------------- families
def fam_keys(r):
    L = r["launch"] or {}; tc = r["token_code"]
    tok = tc["skel"] or ("nocode:" + str(tc["size"]))
    tokm = tc["mask32"] or ("nocode:" + str(tc["size"]))
    lc = f"{L.get('target_code_hash') or L.get('target') or 'create?'}|{L.get('selector')}"
    strict = f"{lc}|{L.get('calldata_len')}|{r['fee']}|{r['tick_spacing']}|{int(r['hooks'] or '0x0', 16) == 0 if r['dex'] == 'v4' else r['dex']}"
    fu = FUND.get(L.get("from"))
    f1 = (fu["first"]["funder"] if fu and fu.get("first") else None)
    h2 = FUND2.get(f1) if f1 else None
    root = h2["first"]["funder"] if (h2 and h2.get("first")) else f1
    return {"tok": tok, "tokm": tokm, "tokx": tc["hash"] or ("nocode:" + str(tc["size"])), "lc": lc, "strict": strict, "fund": root, "fund1": f1}


for i, r in rows.items():
    r["fam"] = fam_keys(r)
    L = r["launch"] or {}; fu = FUND.get(L.get("from"))
    if fu:
        f = fu.get("first"); lt = fu.get("latest_before_launch")
        r["funding"] = {"status": fu["status"], "sampled_pool": fu["pool"] == i, "from_cache": bool(fu.get("from_cache")), "scan_blocks": fu["scan_from"] - fu["scan_to"] + 1,
                        "launch_nonce_at_sample": fu["launch_nonce"], "nonce0_block": fu["nonce0_block"],
                        "funder": f["funder"] if f else None, "via": f["via"] if f else None, "kind": f["kind"] if f else None,
                        "blocks_before_launch": (r["launch_block"] - f["bn"]) if f else None, "value_eth": round(f["value_wei"] / 1e18, 9) if f else None,
                        "funder_nonce": f["funder_nonce"] if f else None, "funding_tx": f["tx"] if f else None,
                        "latest_funder": lt["funder"] if lt else None}
        h2 = FUND2.get(f["funder"]) if f else None
        if h2:
            g2 = h2.get("first")
            r["funding"]["hop2"] = {"status": h2["status"], "funder": g2["funder"] if g2 else None, "via": g2["via"] if g2 else None,
                                    "blocks_before_hop1": (f["bn"] - g2["bn"]) if g2 else None, "value_eth": round(g2["value_wei"] / 1e18, 9) if g2 else None,
                                    "funder_nonce": g2["funder_nonce"] if g2 else None}
        r["funding"]["root"] = r["fam"]["fund"]
    else: r["funding"] = None
FAMS = {}
for key in ("tok", "tokm", "tokx", "lc", "strict", "fund", "fund1"):
    by = collections.defaultdict(list)
    for i, r in rows.items():
        if r["quote_pair"]: continue
        k = r["fam"][key]
        if k is not None: by[k].append(i)
    FAMS[key] = by
for i, r in rows.items():
    r["fam_n"] = {k: (len(FAMS[k].get(r["fam"][k], [])) if r["fam"][k] is not None else None) for k in FAMS}

# cross-pool: did the first real buyer also buy in other pools of the same family?
FSET = {key: {k: set(v) for k, v in by.items()} for key, by in FAMS.items() if key in ("tok", "lc", "fund")}
for i, r in rows.items():
    f = r.get("frb")
    if not f or not f["eoa"]: continue
    bp = bought_pools.get(f["eoa"], set())
    f["eoa_npools_bought"] = len(bp); f["eoa_npools_seen"] = len(seen_pools.get(f["eoa"], ()))
    for key in ("tok", "lc", "fund"):
        k = r["fam"][key]
        if k is None: f[f"also_in_{key}_family"] = None; continue
        fs = FSET[key].get(k, set())
        f[f"also_in_{key}_family"] = sum(1 for j in bp if j != i and j in fs)
log("features done", el())


def q(v, p):
    v = [x for x in v if x is not None]
    if not v: return None
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))]


def med(v):
    v = [x for x in v if x is not None]
    return stt.median(v) if v else None


def fam_summary(key, k, ids):
    rs = [rows[i] for i in ids]
    L = [r["launch"] or {} for r in rs]
    ev = [r for r in rs if r.get("has_events")]
    frb = [r["frb"] for r in ev if r.get("frb")]
    out_pools = [r for r in ev if r.get("outsider") and r["outsider"]["n_outsider_buys"] > 0 and r.get("ev_complete")]
    react = [r for r in out_pools if r["outsider"].get("reaction")]
    base_pools_ = [r for r in ev if r.get("ev_complete") and r.get("n_buys") and r.get("outsider") is not None and r["outsider"]["n_outsider_buys"] == 0]
    base_quick = [r for r in base_pools_ if r.get("pull_after_last_buy") is not None and r["pull_after_last_buy"] <= REACT]
    o12p = [r for r in ev if r.get("ev_complete") and (r.get("outsider12") or {}).get("n")]
    o12r = [r for r in o12p if r["outsider12"].get("reaction")]
    n12p = [r for r in ev if r.get("ev_complete") and (r.get("outsider12") or {}).get("nf_n")]
    n12r = [r for r in n12p if r["outsider12"].get("nf_reaction")]
    b12p = [r for r in ev if r.get("ev_complete") and r.get("outsider12") is not None and r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
    b12q = [r for r in b12p if r.get("pull_after_last_buy12") is not None and r["pull_after_last_buy12"] <= REACT]
    ts = sorted(r["launch_ts"] for r in rs)
    span_days = max((ts[-1] - ts[0]) / 86400, 1 / 24)
    pulls = [r for r in ev if r.get("n_pulls")]
    cnt = lambda xs, n=3: [[a, b] for a, b in collections.Counter(xs).most_common(n)]
    s = {"key": k, "grouping": key, "count": len(rs), "n_with_events": len(ev), "n_with_liq": sum(1 for r in ev if r.get("n_adds")),
         "first_utc": utc(ts[0]), "last_utc": utc(ts[-1]), "per_day": round(len(rs) / max(span_days, 1.0), 1),
         "dex": cnt([r["dex"] for r in rs]), "quote": cnt([r["quote"] for r in rs]), "fee_ts": cnt([f"{r['fee']}/{r['tick_spacing']}" for r in rs]),
         "n_tokens": len({r["token"] for r in rs}), "n_deployers": len({l.get("from") for l in L}), "deployer_top": cnt([l.get("from") for l in L], 2),
         "launch_target": cnt([l.get("target") for l in L], 3), "selector": cnt([l.get("selector") for l in L], 3), "calldata_len": cnt([l.get("calldata_len") for l in L], 3),
         "value_eth": cnt([l.get("value_eth") for l in L], 4), "nonce_med": med([l.get("nonce") for l in L]),
         "tok_size": cnt([r["token_code"]["size"] for r in rs], 2), "known_fp": cnt([r["known_fp"] for r in rs], 4),
         "first_buy_off_med": med([r.get("first_buy_off") for r in ev]),
         "frb_n": len(frb), "frb_off_p10_50_90": [q([f["off"] for f in frb], .1), med([f["off"] for f in frb]), q([f["off"] for f in frb], .9)],
         "frb_eth_med": med([f["eth"] for f in frb]), "frb_to": cnt([f["to"] for f in frb], 3), "frb_sel_clen": cnt([f"{f['sel']}/{f['clen']}" for f in frb], 2),
         "frb_eoa_top": cnt([f["eoa"] for f in frb], 3), "frb_by_launch_wallet": sum(1 for f in frb if f.get("eoa_is_launch_wallet")),
         "frb_eoa_in_same_tok_family": sum(1 for f in frb if (f.get("also_in_tok_family") or 0) > 0),
         "frb_eoa_in_same_lc_family": sum(1 for f in frb if (f.get("also_in_lc_family") or 0) > 0),
         "frb_eoa_in_same_fund_family": sum(1 for f in frb if (f.get("also_in_fund_family") or 0) > 0),
         "n_pulled": len(pulls), "pulled_share": round(len(pulls) / len(ev), 3) if ev else None,
         "pull_off_p10_50_90": [q([r["first_pull_off"] for r in pulls], .1), med([r["first_pull_off"] for r in pulls]), q([r["first_pull_off"] for r in pulls], .9)],
         "full_pull_share": round(sum(1 for r in pulls if r["first_pull_full"]) / len(pulls), 3) if pulls else None,
         "pull_minus_frb_med": med([r.get("pull_minus_frb") for r in ev]),
         "pull_before_frb": sum(1 for r in ev if r.get("pull_before_frb")),
         "pull_by_launch_wallet": sum(1 for r in pulls if r.get("pull_by_launch_wallet")),
         "pull_via": cnt([f"{r['pulls'][0][2]}:{r['pulls'][0][3]}" for r in pulls], 2),
         "outsider_pools": len(out_pools), "outsider_reactions": len(react),
         "outsider_reaction_rate": round(len(react) / len(out_pools), 3) if out_pools else None,
         "pull_after_outsider_med": med([r["outsider"].get("pull_after_last") for r in out_pools]),
         "outsider12_pools": len(o12p), "outsider12_reactions": len(o12r),
         "outsider12_reaction_rate": round(len(o12r) / len(o12p), 3) if o12p else None,
         "pull_after_outsider12_med": med([r["outsider12"].get("pull_after_last") for r in o12p]),
         "baseline12_pools": len(b12p), "baseline12_quick": len(b12q), "baseline12_rate": round(len(b12q) / len(b12p), 3) if b12p else None,
         "outsider12_fp_top": cnt([r["outsider12"]["last_fp"] for r in o12p], 3),
         "outsider12_nf_pools": len(n12p), "outsider12_nf_reactions": len(n12r),
         "outsider12_nf_reaction_rate": round(len(n12r) / len(n12p), 3) if n12p else None,
         "pull_after_outsider12_nf_med": med([r["outsider12"].get("nf_pull_after_last") for r in n12p]),
         "reaction_baseline_pools": len(base_pools_), "reaction_baseline_quick": len(base_quick),
         "reaction_baseline_rate": round(len(base_quick) / len(base_pools_), 3) if base_pools_ else None,
         "pulled_share_with_outsider": round(sum(1 for r in out_pools if r.get("n_pulls")) / len(out_pools), 3) if out_pools else None,
         "pulled_share_without_outsider": round(sum(1 for r in base_pools_ if r.get("n_pulls")) / len(base_pools_), 3) if base_pools_ else None,
         "frb_distinct_eoas": len({f["eoa"] for f in frb}),
         "frb_fp_top": cnt([f"{f['to']}:{f['sel']}:{f['clen']}:{f['prio']}" for f in frb], 2),
         "outsider_fp_top": cnt([r["outsider"]["last_fp"] for r in out_pools], 3),
         "frb_router_top": cnt([f["router"] for f in frb], 2),
         "ours_in": sum(1 for r in rs if r.get("ours")),
         "funded_sampled": sum(1 for r in rs if r.get("funding") and r["funding"].get("funder")),
         "funder_top": cnt([r["funding"]["funder"] for r in rs if r.get("funding") and r["funding"].get("funder")], 3)}
    s["desc"] = describe(s)
    s["pools"] = list(ids)
    return s


def short(a): return a[:10] if isinstance(a, str) else a


def describe(s):
    d = "/".join(f"{k} {n}" for k, n in s["dex"][:2]); qd = "/".join(f"{k} {n}" for k, n in s["quote"][:2]); ft = s["fee_ts"][0][0]
    tgt = s["launch_target"][0][0] if s["launch_target"] else None
    tname = {POSM: "POSM", PM: "PoolManager"}.get(tgt, short(tgt))
    sel = s["selector"][0][0] if s["selector"] else None
    vals = ",".join(str(v) for v, _ in s["value_eth"][:2])
    kf = ",".join(f"{k} {n}/{s['count']}" for k, n in s["known_fp"] if k) or "new"
    frb = s["frb_off_p10_50_90"]; po = s["pull_off_p10_50_90"]
    fto = s["frb_to"][0][0] if s["frb_to"] else None
    return (f"[{kf}] {d} {qd} fee/ts {ft}; {s['count']} launches ({s['per_day']}/d) by {s['n_deployers']} wallets via {tname}:{sel} value {vals}; "
            f"first real buy +{frb[1]} (n {s['frb_n']}, med {s['frb_eth_med'] and round(s['frb_eth_med'], 4)} ETH, via {short(fto)}); "
            f"pulled {s['n_pulled']}/{s['n_with_events']} at +{po[1]}; early-outsider reaction {s['outsider12_reactions']}/{s['outsider12_pools']} "
            f"(baseline {s['baseline12_quick']}/{s['baseline12_pools']})")


FS = {}
for key, by in FAMS.items():
    if key == "tokx": continue
    FS[key] = [fam_summary(key, k, ids) for k, ids in sorted(by.items(), key=lambda kv: -len(kv[1])) if len(ids) >= 5]
    log("families", key, len(by), ">=5:", len(FS[key]), el())

# ---------------- overlap between groupings
def overlap(a, b, top=None):
    res = []
    for s in FS[a][:top]:
        ids = FAMS[a][s["key"]]
        c = collections.Counter(rows[i]["fam"][b] for i in ids if rows[i]["fam"][b] is not None)
        if not c: continue
        n = sum(c.values()); kb, nb = c.most_common(1)[0]
        res.append({"key": s["key"], "count": len(ids), "covered": n, f"n_{b}_families": len(c), f"top_{b}": kb, "top_share": round(nb / n, 3),
                    f"top_{b}_family_size": len(FAMS[b].get(kb, [])) if kb is not None else None})
    return res


OV = {}
for a, b in (("tok", "lc"), ("lc", "tok"), ("tok", "fund"), ("lc", "fund"), ("fund", "tok"), ("fund", "lc"), ("tok", "tokm"), ("tok", "strict")):
    rr = overlap(a, b)
    OV[f"{a}_vs_{b}"] = {"families": len(rr), "pure_ge_0.9": sum(1 for x in rr if x["top_share"] >= 0.9),
                         "split_ge_3": sum(1 for x in rr if x[f"n_{b}_families"] >= 3),
                         "median_n_other": med([x[f"n_{b}_families"] for x in rr]), "rows": rr[:60]}
# contingency of the top families
top_t = [s["key"] for s in FS["tok"][:15]]; top_l = [s["key"] for s in FS["lc"][:15]]
OV["matrix_tok15_x_lc15"] = {"tok": top_t, "lc": top_l, "counts": [[sum(1 for i in FAMS["tok"][t] if rows[i]["fam"]["lc"] == l) for l in top_l] for t in top_t]}
log("overlap done", el())

# ---------------- write
def dump_jsonl(name, it):
    p = os.path.join(CEN, name)
    with open(p + ".tmp", "w") as f:
        for r in it: f.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.replace(p + ".tmp", p)


def dump_json(name, v):
    p = os.path.join(CEN, name); json.dump(v, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)


order = sorted(rows.values(), key=lambda r: (r["launch_block"], r["launch_ti"], r["pool"]))
dump_jsonl("pools.jsonl", order)
for key in FS: dump_json(f"families_{key}.json", FS[key])
dump_json("overlap.json", OV)
dump_json("shared_fps.json", {"min_single_use_wallets": SFP_MIN, "rows": shared_rows})
cnt_dex = collections.Counter(r["dex"] for r in rows.values())
summ = {"window": W_, "window_utc": [utc(W_["from_ts"]), utc(W_["head_ts"])], "built_utc": utc(time.time()),
        "pools": len(rows), "by_dex": dict(cnt_dex), "by_dex_quote": {f"{a}/{b}": n for (a, b), n in collections.Counter((r["dex"], r["quote"]) for r in rows.values()).items()},
        "quote_pairs": sum(1 for r in rows.values() if r["quote_pair"]),
        "with_events": sum(1 for r in rows.values() if r.get("has_events")), "ev_complete": sum(1 for r in rows.values() if r.get("ev_complete")),
        "with_liquidity": sum(1 for r in rows.values() if r.get("n_adds")), "with_swaps": sum(1 for r in rows.values() if r.get("n_swaps")),
        "with_real_buy": sum(1 for r in rows.values() if r.get("frb")), "with_pull": sum(1 for r in rows.values() if r.get("n_pulls")),
        "with_outsider_buy": sum(1 for r in rows.values() if (r.get("outsider") or {}).get("n_outsider_buys")),
        "launch_txs": len({r["launch_tx"] for r in rows.values()}), "missing_launch_tx": sum(1 for r in rows.values() if not r["launch"]),
        "swap_txs_cached": len(TS), "eoas_seen": len(seen_pools),
        "swaps_without_tx_in_first12": sum(1 for r in rows.values() for s in (r.get("swaps12") or []) if s[3] is None),
        "families": {k: {"all": len(by), "ge5": sum(1 for v in by.values() if len(v) >= 5), "ge5_pools": sum(len(v) for v in by.values() if len(v) >= 5),
                         "ge20": sum(1 for v in by.values() if len(v) >= 20), "singletons": sum(1 for v in by.values() if len(v) == 1)} for k, by in FAMS.items()},
        "funding_sample": {"wallets": len(FUND), "wallets_scanned": sum(1 for x in FUND.values() if not x.get("from_cache")),
                           "wallets_from_cache": sum(1 for x in FUND.values() if x.get("from_cache")),
                           "hop2_scanned": len(FUND2), "hop2_found": sum(1 for x in FUND2.values() if x.get("first")),
                           "status": dict(collections.Counter(x["status"] for x in FUND.values())),
                           "pools_covered": sum(1 for r in rows.values() if r.get("funding")),
                           "pools_with_funder": sum(1 for r in rows.values() if r.get("funding") and r["funding"].get("funder"))},
        "shared_fps": len(SHARED), "params": {"SFP_MIN": SFP_MIN, "REAL": REAL, "OUT_MIN": OUT_MIN, "OUT_POOLS": OUT_POOLS, "REACT": REACT, "SPAN": SPAN, "ETH_PER_USDG": ETH_PER_USDG, "NF": NF}}
per = {}
for d in sorted(cnt_dex):
    rs = [r for r in rows.values() if r["dex"] == d]
    per[d] = {"pools": len(rs), "quote_pairs": sum(1 for r in rs if r["quote_pair"]), "by_quote": dict(collections.Counter(r["quote"] for r in rs)),
              "with_events": sum(1 for r in rs if r.get("has_events")), "with_liquidity": sum(1 for r in rs if r.get("n_adds")),
              "with_swaps": sum(1 for r in rs if r.get("n_swaps")), "with_real_buy": sum(1 for r in rs if r.get("frb")),
              "with_pull": sum(1 for r in rs if r.get("n_pulls")), "first_pull_full": sum(1 for r in rs if r.get("first_pull_full")),
              "with_outsider_buy": sum(1 for r in rs if (r.get("outsider") or {}).get("n_outsider_buys")),
              "outsider_reactions": sum(1 for r in rs if (r.get("outsider") or {}).get("reaction")),
              "launch_txs": len({r["launch_tx"] for r in rs}), "launch_wallets": len({(r["launch"] or {}).get("from") for r in rs}),
              "tok_families": len({r["fam"]["tok"] for r in rs}), "lc_families": len({r["fam"]["lc"] for r in rs})}
summ["per_dex"] = per
dump_json("summary.json", summ)
log("written", el())
