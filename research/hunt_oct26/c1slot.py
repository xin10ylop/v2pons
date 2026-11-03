#!/usr/bin/env python3
"""c1slot.py HOURS: who else buys in our seat in C-1's pools (0-20 blocks after its router's first buy, 0.0005 ETH and up) and what
happened to them: the pool pulled within 100 blocks of their buy, their tokens burned, their route (the transaction's target: the public
Universal Router, an aggregator, their own contract) and size. Our relays (old and new) are marked. Read-only, public RPC."""
import os, sys, json, collections
import hlib as H
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 48
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]; R = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
OURS = {"0x2abb5653352f6b2f3b4f4261877cd02d9e05a957": "OUR relay 1", "0x86698926a66f5a160fd145c27d5adac4f5063b9c": "OUR relay 2"}
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T_TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; DEAD = "0x" + "0" * 24 + "000000000000000000000000000000000000dead"
T_INIT4 = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
head = int(H.rpc(url, "eth_blockNumber", []), 16); lo = head - int(HOURS * 36000)
il = []
for a in range(lo, head + 1, 20000):
    il += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19999)), "address": PM, "topics": [T_INIT4]}]) or []
il = [l for l in il if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:66], 16) == 100 and int(l["data"][66:130], 16) == 1 and int(l["data"][130:194], 16) == 0]
tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in il], size=50, workers=4, tries=8)
pools = [{"pid": l["topics"][1], "tok": "0x" + l["topics"][3][26:], "bn": int(l["blockNumber"], 16), "launcher": t["from"].lower()} for l, t in zip(il, tx)
         if t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 2276]
cache_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/c1_tx.json")
tc = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
rows = []
for p in pools:
    hi = min(head, p["bn"] + 4000)
    sw = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(hi), "address": PM, "topics": [T_SWAP4, p["pid"]]}]) or []
    need = [s["transactionHash"] for s in sw if s["transactionHash"] not in tc]
    for h, x in zip(need, H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=8) if need else []):
        tc[h] = [x["from"].lower(), (x.get("to") or "").lower()] if x else [None, None]
    rf = min((int(s["blockNumber"], 16) for s in sw if tc.get(s["transactionHash"], [None, None])[1] == R and -sg(s["data"][2:66]) > 0), default=None)
    if rf is None: continue
    early = [(s, tc.get(s["transactionHash"], [None, None])) for s in sw if rf <= int(s["blockNumber"], 16) <= rf + 20 and -sg(s["data"][2:66]) >= 5 * 10 ** 14]
    early = [(s, w) for s, w in early if w[1] != R and w[0] != p["launcher"]]
    if not early: continue
    ml = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"] + 1), "toBlock": hex(hi), "address": PM, "topics": [T_ML, p["pid"]]}]) or []
    pull = min((int(m["blockNumber"], 16) for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    burns = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(hi), "address": p["tok"], "topics": [T_TR, None, DEAD]}]) or []
    burned = {"0x" + b["topics"][1][26:] for b in burns}
    for s, (f, to) in early:
        b = int(s["blockNumber"], 16)
        rows.append({"who": OURS.get(to, (to or "")[:10]), "route": "UR (public)" if to == UR else ("OURS" if to in OURS else "own contract/other"), "from": f[:10], "off": b - rf,
                     "eth": round(-sg(s["data"][2:66]) / 1e18, 4), "pulled100": pull is not None and pull - b <= 100, "pull_after": (pull - b) if pull else None,
                     "burned": to in burned or f in burned})
json.dump(tc, open(cache_p, "w"))
print(f"last {HOURS:g} h: {len(pools)} C-1 pools; outside buys of 0.0005+ ETH 0-20 blocks after the router's first buy: {len(rows)}")
by = collections.defaultdict(list)
for r in rows: by[r["route"]].append(r)
for k, rs in by.items():
    print(f"  {k:20s} buys {len(rs):3d}  pool pulled within 100 blocks {sum(r['pulled100'] for r in rs):2d}  tokens burned {sum(r['burned'] for r in rs):2d}  size median {sorted(r['eth'] for r in rs)[len(rs) // 2]}")
print("every one (who, sender, blocks after the router's first buy, ETH, pulled within 100, pull after the buy, burned):")
for r in sorted(rows, key=lambda r: (r["route"] != "OURS", r["route"], -r["eth"])):
    print(f"   {r['who']:12s} {r['from']}  +{r['off']:2d}  {r['eth']:.4f}  pulled100 {str(r['pulled100']):5s} pull +{r['pull_after']}  burned {r['burned']}")
