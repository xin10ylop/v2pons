#!/usr/bin/env python3
"""Build the census files from cache/*.jsonl (no RPC). Writes pools.jsonl, events.jsonl, txs.jsonl, families.json, blocks.json,
blocks_meta.json, loose_families.json, v4_other_pools.jsonl, dex_pairs.jsonl, other_dex.json, summary.json."""
import sys, os, json, time, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from fetch import (ZERO32, POSM, SPAN, T_PAIR, T_POOL, T_SOLID, T_ALGEBRA, T_FAC, FAC, all_inits, family_key)
import v4math

OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"; VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
V2433 = 2433328500000000000
t0 = time.time()
win = jget("window.json")


def dump_jsonl(name, rows):
    p = os.path.join(CEN, name)
    with open(p + ".tmp", "w") as f:
        for r in rows: f.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.replace(p + ".tmp", p)


def dump_json(name, v, indent=None):
    p = os.path.join(CEN, name); json.dump(v, open(p + ".tmp", "w"), indent=indent, separators=None if indent else (",", ":")); os.replace(p + ".tmp", p)


def known_rule(tx):
    """the orchestrator's rule, verbatim"""
    if not tx: return "none"
    if tx["to"] == OPA or tx["selector"] == "2fcb9108": return "operator-A"
    if tx["to"] == POSM and tx["selector"] == "ac9650d8" and tx["calldata_len"] == 1444:
        return "vbot-v2.433" if tx["value_wei"] == V2433 else "vbot-other"
    return "none"


def known_pool(tx):
    if not tx: return "none"
    if tx["to"] == OPA or tx["selector"] == "2fcb9108": return "operator-A"
    if tx["to"] == POSM and tx["selector"] == "ac9650d8" and tx["calldata_len"] == 1444:
        return "vbot-v2.433" if tx["value_wei"] == V2433 else "vbot-other"
    return "none"


# ---- inits
A = all_inits()
E = [l for l in A if l["topics"][2] == ZERO32]
O = [l for l in A if l["topics"][2] != ZERO32]
T = {x["hash"]: x for x in jl_read("ltx.jsonl")}
R = {x["hash"]: x for x in jl_read("lrcpt.jsonl")}
CODES = {x["addr"]: x for x in jl_read("codes.jsonl")}
BM = {x["bn"]: x for x in jl_read("blocks.jsonl")}

