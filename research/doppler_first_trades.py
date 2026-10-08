#!/usr/bin/env python3
"""The Doppler-hook v4 launches on Robinhood Chain (hook 0x4e3468951d: LONG, and Bankr through Doppler's Rehype hook, whose launch
fee falls from 80% to 1.69% over the first ten seconds): how many a day, and does anyone trade them in the first minute? A seat at
the ten-second boundary needs a crowd to sell into. A sample of the last 24 hours: every swap in the first 600 blocks with its
whole second since creation and the fee field of the Swap event (the LP fee; the hook's own launch fee is not in it).

    python3 src/analysis/doppler_first_trades.py [sample=200]
"""
import json, sys, time, random, collections, statistics as st, urllib.request
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128", "Accept": "application/json"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; HOOK = "4e3468951d49f2eea976ed0d6e75ffcb44a9a544"; N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
def post(b):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(b).encode(), H), timeout=90))
        except Exception: time.sleep(3 + 3 * i)
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise OverflowError(str(r["error"]))
    return r["result"]
def logs(f, a, b):
    try: return rpc("eth_getLogs", [dict(f, fromBlock=hex(a), toBlock=hex(b))])
    except OverflowError:
        m = (a + b) // 2; return logs(f, a, m) + logs(f, m + 1, b)
head = int(rpc("eth_blockNumber", []), 16); lo = head - 864000 - 600; pools = {}
for a in range(lo, head - 600, 99999):
    for l in logs({"address": PM, "topics": [T_INIT]}, a, min(a + 99998, head - 600)):
        d = l["data"]
        if d[2 + 64*2 + 24: 2 + 64*3] == HOOK: pools[l["topics"][1]] = {"bn": int(l["blockNumber"], 16), "eth": l["topics"][2][-40:] == "0" * 40, "ts": int(d[66:130], 16)}
print(f"Doppler-hook launches in the last 24 h: {len(pools)} ({sum(p['eth'] for p in pools.values())} paired with ETH); tick spacing "
      f"{dict(collections.Counter(p['ts'] for p in pools.values()))}")
random.seed(3); smp = random.sample(sorted(pools), min(N, len(pools))); sw = collections.defaultdict(list)
for i in range(0, len(smp), 90):
    b = smp[i:i+90]; a0 = min(pools[p]["bn"] for p in b); a1 = max(pools[p]["bn"] for p in b) + 600
    for a in range(a0, a1, 99999):
        for l in logs({"address": PM, "topics": [T_SWAP, b]}, a, min(a + 99998, a1)):
            pid = l["topics"][1]; bn = int(l["blockNumber"], 16)
            if bn <= pools[pid]["bn"] + 600: sw[pid].append((bn, int(l["data"][2 + 64*5: 2 + 64*6], 16)))
bns = sorted({pools[p]["bn"] for p in smp} | {x[0] for v in sw.values() for x in v}); ts = {}
for i in range(0, len(bns), 50):
    for x in post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), False]} for j, b in enumerate(bns[i:i+50])]):
        ts[int(x["result"]["number"], 16)] = int(x["result"]["timestamp"], 16)
first = []; by_s = collections.defaultdict(list)
for pid in smp:
    v = sorted(sw.get(pid, []))
    if not v: continue
    t0 = ts[pools[pid]["bn"]]; first.append(ts[v[0][0]] - t0)
    for bn, fee in v: by_s[min(ts[bn] - t0, 20)].append(fee / 1e4)
print(f"sampled {len(smp)}: {len(first)} had a swap in the first minute ({len(first)/len(smp):.0%}); first swap at second p10/50/90 "
      f"{[sorted(first)[int(q*(len(first)-1))] for q in (.1, .5, .9)] if first else []}")
for s in sorted(by_s): print(f"   second {s:2d}{'+' if s == 20 else ' '}: {len(by_s[s]):4d} swaps, Swap-event fee median {st.median(by_s[s]):.2f}%")
