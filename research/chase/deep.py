#!/usr/bin/env python3
"""rh_deep.py: every swap and liquidity event in the first 3000 blocks (5 min) of the operator's pools on Robinhood since Oct 15,
with the wallet behind each swap, to price the trade again."""
import json, os, sys, time, urllib.request, urllib.error, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from eth_utils import keccak
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
# deep.py LAUNCHER OUT [SCAN_JSON RPC PM HORIZON HOOK]
LAUNCHER = (sys.argv[1][2:].lower() if sys.argv[1].startswith("0x") else sys.argv[1].lower()) if len(sys.argv) > 1 else "3194e32622c5d860a0572c74edda99dcfd8fc827"; OUT = sys.argv[2] if len(sys.argv) > 2 else "rh_deep.json"
SCAN = sys.argv[3] if len(sys.argv) > 3 else "rh.json"; RPC = sys.argv[4] if len(sys.argv) > 4 else "https://rpc.mainnet.chain.robinhood.com"
PM = sys.argv[5] if len(sys.argv) > 5 else "0x8366a39cc670b4001a1121b8f6a443a643e40951"; HORIZON = int(sys.argv[6]) if len(sys.argv) > 6 else 3000
HOOK = sys.argv[7][2:].lower() if len(sys.argv) > 7 else None
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex(); T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2+64*i:2+64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
import os, concurrent.futures as cf
TX_RPC = os.environ.get("TX_RPC"); NOBATCH = os.environ.get("NOBATCH") == "1"
def post1(body, url=None):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url or RPC, json.dumps(body).encode(), H), timeout=120))
        except urllib.error.HTTPError as e:
            if e.code == 400: raise
            time.sleep(min(60, 4*(i+1)) if e.code == 429 else 2+i)
        except Exception:
            if i == 9: raise
            time.sleep(2+2*i)
    raise RuntimeError("rpc gave up")
def post(body, url=None):
    """a batch; on a node that refuses batches (NOBATCH=1) the same requests one by one in 4 threads"""
    if isinstance(body, list) and NOBATCH and not url:
        def one(q):
            try: return dict(post1(q), id=q["id"])
            except Exception as e: return {"id": q["id"], "error": repr(e)[:80]}
        with cf.ThreadPoolExecutor(4) as ex: return list(ex.map(one, body))
    return post1(body, url)
d = json.load(open(SCAN))
if LAUNCHER.startswith("sel:"): pools = {pid: p for pid, p in d["pools"].items() if p.get("sel") == "0x" + LAUNCHER[4:].replace("0x", "") and (HOOK is None or p["hook"] == HOOK)}   # a family of rotating launchers sharing one launch selector
else: pools = {pid: p for pid, p in d["pools"].items() if p["to"] == LAUNCHER and (HOOK is None or p["hook"] == HOOK)}
pids = sorted(pools, key=lambda k: pools[k]["bn"]); print(f"{len(pids)} pools of 0x{LAUNCHER}", flush=True)
ev = {}
STEP = 8 if "robinhood" in RPC else 4
TXSTEP = 40 if (TX_RPC or "robinhood" in RPC) else 10
for i in range(0, len(pids), STEP):
    chunk = pids[i:i+STEP]
    body = [{"jsonrpc": "2.0", "id": j, "method": "eth_getLogs", "params": [{"address": PM, "topics": [[T_SWAP, T_ML], pid], "fromBlock": hex(pools[pid]["bn"]), "toBlock": hex(pools[pid]["bn"] + HORIZON)}]} for j, pid in enumerate(chunk)]
    r = post(body); r = r if isinstance(r, list) else [r]
    for x in r:
        if "result" not in x: print("  err", str(x.get("error"))[:100], flush=True); continue
        pid = chunk[x["id"]]; sw = []; liq = []
        for l in x["result"]:
            dd = l["data"]; bn = int(l["blockNumber"], 16)
            if l["topics"][0] == T_SWAP: sw.append([bn, int(l["logIndex"], 16), s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), l["transactionHash"]])
            else: liq.append([bn, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2)), l["transactionHash"]])
        ev[pid] = {"swaps": sorted(sw), "liq": sorted(liq)}
    if i % 80 == 0: print(f"  events {i+len(chunk)}/{len(pids)}", flush=True)
hashes = list(dict.fromkeys(s[6] for e in ev.values() for s in e["swaps"][:60])); print(f"{len(hashes)} swap txs to look up", flush=True)
txs = {}
for i in range(0, len(hashes), TXSTEP):
    chunk = hashes[i:i+TXSTEP]; r = None
    for _ in range(5):
        r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [h]} for j, h in enumerate(chunk)], url=TX_RPC)
        if isinstance(r, list) and all("result" in x and x["result"] for x in r): break
        time.sleep(3)
    for x in (r if isinstance(r, list) else []):
        t = x.get("result")
        if t: txs[t["hash"]] = [t["from"][2:].lower(), (t.get("to") or "")[2:].lower(), int(t["nonce"], 16), int(t["value"], 16), t["input"][:10]]
    if (i // 40) % 25 == 0: print(f"  txs {i+len(chunk)}/{len(hashes)}", flush=True)
json.dump({"launcher": LAUNCHER, "pools": pools, "events": ev, "txs": txs}, open(OUT, "w")); print("done ->", OUT, flush=True)
