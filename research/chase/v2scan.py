#!/usr/bin/env python3
"""v2scan.py RPC FACTORY WETH FROM_BLOCK OUT [HORIZON=900 SWAPWIN=300]: every WETH pair created on a Uniswap-V2 factory since FROM_BLOCK,
its creator, its first Mint (ETH side), Burns (pulls) inside HORIZON blocks, swaps inside SWAPWIN blocks with the wallet behind each."""
import json, sys, time, urllib.request, urllib.error, collections, concurrent.futures as cf
from eth_utils import keccak
RPC, FACTORY, WETH, B0, OUT = sys.argv[1], sys.argv[2].lower(), sys.argv[3].lower(), int(sys.argv[4]), sys.argv[5]
HORIZON = int(sys.argv[6]) if len(sys.argv) > 6 else 900; SWAPWIN = int(sys.argv[7]) if len(sys.argv) > 7 else 300
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
T_PC = "0x"+keccak(text="PairCreated(address,address,address,uint256)").hex(); T_MINT = "0x"+keccak(text="Mint(address,uint256,uint256)").hex()
T_BURN = "0x"+keccak(text="Burn(address,uint256,uint256,address)").hex(); T_SW = "0x"+keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()
W = lambda d, i: int(d[2+64*i:2+64*(i+1)], 16); W32 = "0x" + "0"*24 + WETH[2:]
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=90))
            if "result" in r: return r["result"]
            time.sleep(2)
        except urllib.error.HTTPError as e: time.sleep(6 if e.code == 429 else 2)
        except Exception: time.sleep(2)
    return None
head = int(rpc("eth_blockNumber", []), 16); print(f"blocks {B0}-{head}", flush=True)
pairs = {}
for pos in (1, 2):
    for a in range(B0, head+1, 5000):
        ls = rpc("eth_getLogs", [{"address": FACTORY, "topics": [T_PC, W32, None] if pos == 1 else [T_PC, None, W32], "fromBlock": hex(a), "toBlock": hex(min(a+4999, head))}]) or []
        for l in ls:
            pair = "0x" + l["data"][2:66][-40:]; pairs[pair] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": l["topics"][2 if pos == 1 else 1][-40:], "weth_is0": pos == 1}
print(f"WETH pairs created: {len(pairs)}", flush=True)
def events(pair):
    p = pairs[pair]; ls = rpc("eth_getLogs", [{"address": pair, "topics": [[T_MINT, T_BURN, T_SW]], "fromBlock": hex(p["bn"]), "toBlock": hex(p["bn"]+HORIZON)}]) or []
    mints, burns, swaps = [], [], []
    for l in ls:
        bn = int(l["blockNumber"], 16); d = l["data"]; t0 = l["topics"][0]
        if t0 == T_MINT: mints.append((bn, W(d, 0), W(d, 1), l["transactionHash"]))
        elif t0 == T_BURN: burns.append((bn, W(d, 0), W(d, 1), l["transactionHash"]))
        elif bn <= p["bn"] + SWAPWIN: swaps.append((bn, int(l["logIndex"], 16), W(d, 0), W(d, 1), W(d, 2), W(d, 3), l["transactionHash"]))
    return pair, mints, burns, swaps
with cf.ThreadPoolExecutor(4) as ex:
    for n, (pair, mints, burns, swaps) in enumerate(ex.map(events, list(pairs))):
        p = pairs[pair]; p["mints"], p["burns"], p["swaps"] = mints, burns, swaps
        if mints: p["eth_in"] = (mints[0][1] if p["weth_is0"] else mints[0][2]) / 1e18
        if n % 100 == 0: print(f"  events {n}/{len(pairs)}", flush=True)
hashes = list(dict.fromkeys([p["tx"] for p in pairs.values()] + [s[6] for p in pairs.values() for s in p["swaps"][:25]]))
print(f"tx lookups: {len(hashes)}", flush=True)
def tx(h):
    t = rpc("eth_getTransactionByHash", [h]); return h, ([t["from"][2:].lower(), (t.get("to") or "")[2:].lower(), int(t["nonce"], 16), int(t["value"], 16), t["input"][:10]] if t else None)
txs = {}
with cf.ThreadPoolExecutor(4) as ex:
    for n, (h, t) in enumerate(ex.map(tx, hashes)):
        if t: txs[h] = t
        if n % 500 == 0: print(f"  txs {n}/{len(hashes)}", flush=True)
for p in pairs.values():
    t = txs.get(p["tx"]); p["from"], p["to"], p["nonce"], p["sel"] = (t[0], t[1], t[2], t[4]) if t else (None, None, None, None)
json.dump({"factory": FACTORY, "weth": WETH, "blocks": [B0, head], "pairs": pairs, "txs": txs}, open(OUT, "w")); print("done ->", OUT, flush=True)
