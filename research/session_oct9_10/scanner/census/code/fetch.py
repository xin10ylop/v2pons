#!/usr/bin/env python3
"""Census fetch, stage by stage, every RPC result appended to cache/*.jsonl as it arrives (rerun resumes).

    python3 -I fetch.py window|inits|ltx|codes|blocks|events|stx|dex|all
"""
import sys, os, json, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

ZERO32 = "0x" + "0" * 64
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
SPAN = 3000
T_PAIR = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex()
T_POOL = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_SOLID = "0x" + keccak(text="PairCreated(address,address,bool,address,uint256)").hex()     # Solidly / Aerodrome / Velodrome style
T_ALGEBRA = "0x" + keccak(text="Pool(address,address,address)").hex()                         # Algebra style
T_FAC = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"                   # bonding-curve factory create (third/fac_logs.py)
FAC = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"


def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


def window():
    w = jget("window.json")
    if w: return w
    t0 = time.time()
    head = int(rpc("eth_blockNumber", []), 16); head_ts = block_ts(head)
    now = int(time.time()); start_ts = now - 48 * 3600
    a = block_at(start_ts, head)
    w = {"from_block": a, "from_ts": block_ts(a), "head": head, "head_ts": head_ts, "now_at_start": now, "target_from_ts": start_ts}
    jput("window.json", w); timing("window", time.time() - t0); log("window", w); return w


def compact_log(l):
    return {"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
            "addr": l["address"].lower(), "topics": l["topics"], "data": l["data"]}


def inits():
    w = window(); t0 = time.time()
    done = jl_read("inits.jsonl"); last = max([c["b"] for c in done], default=w["from_block"] - 1)
    a = last + 1
    while a <= w["head"]:
        b = min(a + 99_999, w["head"])
        ls = logs({"address": PM, "topics": [T_INIT]}, a, b)
        jl_append("inits.jsonl", [{"a": a, "b": b, "logs": [compact_log(l) for l in ls]}]); log("inits", a, b, len(ls)); a = b + 1
    n = sum(len(c["logs"]) for c in jl_read("inits.jsonl"))
    timing("inits", time.time() - t0, {"init_logs": n})


def all_inits():
    seen = set(); out = []
    for c in jl_read("inits.jsonl"):
        for l in c["logs"]:
            k = (l["tx"], l["li"])
            if k not in seen: seen.add(k); out.append(l)
    return sorted(out, key=lambda l: (l["bn"], l["li"]))


def eth_inits(): return [l for l in all_inits() if l["topics"][2] == ZERO32]


def trim_tx(t, full_max=2048):
    inp = t.get("input") or "0x"; n = (len(inp) - 2) // 2
    d = {"hash": t["hash"], "from": (t.get("from") or "").lower(), "to": (t.get("to") or None) and t["to"].lower(), "value_wei": int(t.get("value") or "0x0", 16),
         "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16) if t.get("blockNumber") else None,
         "ti": int(t["transactionIndex"], 16) if t.get("transactionIndex") else None, "type": int(t.get("type") or "0x0", 16), "gas": int(t["gas"], 16),
         "gas_price": int(t["gasPrice"], 16) if t.get("gasPrice") else None,
         "max_fee": int(t["maxFeePerGas"], 16) if t.get("maxFeePerGas") else None,
         "max_prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
         "selector": inp[2:10], "calldata_len": n, "input512": inp[:2 + 1024]}
    if n < full_max: d["input"] = inp
    if t.get("authorizationList"): d["auth"] = t["authorizationList"]
    return d


def fetch_txs(hashes, cache, label):
    have = {x["hash"] for x in jl_read(cache)}
    need = [h for h in dict.fromkeys(hashes) if h not in have]
    log(label, "need", len(need), "have", len(have)); t0 = time.time()
    for i in range(0, len(need), 500):
        ch = need[i:i + 500]
        r = batch([("eth_getTransactionByHash", [h]) for h in ch])
        rows = [trim_tx(t) for t in r if t]
        miss = [h for h, t in zip(ch, r) if not t]
        jl_append(cache, rows)
        if miss: jl_append("missing_txs.jsonl", [{"hash": h, "stage": label} for h in miss])
        if i % 5000 == 0: log(label, i + len(ch), "/", len(need), f"{time.time() - t0:.0f}s")


