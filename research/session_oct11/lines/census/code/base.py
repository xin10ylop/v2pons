"""The pool list (from stage-1 logs) and shared constants."""
import os, json, collections
from lib2 import *

Z = "0x0000000000000000000000000000000000000000"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"; USDG2 = "0x386c702c290a954d1c0ba0efc12d51373e02d3f3"
QUOTES = {Z: ("ETH", 18), WETH: ("WETH", 18), USDG: ("USDG", 6), USDG2: ("USDG2", 18)}
V2F = {"0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f": "v2a", "0x0d1ebb179cdbca88d74c923c4255cb2b17474afd": "v2b"}
V3F = {"0x1f7d7550b1b028f7571e69a784071f0205fd2efa": "v3"}
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_PAIR = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex()
T_POOL = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T2_SWAP = "0x" + keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()
T2_MINT = "0x" + keccak(text="Mint(address,uint256,uint256)").hex()
T2_BURN = "0x" + keccak(text="Burn(address,uint256,uint256,address)").hex()
T3_SWAP = "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()
T3_MINT = "0x" + keccak(text="Mint(address,address,int24,int24,uint128,uint256,uint256)").hex()
T3_BURN = "0x" + keccak(text="Burn(address,int24,int24,uint128,uint256,uint256)").hex()
SPAN = 3000
ETH_PER_USDG = 1 / 2570.0     # fixed conversion for USDG-quoted pools (documented in the README; ETH ~ $2,570 on Oct 11)
A = lambda t: "0x" + t[26:]


def window(): return jget("window.json")


def base_pools():
    """every in-scope pool: v4 with ETH/WETH/USDG on a side, V2/V3 on the three factories with WETH on a side. Sorted by (bn, li)."""
    out = []
    for r in jl_read("inits.jsonl"):
        for l in r["logs"]:
            c0, c1 = A(l["topics"][2]), A(l["topics"][3]); q0, q1 = c0 in QUOTES, c1 in QUOTES
            if not (q0 or q1): continue
            d = l["data"]; qs = 0 if q0 else 1
            out.append({"dex": "v4", "pool": l["topics"][1], "c0": c0, "c1": c1, "quote_side": qs, "quote": QUOTES[(c0, c1)[qs]][0],
                        "token": (c0, c1)[1 - qs], "quote_pair": q0 and q1, "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)),
                        "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrt_p0": W(d, 3), "tick0": sgn(W(d, 4)),
                        "launch_block": l["bn"], "ti": l["ti"], "li": l["li"], "launch_tx": l["tx"]})
    for r in jl_read("factory.jsonl"):
        for l in r["logs"]:
            c0, c1 = A(l["topics"][1]), A(l["topics"][2])
            if WETH not in (c0, c1): continue
            qs = 0 if c0 == WETH else 1
            if l["topics"][0] == T_PAIR:
                row = {"dex": V2F[l["addr"]], "pool": A(l["data"][:66]), "fee": 3000, "tick_spacing": None}
            else:
                row = {"dex": "v3", "pool": A("0x" + l["data"][2 + 64: 2 + 128]), "fee": int(l["topics"][3], 16), "tick_spacing": sgn(W(l["data"], 0))}
            other = (c0, c1)[1 - qs]
            row.update({"factory": l["addr"], "c0": c0, "c1": c1, "quote_side": qs, "quote": "WETH", "token": other, "quote_pair": other in QUOTES,
                        "launch_block": l["bn"], "ti": l["ti"], "li": l["li"], "launch_tx": l["tx"]})
            out.append(row)
    out.sort(key=lambda r: (r["launch_block"], r["li"]))
    seen = set(); res = []
    for r in out:
        k = (r["dex"], r["pool"])
        if k in seen: continue
        seen.add(k); res.append(r)
    return res


def trim_tx(t, full_max=4096, head_words=None):
    inp = t.get("input") or "0x"; n = (len(inp) - 2) // 2
    d = {"hash": t["hash"], "from": (t.get("from") or "").lower(), "to": (t.get("to") or None) and t["to"].lower(), "value_wei": int(t.get("value") or "0x0", 16),
         "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16) if t.get("blockNumber") else None,
         "ti": int(t["transactionIndex"], 16) if t.get("transactionIndex") else None, "type": int(t.get("type") or "0x0", 16), "gas": int(t["gas"], 16),
         "gas_price": int(t["gasPrice"], 16) if t.get("gasPrice") else None,
         "max_fee": int(t["maxFeePerGas"], 16) if t.get("maxFeePerGas") else None,
         "max_prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
         "selector": inp[2:10], "calldata_len": n}
    if head_words is not None: d["input_head"] = inp[:10 + 64 * head_words]
    elif n < full_max: d["input"] = inp
    else: d["input_head"] = inp[:2 + 2048]
    if t.get("authorizationList"): d["auth"] = len(t["authorizationList"])
    return d


def old_tx_iter():
    """the first census's cached transactions (same trim format, input kept below 2,048 bytes)"""
    for name in ("ltx.jsonl", "stx.jsonl"):
        for x in jl_iter(name, OLD): yield x


def fetch_txs(hashes, cache, label, head_words=None, have=None, chunk=500):
    if have is None: have = {x["hash"] for x in jl_iter(cache)}
    need = [h for h in dict.fromkeys(hashes) if h not in have]
    log(label, "need", len(need), "have", len(have)); t0 = time.time()
    for i in range(0, len(need), chunk):
        ch = need[i:i + chunk]
        r = batch([("eth_getTransactionByHash", [h]) for h in ch])
        rows = [trim_tx(t, head_words=head_words) for t in r if t]
        miss = [h for h, t in zip(ch, r) if not t]
        jl_append(cache, rows)
        if miss: jl_append("missing_txs.jsonl", [{"hash": h, "stage": label} for h in miss])
        if (i // chunk) % 10 == 0: log(label, i + len(ch), "/", len(need), f"{time.time() - t0:.0f}s", STATS)
    return len(need)
