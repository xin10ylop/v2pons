#!/usr/bin/env python3
"""The 2-2.45% fee v4 launch family on Robinhood Chain (no hook, tick spacing 200, ETH as currency0; report 24.45's "only open
candidate"), widened to every no-hook tick-200 ETH pool with a 1.5-5% fee (from Oct 1 the operator spreads its launches over odd
fees, so the family is found by its launcher, not its fee), pulled for the natural-experiment test of the trap: every launch in a window, every swap on each in its first 20
minutes, every liquidity change, and the wallet behind every swap (tx.from, its nonce at that transaction, the router it called).
Public RPC: Initialize logs filtered on currency0 = ETH, 429 backoff, batched transaction lookups.

    python3 src/analysis/v4_slowrug_pull.py "2026-09-29 21:00" "2026-10-08 10:30" data/derived/edge_check/Q/slowrug.json

With a launcher address as a fourth argument it follows that launcher instead of the fee band: every no-hook tick-200 ETH pool
OUTSIDE the band (the 1% family and the 88% dynamic-fee pools excepted) whose launch transaction calls it. The family's operator,
0x3194e326, moved from 2-2.45% fees to 0.01-0.1% on Oct 5:

    python3 src/analysis/v4_slowrug_pull.py "2026-09-29 21:00" "2026-10-08 10:30" data/derived/edge_check/Q/slowrug_op.json 0x3194e32622c5d860a0572c74edda99dcfd8fc827
"""
import json, sys, time, calendar, urllib.request, urllib.error, collections
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128", "Accept": "application/json"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; ZERO32 = "0x" + "0" * 64
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
FEE_LO, FEE_HI, TS = 15000, 50000, 200; HORIZON = 12000; SPAN = 250000; SPAN_T = 99999   # the node allows 100k blocks for a topic-batched query
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); A = lambda d, i: d[2 + 64*i + 24: 2 + 64*(i+1)]
def signed(x): return x - (1 << 256) if x >= (1 << 255) else x
calls = [0]
def post(body):
    for i in range(12):
        try:
            calls[0] += 1
            return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e:
            time.sleep(min(60, 4 * (i + 1)) if e.code == 429 else 2 + i)
        except Exception:
            if i == 11: raise
            time.sleep(2 + 2 * i)
    raise RuntimeError("rpc gave up")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r:
        msg = str(r["error"])
        if "exceeds limit" in msg or "max topics" in msg or "too many" in msg.lower(): raise OverflowError(msg)
        raise RuntimeError(msg[:160])
    return r["result"]
def logs(flt, a, b):
    try:
        return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except OverflowError:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)