def ltx():
    t0 = time.time()
    L = eth_inits()
    fetch_txs([l["tx"] for l in L], "ltx.jsonl", "ltx")
    # contract-creation launches -> receipt (contractAddress, status, gasUsed)
    T = {x["hash"]: x for x in jl_read("ltx.jsonl")}
    have = {x["hash"] for x in jl_read("lrcpt.jsonl")}
    need = [h for h, t in T.items() if t["to"] is None and h not in have]
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]; r = batch([("eth_getTransactionReceipt", [h]) for h in ch], size=20)
        jl_append("lrcpt.jsonl", [{"hash": h, "contract": x.get("contractAddress"), "status": x.get("status"), "gas_used": int(x["gasUsed"], 16)} for h, x in zip(ch, r) if x])
    timing("ltx", time.time() - t0, {"launch_txs": len(T), "creates": len(need)})


def codes():
    """code size + hash of every launch `to` (latest state; no archive)"""
    t0 = time.time()
    tos = sorted({t["to"] for t in jl_read("ltx.jsonl") if t["to"]} | {r["contract"].lower() for r in jl_read("lrcpt.jsonl") if r.get("contract")})
    have = {x["addr"] for x in jl_read("codes.jsonl")}
    need = [a for a in tos if a not in have]
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]; r = batch([("eth_getCode", [a, "latest"]) for a in ch], size=20)
        rows = []
        for a, c in zip(ch, r):
            if c is None: continue
            b = bytes.fromhex(c[2:])
            rows.append({"addr": a, "size": len(b), "hash": keccak(b).hex() if b else None, "head": c[:2 + 96]})
        jl_append("codes.jsonl", rows)
        if i % 400 == 0: log("codes", i, len(need))
    timing("codes", time.time() - t0, {"addresses": len(tos)})


def blocks():
    t0 = time.time()
    bns = sorted({l["bn"] for l in eth_inits()})
    have = {x["bn"] for x in jl_read("blocks.jsonl")}
    need = [b for b in bns if b not in have]
    for i in range(0, len(need), 500):
        ch = need[i:i + 500]; r = batch([("eth_getBlockByNumber", [hex(b), False]) for b in ch])
        jl_append("blocks.jsonl", [{"bn": b, "ts": int(x["timestamp"], 16), "basefee": int(x.get("baseFeePerGas") or "0x0", 16), "ntx": len(x["transactions"])}
                                   for b, x in zip(ch, r) if x])
        log("blocks", i + len(ch), len(need))
    timing("blocks", time.time() - t0, {"blocks": len(bns)})


def family_key(init, tx):
    d = init["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
    to = tx["to"] if tx else None
    return f"{to or 'create'}|{tx['selector'] if tx else '?'}|{tx['calldata_len'] if tx else -1}|{fee}|{ts}|{str(int(hooks, 16) == 0).lower()}"


def events(min_fam=5, which="big"):
    """Swap + ModifyLiquidity of each pool over [launch, launch + SPAN] (capped at the head at fetch time). which = big (families >= min_fam)
    or rest (the others)."""
    t0 = time.time()
    L = eth_inits(); T = {x["hash"]: x for x in jl_read("ltx.jsonl")}
    fam = {l["topics"][1]: family_key(l, T.get(l["tx"])) for l in L}
    cnt = collections.Counter(fam.values())
    sel = [l for l in L if (cnt[fam[l["topics"][1]]] >= min_fam) == (which == "big")]
    done = set()
    for g in jl_read("ev_groups.jsonl"):
        for p in g["pids"]: done.add(p)
    head = int(rpc("eth_blockNumber", []), 16)
    todo = [(l["bn"], l["topics"][1]) for l in sel if l["topics"][1] not in done]
    seen = set(); todo2 = []
    for b, p in todo:
        if p in seen: continue
        seen.add(p); todo2.append((b, p))
    todo = sorted(todo2)
    groups = []; g = []
    for b, p in todo:
        if g and (b - g[0][0] > 6000 or len(g) >= 20): groups.append(g); g = []
        g.append((b, p))
    if g: groups.append(g)
    log("events", which, "pools", len(todo), "groups", len(groups), "head", head)
    for gi, g in enumerate(groups):
        a = g[0][0]; z = min(head, g[-1][0] + SPAN); ids = [p for _, p in g]
        ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, z)
        jl_append("ev_groups.jsonl", [{"pids": ids, "launch": {p: b for b, p in g}, "a": a, "b": z, "head": head, "logs": [compact_log(l) for l in ls]}])
        if gi % 25 == 0: log("events", which, gi, "/", len(groups), len(ls), f"{time.time() - t0:.0f}s")
    timing(f"events_{which}", time.time() - t0, {"pools": len(todo), "groups": len(groups)})