pools = {}
for l in E:
    pid = l["topics"][1]; d = l["data"]; tx = T.get(l["tx"])
    hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
    to = tx["to"] if tx else None
    created = (R.get(l["tx"]) or {}).get("contract")
    code = CODES.get(to or (created or "").lower() or "-")
    row = {"pid": pid, "token": "0x" + l["topics"][3][26:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": hooks, "hooks_zero": int(hooks, 16) == 0,
           "sqrt_p0": W(d, 3), "tick0": sgn(W(d, 4)), "launch_block": l["bn"], "launch_ts": BM.get(l["bn"], {}).get("ts"), "launch_tx": l["tx"],
           "tx_index": l["ti"], "log_index": l["li"],
           "launch_to": to, "launch_from": tx["from"] if tx else None, "launch_nonce": tx["nonce"] if tx else None,
           "launch_value_wei": tx["value_wei"] if tx else None, "launch_value_eth": round(tx["value_wei"] / 1e18, 9) if tx else None,
           "selector": tx["selector"] if tx else None, "calldata_len": tx["calldata_len"] if tx else None,
           "created_contract": created.lower() if created else None,
           "to_code_size": code["size"] if code else None, "to_code_hash": code["hash"] if code else None,
           "family": family_key(l, tx), "known": known_pool(tx), "known_by_rule": known_rule(tx)}
    if pid in pools: row["dup_init"] = True
    pools[pid] = row
fcnt = collections.Counter(r["family"] for r in pools.values())
for r in pools.values(): r["family_count"] = fcnt[r["family"]]
print("pools", len(pools), "eth inits", len(E), "other", len(O), f"{time.time() - t0:.0f}s", flush=True)

# ---- events
ev = {}
for g in jl_read("ev_groups.jsonl"):
    for p in g["pids"]:
        lb = g["launch"][p]; e = ev.setdefault(p, {"pid": p, "launch_block": lb, "ev_from": lb, "ev_to": min(lb + SPAN, g["b"]), "logs": {}})
        e["ev_to"] = max(e["ev_to"], min(lb + SPAN, g["b"]))
    for l in g["logs"]:
        p = l["topics"][1]
        if p not in g["launch"]: continue
        lb = g["launch"][p]
        if lb <= l["bn"] <= lb + SPAN: ev[p]["logs"][(l["bn"], l["li"])] = l
print("event pools", len(ev), f"{time.time() - t0:.0f}s", flush=True)

events = {}
for p, e in ev.items():
    sw, pulls, adds, zero = [], [], [], []
    for k in sorted(e["logs"]):
        l = e["logs"][k]; d = l["data"]; sender = "0x" + l["topics"][2][26:]
        if l["topics"][0] == T_SWAP:
            sw.append({"bn": l["bn"], "ti": l["ti"], "li": l["li"], "sender": sender, "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1)), "sqrt_p": W(d, 2), "liq": W(d, 3),
                       "tick": sgn(W(d, 4)), "fee": W(d, 5), "tx": l["tx"]})
        else:
            dl = sgn(W(d, 2)); m = {"bn": l["bn"], "ti": l["ti"], "li": l["li"], "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dl": dl, "sender": sender, "tx": l["tx"]}
            (pulls if dl < 0 else adds if dl > 0 else zero).append(m)
    events[p] = {"pid": p, "launch_block": e["launch_block"], "ev_from": e["ev_from"], "ev_to": e["ev_to"], "complete": e["ev_to"] >= e["launch_block"] + SPAN,
                 "swaps": sw, "pulls": pulls, "adds": adds, "zero_mods": zero}
del ev

# per-pool conveniences
for p, r in pools.items():
    e = events.get(p)
    r["has_events"] = e is not None
    if not e: continue
    lb = r["launch_block"]; sw = e["swaps"]
    buys = [s for s in sw if s["a0"] < 0]; sells = [s for s in sw if s["a0"] > 0]
    r["ev_to"] = e["ev_to"]; r["ev_complete"] = e["complete"]
    r["n_swaps"] = len(sw); r["n_buys"] = len(buys); r["n_sells"] = len(sells); r["n_pulls"] = len(e["pulls"]); r["n_adds"] = len(e["adds"])
    r["eth_in_buys"] = round(sum(-s["a0"] for s in buys) / 1e18, 9)
    r["first_buy_rel"] = buys[0]["bn"] - lb if buys else None
    r["first_buy_eth"] = round(-buys[0]["a0"] / 1e18, 9) if buys else None
    r["first_pull_rel"] = e["pulls"][0]["bn"] - lb if e["pulls"] else None
    la = [(a["lo"], a["hi"], a["dl"]) for a in e["adds"] if a["tx"] == r["launch_tx"]]
    r["liq_launch"] = v4math.active_liquidity(r["tick0"], la) if la else None
    r["buy_in_launch_tx"] = any(s["tx"] == r["launch_tx"] for s in buys)

# ---- transactions
txs = {}
def add_tx(t, kind, ref=None):
    x = txs.get(t["hash"])
    if x is None:
        x = dict(t); x["value_eth"] = round(t["value_wei"] / 1e18, 12); x["kind"] = []; x["refs"] = []; txs[t["hash"]] = x
    if kind not in x["kind"]: x["kind"].append(kind)
    if ref: x["refs"].append(ref)
for r in pools.values():
    t = T.get(r["launch_tx"])
    if t: add_tx(t, "launch", [r["pid"], "launch", 0])
S = {x["hash"]: x for x in jl_read("stx.jsonl")}
for p, e in events.items():
    for i, s in enumerate(e["swaps"][:8]):
        t = S.get(s["tx"]) or T.get(s["tx"])
        if t: add_tx(t, "swap", [p, "swap", i])
    for i, s in enumerate(e["pulls"][:2]):
        t = S.get(s["tx"]) or T.get(s["tx"])
        if t: add_tx(t, "pull", [p, "pull", i])
print("txs", len(txs), f"{time.time() - t0:.0f}s", flush=True)

# vbot-router / router stats per pool (from the first 8 swaps' txs)
for p, r in pools.items():
    e = events.get(p)
    if not e: continue
    tos = []
    for s in e["swaps"][:8]:
        t = txs.get(s["tx"]); tos.append(t["to"] if t else None)
    r["first8_swap_to"] = tos
    pt = [txs.get(s["tx"]) for s in e["pulls"][:1]]
    r["first_pull_to"] = pt[0]["to"] if pt and pt[0] else None
    r["first_pull_selector"] = pt[0]["selector"] if pt and pt[0] else None
    r["first_pull_from"] = pt[0]["from"] if pt and pt[0] else None

# ---- families
fams = {}
for r in sorted(pools.values(), key=lambda r: (r["launch_block"], r["log_index"])):
    k = r["family"]; f = fams.get(k)
    if f is None:
        f = fams[k] = {"key": k, "count": 0, "pids": [], "launch_to": r["launch_to"] or "create", "selector": r["selector"], "calldata_len": r["calldata_len"],
                       "fee": r["fee"], "tick_spacing": r["tick_spacing"], "hooks_zero": r["hooks_zero"], "_vals": collections.Counter(), "_from": collections.Counter(),
                       "_known": collections.Counter(), "_hooks": collections.Counter(), "first_block": r["launch_block"], "_nonce": [], "_ev": 0,
                       "to_code_size": r["to_code_size"], "to_code_hash": r["to_code_hash"], "_router": collections.Counter(), "_pullto": collections.Counter(),
                       "_fb": [], "_fp": [], "_fbe": []}
    f["count"] += 1; f["pids"].append(r["pid"]); f["last_block"] = r["launch_block"]
    f["_vals"][round((r["launch_value_wei"] or 0) / 1e18, 6)] += 1; f["_from"][r["launch_from"]] += 1; f["_known"][r["known"]] += 1; f["_hooks"][r["hooks"]] += 1
    if r["launch_nonce"] is not None: f["_nonce"].append(r["launch_nonce"])
    if r.get("has_events"):
        f["_ev"] += 1
        for a in set(x for x in r.get("first8_swap_to") or [] if x): f["_router"][a] += 1
        if r.get("first_pull_to"): f["_pullto"][r["first_pull_to"] + ":" + (r.get("first_pull_selector") or "")] += 1
        if r.get("first_buy_rel") is not None: f["_fb"].append(r["first_buy_rel"])
        if r.get("first_pull_rel") is not None: f["_fp"].append(r["first_pull_rel"])
        if r.get("first_buy_eth") is not None: f["_fbe"].append(r["first_buy_eth"])
def pct(v, qs=(.1, .5, .9)):
    v = sorted(v); return [v[int(q * (len(v) - 1))] for q in qs] if v else None
out = {}
vb_buy = collections.Counter(r["family"] for r in pools.values() if VBOT_ROUTER in (r.get("first8_swap_to") or []))
vb_pull = collections.Counter(r["family"] for r in pools.values() if r.get("first_pull_to") == VBOT_ROUTER)
for k, f in sorted(fams.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
    kn = f["_known"]
    if kn.get("vbot-v2.433") and len(kn) == 1: rule = "vbot-v2.433"
    elif kn.get("operator-A"): rule = "operator-A"
    elif kn.get("vbot-v2.433") or kn.get("vbot-other"): rule = "vbot-other"
    else: rule = "none"
    known = rule
    # the rule's "vbot-other" covers every 1,444-byte POSM multicall, which is the standard create-and-mint layout used by many
    # launchers: keep the label only with evidence (the bot's router buys or pulls in the family's pools, or the bot's incrementing
    # fee tiers 10001..10300 of HANDOFF section 1)
    if rule == "vbot-other" and not (vb_buy[k] or vb_pull[k] or 10001 <= f["fee"] <= 10300): known = "none"
    for p in f["pids"]:
        if pools[p]["known"] == "vbot-other" and known == "none": pools[p]["known"] = "none"
    out[k] = {"count": f["count"], "pids": f["pids"], "launch_to": f["launch_to"], "selector": f["selector"], "calldata_len": f["calldata_len"],
              "values_eth": sorted(f["_vals"]), "value_counts": [[v, n] for v, n in f["_vals"].most_common(12)], "fee": f["fee"], "tick_spacing": f["tick_spacing"],
              "hooks_zero": f["hooks_zero"], "hooks": [h for h, _ in f["_hooks"].most_common(5)], "known": known, "known_by_rule": rule,
              "vbot_router_buy_pools": vb_buy[k], "vbot_router_pull_pools": vb_pull[k],
              "n_deployers": len(f["_from"]), "top_deployers": f["_from"].most_common(3), "nonce_med": st.median(f["_nonce"]) if f["_nonce"] else None,
              "nonce0": sum(1 for x in f["_nonce"] if x == 0), "first_block": f["first_block"], "last_block": f["last_block"],
              "to_code_size": f["to_code_size"], "to_code_hash": f["to_code_hash"], "n_with_events": f["_ev"],
              "swap_tx_to_top": f["_router"].most_common(6), "first_pull_to_sel_top": f["_pullto"].most_common(4),
              "first_buy_rel_p10_50_90": pct(f["_fb"]), "first_pull_rel_p10_50_90": pct(f["_fp"]), "first_buy_eth_p10_50_90": pct(f["_fbe"]),
              "n_no_pull_in_window": f["_ev"] - len(f["_fp"])}
fams = out

# loose families: the key without launch_to (operators that launch through many contracts, one per launch or a few)
loose = collections.defaultdict(lambda: {"count": 0, "launch_tos": collections.Counter(), "families": set(), "code_hashes": collections.Counter()})
for r in pools.values():
    k = f"{r['selector']}|{r['calldata_len']}|{r['fee']}|{r['tick_spacing']}|{str(r['hooks_zero']).lower()}"
    x = loose[k]; x["count"] += 1; x["launch_tos"][r["launch_to"] or "create"] += 1; x["families"].add(r["family"]); x["code_hashes"][r["to_code_hash"]] += 1
loose = {k: {"count": v["count"], "n_launch_to": len(v["launch_tos"]), "n_families": len(v["families"]), "top_launch_to": v["launch_tos"].most_common(5),
             "code_hashes": v["code_hashes"].most_common(4)} for k, v in sorted(loose.items(), key=lambda kv: -kv[1]["count"])}

# code families: the strict key with launch_to replaced by the launch contract's code hash (latest state), for operators that launch
# through one contract per launch (or a few); only groups spanning 2+ launch contracts are interesting, all are written
codef = collections.defaultdict(lambda: {"count": 0, "pids": [], "launch_tos": collections.Counter(), "families": set(), "_vals": collections.Counter(),
                                         "_from": collections.Counter(), "_known": collections.Counter()})
for r in sorted(pools.values(), key=lambda r: (r["launch_block"], r["log_index"])):
    if not r["to_code_hash"]: continue
    k = f"{r['to_code_hash']}|{r['selector']}|{r['calldata_len']}|{r['fee']}|{r['tick_spacing']}|{str(r['hooks_zero']).lower()}"
    x = codef[k]; x["count"] += 1; x["pids"].append(r["pid"]); x["launch_tos"][r["launch_to"] or ("create:" + (r["created_contract"] or "?"))] += 1
    x["families"].add(r["family"]); x["_vals"][round((r["launch_value_wei"] or 0) / 1e18, 6)] += 1; x["_from"][r["launch_from"]] += 1; x["_known"][r["known"]] += 1
codef = {k: {"count": v["count"], "n_launch_to": len(v["launch_tos"]), "n_families": len(v["families"]), "top_launch_to": v["launch_tos"].most_common(5),
             "values_eth": sorted(v["_vals"]), "n_deployers": len(v["_from"]), "known_pools": dict(v["_known"]), "pids": v["pids"]}
         for k, v in sorted(codef.items(), key=lambda kv: -kv[1]["count"])}

# to families: launch_to|selector|calldata_len (fee, tick spacing and hooks free), for launchers that vary the fee per launch
tof = collections.defaultdict(lambda: {"count": 0, "fees": collections.Counter(), "ts": collections.Counter(), "hooks_zero": collections.Counter(),
                                       "_vals": collections.Counter(), "_from": collections.Counter(), "_known": collections.Counter(), "families": set()})
for r in pools.values():
    k = f"{r['launch_to'] or 'create'}|{r['selector']}|{r['calldata_len']}"
    x = tof[k]; x["count"] += 1; x["fees"][r["fee"]] += 1; x["ts"][r["tick_spacing"]] += 1; x["hooks_zero"][r["hooks_zero"]] += 1
    x["_vals"][round((r["launch_value_wei"] or 0) / 1e18, 6)] += 1; x["_from"][r["launch_from"]] += 1; x["_known"][r["known"]] += 1; x["families"].add(r["family"])
tof = {k: {"count": v["count"], "n_families": len(v["families"]), "fees": v["fees"].most_common(8), "n_fees": len(v["fees"]), "tick_spacings": v["ts"].most_common(4),
           "hooks_zero": {str(a).lower(): b for a, b in v["hooks_zero"].items()}, "values_top": v["_vals"].most_common(6), "n_values": len(v["_vals"]),
           "n_deployers": len(v["_from"]), "known_pools": dict(v["_known"])} for k, v in sorted(tof.items(), key=lambda kv: -kv[1]["count"])}

# ---- other v4 pools (non-ETH currency0), dex pairs, factory creates
other_v4 = [{"pid": l["topics"][1], "currency0": "0x" + l["topics"][2][26:], "currency1": "0x" + l["topics"][3][26:], "fee": W(l["data"], 0),
             "tick_spacing": sgn(W(l["data"], 1)), "hooks": "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3], "sqrt_p0": W(l["data"], 3), "tick0": sgn(W(l["data"], 4)),
             "bn": l["bn"], "ti": l["ti"], "tx": l["tx"]} for l in O]
D = jl_read("dex.jsonl"); names = {T_PAIR: "v2_PairCreated", T_POOL: "v3_PoolCreated", T_SOLID: "solidly_PairCreated", T_ALGEBRA: "algebra_Pool", T_INIT: "v4_Initialize_other_pm"}
pairs = []; em = collections.Counter(); qc = collections.defaultdict(collections.Counter); chunks = {"noaddr": [], "fac": []}
for c in D:
    chunks[c["kind"]].append([c["a"], c["b"]])
    if c["kind"] != "noaddr": continue
    for l in c["logs"]:
        kind = names.get(l["topics"][0], l["topics"][0]); em[(kind, l["addr"])] += 1
        t0_, t1_ = "0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]
        row = {"kind": kind, "factory": l["addr"], "token0": t0_, "token1": t1_, "bn": l["bn"], "tx": l["tx"]}
        if kind == "v2_PairCreated": row["pair"] = "0x" + l["data"][2 + 24: 2 + 64]
        elif kind == "v3_PoolCreated": row["fee"] = int(l["topics"][3], 16); row["pool"] = "0x" + l["data"][2 + 64 + 24: 2 + 128]
        pairs.append(row); qc[l["addr"]][t0_] += 1; qc[l["addr"]][t1_] += 1
fac_creates = [x for c in D if c["kind"] == "fac" for x in c["logs"]]
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
other_dex = {"window": [win["from_block"], win["head"]],
             "emitters": [{"kind": k, "address": a, "count": n, "with_weth": qc[a][WETH]} for (k, a), n in em.most_common()],
             "pm_initialize_total": len(A), "pm_initialize_eth": len(E),
             "v4_currency0_top": collections.Counter("0x" + l["topics"][2][26:] for l in A).most_common(12),
             "bonding_curve_factory": {"address": FAC, "topic": T_FAC, "creates": len(fac_creates),
                                       "per_100k_blocks": [[c["a"], c["b"], len(c["logs"])] for c in D if c["kind"] == "fac"]},
             "scanned_chunks": {k: len(v) for k, v in chunks.items()},
             "samples_40_creating_txs_per_factory": jget("dex_samples.json", {})}

# ---- write
dump_jsonl("pools.jsonl", sorted(pools.values(), key=lambda r: (r["launch_block"], r["log_index"])))
dump_jsonl("events.jsonl", [events[p] for p in sorted(events, key=lambda p: (events[p]["launch_block"], p))])
dump_jsonl("txs.jsonl", sorted(txs.values(), key=lambda t: (t["bn"] or 0, t["ti"] or 0)))
dump_json("families.json", fams)
dump_json("loose_families.json", loose)
dump_json("code_families.json", codef)
dump_json("to_families.json", tof)
dump_json("blocks.json", {str(b): x["ts"] for b, x in sorted(BM.items())})
dump_json("blocks_meta.json", {str(b): [x["ts"], x["basefee"], x["ntx"]] for b, x in sorted(BM.items())})
dump_jsonl("v4_other_pools.jsonl", other_v4)
dump_jsonl("dex_pairs.jsonl", pairs)
dump_jsonl("bonding_creates.jsonl", [{"bn": x["bn"], "tx": x["tx"], "token": "0x" + x["topics"][1][26:], "curve": "0x" + x["topics"][2][26:],
                                      "creator": "0x" + x["topics"][3][26:]} for x in fac_creates])
dump_json("other_dex.json", other_dex, indent=1)
summ = {"window": win, "pools_total_v4_inits": len(A), "eth_pools": len(pools), "pools_fetched_for_events": len(events),
        "pools_with_events": sum(1 for e in events.values() if e["swaps"] or e["pulls"] or e["adds"] or e["zero_mods"]),
        "pools_with_swaps": sum(1 for e in events.values() if e["swaps"]), "pools_with_pulls": sum(1 for e in events.values() if e["pulls"]),
        "launch_txs": len({r["launch_tx"] for r in pools.values()}), "multi_pool_launch_txs": sum(1 for h, n in collections.Counter(r["launch_tx"] for r in pools.values()).items() if n > 1),
        "pools_complete_window": sum(1 for e in events.values() if e["complete"]), "families": len(fams),
        "families_ge5": sum(1 for f in fams.values() if f["count"] >= 5), "families_ge3": sum(1 for f in fams.values() if f["count"] >= 3),
        "txs": len(txs), "tx_kinds": collections.Counter(k for t in txs.values() for k in t["kind"]),
        "missing_txs": len(jl_read("missing_txs.jsonl")), "launch_txs_missing": sum(1 for r in pools.values() if r["launch_to"] is None and r["selector"] is None),
        "known_pools": collections.Counter(r["known"] for r in pools.values()), "known_by_rule_pools": collections.Counter(r["known_by_rule"] for r in pools.values()), "timing": jget("timing.json"), "build_secs": round(time.time() - t0, 1)}
dump_json("summary.json", summ, indent=1)
print(json.dumps(summ, indent=1, default=str))