def block_at(ts):
    lo, hi = 1, int(rpc("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo + hi) // 2
        if int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
    return lo
def txs(hashes):
    """{hash: [from, to, nonce, value_wei, selector]} through batched eth_getTransactionByHash"""
    out = {}; hs = list(hashes)
    for i in range(0, len(hs), 50):
        chunk = hs[i:i+50]
        for _ in range(6):
            r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [h]} for j, h in enumerate(chunk)])
            if isinstance(r, list) and all("result" in x and x["result"] for x in r): break
            time.sleep(3)
        for x in (r if isinstance(r, list) else []):
            t = x.get("result")
            if t: out[t["hash"]] = [t["from"][2:].lower(), (t.get("to") or "")[2:].lower(), int(t["nonce"], 16), int(t["value"], 16), t["input"][:10]]
        if (i // 50) % 40 == 0: print(f"  txs {i + len(chunk)} of {len(hs)} ({calls[0]} calls)", flush=True)
    return out
def main():
    global LAUNCHER
    LAUNCHER = sys.argv[4][2:].lower() if len(sys.argv) > 4 else ""
    t_lo = calendar.timegm(time.strptime(sys.argv[1], "%Y-%m-%d %H:%M")); t_hi = calendar.timegm(time.strptime(sys.argv[2], "%Y-%m-%d %H:%M")); out = sys.argv[3]
    b_lo, b_hi = block_at(t_lo), block_at(t_hi); t0 = time.time(); print(f"blocks {b_lo}-{b_hi}", flush=True)
    pools = {}; n_eth = 0; sib = collections.Counter()
    for a in range(b_lo, b_hi, SPAN):
        for l in logs({"address": PM, "topics": [T_INIT, None, ZERO32]}, a, min(a + SPAN - 1, b_hi)):
            d = l["data"]; n_eth += 1; fee, ts, hook = W(d, 0), signed(W(d, 1)), A(d, 2)
            if hook == "0" * 40 and ts == TS and fee >= 15000: sib[fee] += 1
            if hook != "0" * 40 or ts != TS: continue
            if LAUNCHER:
                if FEE_LO <= fee <= FEE_HI or fee in (10000, 883131, 880238): continue
            elif not FEE_LO <= fee <= FEE_HI: continue
            pools[l["topics"][1]] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "c1": l["topics"][3][-40:], "fee": fee, "sqrtP0": W(d, 3), "tick0": signed(W(d, 4))}
    if LAUNCHER:                                                  # keep the launches whose transaction calls the launcher
        lt = txs({p["tx"] for p in pools.values()}); pools = {k: v for k, v in pools.items() if lt.get(v["tx"], ["", ""])[1] == LAUNCHER}
    print(f"{n_eth} ETH-paired pools initialized, {len(pools)} in the family ({time.time()-t0:.0f} s); no-hook tick-200 fees >= 1.5%: {dict(sib.most_common())}", flush=True)
    pids = sorted(pools, key=lambda p: pools[p]["bn"]); swaps = collections.defaultdict(list); liq = collections.defaultdict(list)
    for i in range(0, len(pids), 90):
        batch = pids[i:i+90]; lo_b = min(pools[p]["bn"] for p in batch); hi_b = max(pools[p]["bn"] for p in batch) + HORIZON
        for a in range(lo_b, hi_b, SPAN_T):
            for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], batch]}, a, min(a + SPAN_T - 1, hi_b)):
                pid = l["topics"][1]; bn = int(l["blockNumber"], 16); d = l["data"]
                if not pools[pid]["bn"] <= bn <= pools[pid]["bn"] + HORIZON: continue
                if l["topics"][0] == T_SWAP:
                    swaps[pid].append([bn, int(l["logIndex"], 16), l["topics"][2][-40:], signed(W(d, 0)), signed(W(d, 1)), W(d, 2), W(d, 3), W(d, 5), l["transactionHash"]])
                else:
                    liq[pid].append([bn, int(l["logIndex"], 16), l["topics"][2][-40:], signed(W(d, 0)), signed(W(d, 1)), signed(W(d, 2)), l["transactionHash"]])
        print(f"  logs for {i + len(batch)} of {len(pids)} pools: {sum(len(v) for v in swaps.values())} swaps, {sum(len(v) for v in liq.values())} liquidity events ({time.time()-t0:.0f} s)", flush=True)
    hashes = {x[8] for v in swaps.values() for x in v} | {x[6] for v in liq.values() for x in v} | {p["tx"] for p in pools.values()}
    T = txs(hashes); bns = sorted({p["bn"] for p in pools.values()}); launch_ts = {}
    for i in range(0, len(bns), 50):                              # the launch blocks' timestamps (days, hours)
        for x in post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), False]} for j, b in enumerate(bns[i:i+50])]):
            launch_ts[int(x["result"]["number"], 16)] = int(x["result"]["timestamp"], 16)
    json.dump({"window": [sys.argv[1], sys.argv[2]], "blocks": [b_lo, b_hi], "family": [FEE_LO, FEE_HI, TS, LAUNCHER], "pools": pools, "swaps": dict(swaps), "liquidity": dict(liq), "txs": T, "launch_ts": launch_ts,
               "swap_fields": ["bn", "logIndex", "sender", "amount0", "amount1", "sqrtPriceX96", "liquidity", "fee", "tx"],
               "liquidity_fields": ["bn", "logIndex", "sender", "tickLower", "tickUpper", "liquidityDelta", "tx"], "tx_fields": ["from", "to", "nonce", "value", "selector"]}, open(out, "w"))
    print(f"wrote {out}: {len(pools)} launches, {sum(len(v) for v in swaps.values())} swaps, {len(T)} transactions ({time.time()-t0:.0f} s, {calls[0]} calls)", flush=True)
main()
