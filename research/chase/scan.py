#!/usr/bin/env python3
"""scan.py CHAIN RPC PM "YYYY-mm-dd HH:MM" OUT.json : every v4 pool initialized with native as currency0 since the timestamp,
its launch tx (to, selector, from), hook, fee, tick spacing, first liquidity add (delta, ETH-side estimate), grouped by launcher."""
import json, sys, time, calendar, urllib.request, urllib.error, collections
from eth_utils import keccak
CHAIN, RPC, PM, T0, OUT = sys.argv[1], sys.argv[2], sys.argv[3].lower(), sys.argv[4], sys.argv[5]
SPAN0 = int(sys.argv[6]) if len(sys.argv) > 6 else 20000
PULLW = int(sys.argv[7]) if len(sys.argv) > 7 else 150   # blocks in ~5 minutes on this chain
SAMPLE = 25
LOOKBACK = int(sys.argv[8]) if len(sys.argv) > 8 else 6_000_000
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}; ZERO32 = "0x" + "0"*64
import os as _os
PAIR = _os.environ.get("PAIR")            # a wrapped-coin address to pair on instead of the native coin (e.g. WETH on Base)
PAIR_POS = int(_os.environ.get("PAIR_POS", "2"))   # 2 = currency0, 3 = currency1
PAIR32 = ("0x" + "0"*24 + PAIR[2:].lower()) if PAIR else ZERO32
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2+64*i:2+64*(i+1)], 16); A = lambda d, i: d[2+64*i+24:2+64*(i+1)]
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
calls = [0]
def post(body, timeout=90, url=None):
    for i in range(10):
        try:
            calls[0] += 1
            return json.load(urllib.request.urlopen(urllib.request.Request(url or RPC, json.dumps(body).encode(), H), timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code == 400: raise
            time.sleep(min(60, 4*(i+1)) if e.code == 429 else 2+i)
        except Exception:
            if i == 9: raise
            time.sleep(2+2*i)
    raise RuntimeError("rpc gave up")
import concurrent.futures as cf, os
NOBATCH = [os.environ.get("NOBATCH") == "1"]
def batch(reqs):
    """a JSON-RPC batch, or the same requests one by one in threads when the node refuses batches"""
    if not NOBATCH[0]:
        try:
            r = post(reqs, url=os.environ.get("TX_RPC") or None)
            if isinstance(r, list): return r
            NOBATCH[0] = True; print("   node refuses batches: single requests from here", flush=True)
        except urllib.error.HTTPError as e:
            NOBATCH[0] = True; print("   node refuses batches (HTTP %s): single requests from here" % e.code, flush=True)
        except Exception:
            NOBATCH[0] = True
    def one(q):
        try: return dict(post(q, timeout=40), id=q["id"])
        except Exception as e: return {"id": q["id"], "error": repr(e)[:80]}
    with cf.ThreadPoolExecutor(6) as ex: return list(ex.map(one, reqs))
def rpc(m, p):
    for i in range(8):
        r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
        if "error" in r and r["error"].get("code") == -32005 and "limit exceeded" in str(r["error"]).lower() and "range" not in str(r["error"]).lower():
            time.sleep(1.5 * (i + 1)); continue
        break
    if "error" in r:
        msg = str(r["error"]).lower()
        if any(k in msg for k in ("limit", "too many", "range", "exceed", "10000", "too large", "max")): raise OverflowError(msg)
        raise RuntimeError(msg[:200])
    return r["result"]
def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except OverflowError:
        if b <= a: raise
        m = (a+b)//2; return logs(flt, a, m) + logs(flt, m+1, b)
def block_at(ts):
    hi = int(rpc("eth_blockNumber", []), 16); lo = max(1, hi - LOOKBACK)
    while lo < hi:
        mid = (lo+hi)//2
        if int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < ts: lo = mid+1
        else: hi = mid
    return lo
def txs(hashes):
    out = {}; hs = list(hashes)
    for i in range(0, len(hs), 40):
        chunk = hs[i:i+40]; r = None
        for _ in range(4):
            r = batch([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [h]} for j, h in enumerate(chunk)])
            if isinstance(r, list) and all("result" in x and x["result"] for x in r): break
            time.sleep(3)
        if (i // 40) % 25 == 0: print(f"   txs {i+len(chunk)}/{len(hs)}", flush=True)
        for x in (r if isinstance(r, list) else []):
            t = x.get("result")
            if t: out[t["hash"]] = [t["from"][2:].lower(), (t.get("to") or "")[2:].lower(), int(t["nonce"], 16), int(t["value"], 16), t["input"][:10], int(t["blockNumber"], 16)]
    return out
def main():
    t_lo = calendar.timegm(time.strptime(T0, "%Y-%m-%d %H:%M")); head = int(rpc("eth_blockNumber", []), 16); b_lo = block_at(t_lo)
    print(f"[{CHAIN}] blocks {b_lo}-{head} ({head-b_lo})", flush=True)
    inits = []; cache = OUT + ".inits.json"
    if os.path.exists(cache): inits = json.load(open(cache)); print(f"[{CHAIN}] inits from cache {cache}", flush=True)
    else:
        for a in range(b_lo, head+1, SPAN0):
            inits += logs({"address": PM, "topics": [T_INIT, None, PAIR32] if PAIR_POS == 2 else [T_INIT, None, None, PAIR32]}, a, min(a+SPAN0-1, head))
        json.dump(inits, open(cache, "w"))
    print(f"[{CHAIN}] native-paired pools: {len(inits)} ({calls[0]} calls)", flush=True)
    pools = {}
    for l in inits:
        d = l["data"]; pid = l["topics"][1]
        pools[pid] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": l["topics"][3][-40:] if PAIR_POS == 2 else l["topics"][2][-40:], "pair_pos": PAIR_POS, "fee": W(d, 0), "ts": sgn(W(d, 1)), "hook": A(d, 2), "sqrtP0": W(d, 3), "tick0": sgn(W(d, 4))}
    tx = txs({p["tx"] for p in pools.values()})
    for p in pools.values():
        t = tx.get(p["tx"]); p["from"], p["to"], p["sel"], p["nonce"] = (t[0], t[1], t[4], t[2]) if t else (None, None, None, None)
    # first liquidity add per pool: from the launch tx receipt (same tx usually) else logs in the next 50 blocks
    byto = collections.Counter((p["to"], p["hook"], p["ts"]) for p in pools.values())
    print(f"[{CHAIN}] launchers (to, hook, tickspacing) -> count:", flush=True)
    for k, n in byto.most_common(25): print("   ", k, n, flush=True)
    # liquidity and the pull, for up to SAMPLE pools of every launcher group with >= 2 pools (batched getLogs)
    groups = collections.defaultdict(list)
    for pid, p in sorted(pools.items(), key=lambda kv: kv[1]["bn"]): groups[(p["to"], p["hook"], p["ts"])].append(pid)
    todo = [pid for k, v in groups.items() if len(v) >= 2 for pid in (v[:SAMPLE//2] + v[-(SAMPLE - SAMPLE//2):] if len(v) > SAMPLE else v)]
    todo = list(dict.fromkeys(todo)); print(f"[{CHAIN}] liquidity for {len(todo)} sampled pools in {sum(1 for v in groups.values() if len(v) >= 2)} groups", flush=True)
    for i in range(0, len(todo), 10):
        chunk = todo[i:i+10]
        body = [{"jsonrpc": "2.0", "id": j, "method": "eth_getLogs", "params": [{"address": PM, "topics": [T_ML, pid], "fromBlock": hex(pools[pid]["bn"]), "toBlock": hex(pools[pid]["bn"] + PULLW)}]} for j, pid in enumerate(chunk)]
        try: r = batch(body)
        except Exception as e: print("   batch failed", repr(e)[:80], flush=True); continue
        for x in r:
            if "result" not in x or not isinstance(x.get("id"), int): continue
            p = pools[chunk[x["id"]]]; ls = x["result"]
            adds = [(int(l["blockNumber"], 16), sgn(W(l["data"], 2)), sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), l["transactionHash"]) for l in ls]
            p["liq"] = [a for a in adds if a[1] > 0][:2]; p["pull"] = [a[0] - p["bn"] for a in adds if a[1] < 0][:1]
            if p["liq"]:
                L, tl, tu = p["liq"][0][1], p["liq"][0][2], p["liq"][0][3]; sp = p["sqrtP0"]/2**96
                spl, spu = 1.0001**(tl/2), 1.0001**(tu/2); spc = min(max(sp, spl), spu)
                p["eth0"] = L*(spu-spc)/(spc*spu)/1e18 if spu > spc else 0.0
    json.dump({"chain": CHAIN, "from": T0, "blocks": [b_lo, head], "pools": pools}, open(OUT, "w"))
    print(f"[{CHAIN}] done, {len(pools)} pools, {calls[0]} calls -> {OUT}", flush=True)
main()