def pool_swaps():
    """pid -> sorted swap logs within [launch, launch + SPAN]"""
    out = {}
    for g in jl_read("ev_groups.jsonl"):
        for l in g["logs"]:
            p = l["topics"][1]
            if p not in g["launch"] or l["topics"][0] != T_SWAP: continue
            lb = g["launch"][p]
            if lb <= l["bn"] <= lb + SPAN: out.setdefault(p, {})[(l["bn"], l["li"])] = l
    return {p: [v[k] for k in sorted(v)] for p, v in out.items()}


def pool_pulls():
    """pid -> sorted ModifyLiquidity logs with a negative delta within [launch, launch + SPAN]"""
    out = {}
    for g in jl_read("ev_groups.jsonl"):
        for l in g["logs"]:
            p = l["topics"][1]
            if p not in g["launch"] or l["topics"][0] != T_ML or sgn(W(l["data"], 2)) >= 0: continue
            lb = g["launch"][p]
            if lb <= l["bn"] <= lb + SPAN: out.setdefault(p, {})[(l["bn"], l["li"])] = l
    return {p: [v[k] for k in sorted(v)] for p, v in out.items()}


def stx(n_first=8):
    """the transactions of each pool's first n_first swaps, then of its first two pulls"""
    t0 = time.time()
    S = pool_swaps(); hs = []
    for p, sw in S.items():
        for l in sw[:n_first]: hs.append(l["tx"])
    fetch_txs(hs, "stx.jsonl", "stx")
    P = pool_pulls(); ph = [l["tx"] for p, pl in P.items() for l in pl[:2]]
    fetch_txs(ph, "stx.jsonl", "ptx")
    timing("stx", time.time() - t0, {"pools_with_swaps": len(S), "swap_hashes": len(set(hs)), "pools_with_pulls": len(P), "pull_hashes": len(set(ph))})


def dex():
    """no-address scans (30k-block cap) for V2/V3/Solidly/Algebra factory events and v4 Initialize from any PoolManager; plus the
    bonding-curve factory's creates."""
    w = window(); t0 = time.time()
    done = jl_read("dex.jsonl"); last = max([c["b"] for c in done if c["kind"] == "noaddr"], default=w["from_block"] - 1)
    a = last + 1
    while a <= w["head"]:
        b = min(a + 29_999, w["head"])
        ls = logs({"topics": [[T_PAIR, T_POOL, T_SOLID, T_ALGEBRA, T_INIT]]}, a, b)
        rows = [compact_log(l) for l in ls if not (l["address"].lower() == PM and l["topics"][0] == T_INIT)]
        npm = sum(1 for l in ls if l["address"].lower() == PM and l["topics"][0] == T_INIT)
        jl_append("dex.jsonl", [{"kind": "noaddr", "a": a, "b": b, "pm_inits": npm, "logs": rows}])
        log("dex", a, b, len(ls), npm); a = b + 1
    last = max([c["b"] for c in done if c["kind"] == "fac"], default=w["from_block"] - 1)
    a = last + 1
    while a <= w["head"]:
        b = min(a + 99_999, w["head"])
        ls = logs({"address": FAC, "topics": [T_FAC]}, a, b)
        jl_append("dex.jsonl", [{"kind": "fac", "a": a, "b": b, "logs": [{"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "topics": l["topics"], "data": l["data"][:2 + 64 * 4]} for l in ls]}])
        log("fac", a, b, len(ls)); a = b + 1
    timing("dex", time.time() - t0)


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"window": window, "inits": inits, "ltx": ltx, "codes": codes, "blocks": blocks, "events": lambda: events(which="big"),
             "events_rest": lambda: events(which="rest"), "stx": stx, "dex": dex}
    for s in (steps if st == "all" else [st]):
        if st == "all" and s == "events_rest": continue
        log("== stage", s); steps[s]()
    log("STATS", STATS)
