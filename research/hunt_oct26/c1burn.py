#!/usr/bin/env python3
"""c1burn.py HOURS: who C-1 burns. C-1's router can take a holder's tokens (it approves itself on the holder's behalf and sends them to
0xdead, naming the holders: Nov 3 06:50, our relay and wallet). For every C-1 pool of the last HOURS hours: the outside buys (not through
its router), the buyer (the transaction's sender) and holder (who received the tokens), and the burns (transfers to 0xdead in transactions
to its router). Per buyer, in order: was it burned in its first C-1 pool of the window, or only after? How long after the buy did the burn
come? Read-only, public RPC."""
import os, sys, json, collections, statistics as st
import hlib as H
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 48
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]; R = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
T_TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; DEAD = "0x" + "0" * 24 + "000000000000000000000000000000000000dead"
T_INIT4 = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
head = int(H.rpc(url, "eth_blockNumber", []), 16); lo = head - int(HOURS * 36000)
il = []
for a in range(lo, head + 1, 20000):
    il += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19999)), "address": PM, "topics": [T_INIT4]}]) or []
il = [l for l in il if l["topics"][2] == "0x" + "0" * 64 and int(l["data"][2:66], 16) == 100 and int(l["data"][66:130], 16) == 1 and int(l["data"][130:194], 16) == 0]
tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in il], size=50, workers=4, tries=8)
pools = [{"pid": l["topics"][1], "tok": "0x" + l["topics"][3][26:], "bn": int(l["blockNumber"], 16), "launcher": t["from"].lower()} for l, t in zip(il, tx)
         if t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 2276]
print(f"last {HOURS:g} h: {len(pools)} C-1 pools", flush=True)
cache_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/c1_tx.json")
try:
    tc = json.load(open(cache_p))
except (OSError, ValueError):
    tc = {}
buys = []; burns = []
for p in pools:
    hi = min(head, p["bn"] + 6000)
    sw = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(hi), "address": PM, "topics": [T_SWAP4, p["pid"]]}]) or []
    need = [s["transactionHash"] for s in sw if s["transactionHash"] not in tc]
    for h, x in zip(need, H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=8) if need else []):
        tc[h] = [x["from"].lower(), (x.get("to") or "").lower()] if x else [None, None]
    for s in sw:
        f, to = tc.get(s["transactionHash"], [None, None])
        if -sg(s["data"][2:66]) > 10 ** 14 and to != R and f != p["launcher"] and f is not None:
            buys.append({"pool": p["pid"], "tok": p["tok"], "b": int(s["blockNumber"], 16), "from": f, "to": to, "h": s["transactionHash"]})
    bl = []
    for a in range(p["bn"], hi + 1, 2000):
        bl += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(hi, a + 1999)), "address": p["tok"], "topics": [T_TR, None, DEAD]}]) or []
    for x in bl:
        burns.append({"pool": p["pid"], "holder": "0x" + x["topics"][1][26:], "b": int(x["blockNumber"], 16), "h": x["transactionHash"]})
json.dump(tc, open(cache_p, "w"))
bt = {t["hash"]: t for t in (H.batch(url, [("eth_getTransactionByHash", [h]) for h in sorted({b["h"] for b in burns})], size=50, workers=4, tries=8) if burns else []) if t}
burns = [b for b in burns if (bt.get(b["h"], {}).get("to") or "").lower() == R]
named = collections.defaultdict(set)                                       # pool -> the addresses its burn transactions name
for b in burns:
    d = bt[b["h"]]["input"][10:]                                            # the words after the 4-byte selector
    for i in range(0, len(d) - 63, 64):
        w = d[i:i + 64]
        if w[:24] == "0" * 24 and w[24:] != "0" * 40:
            named[b["pool"]].add("0x" + w[24:])
burned_at = {(b["pool"], b["holder"]): b["b"] for b in burns}
print(f"outside buys: {len(buys)} by {len({x['from'] for x in buys})} buyers; burns by C-1's router: {len(burns)} in {len({b['pool'] for b in burns})} pools", flush=True)
by = collections.defaultdict(list)
for x in sorted(buys, key=lambda x: x["b"]):
    by[x["from"]].append(x)
first = []; later = []; delays = []
for w, xs in by.items():
    seen = []
    for x in xs:
        if x["pool"] in seen:
            continue
        hit = w in named.get(x["pool"], set()) or (x["to"] in named.get(x["pool"], set()) and x["to"] not in ("0x8876789976decbfcbbbe364623c63652db8c0904",))
        (first if not seen else later).append(hit)
        if hit:
            bb = [b["b"] for b in burns if b["pool"] == x["pool"]]
            delays.append(min(bb) - x["b"])
        seen.append(x["pool"])
print(f"a buyer's FIRST C-1 pool in the window: burned {sum(first)} of {len(first)} ({sum(first) / max(1, len(first)):.0%})")
print(f"its later C-1 pools: burned {sum(later)} of {len(later)} ({sum(later) / max(1, len(later)):.0%})")
if delays:
    ds = sorted(delays); print(f"the burn after the buy (blocks): median {st.median(ds)}, min {ds[0]}, p25 {ds[len(ds) // 4]}, p75 {ds[3 * len(ds) // 4]}, max {ds[-1]}")
rep = collections.Counter(); 
for w, xs in by.items():
    ps = []
    for x in xs:
        if x["pool"] not in ps: ps.append(x["pool"])
    hits = [w in named.get(p, set()) for p in ps]
    rep[(len(ps) > 1, hits[0] if hits else None)] += 1
print("buyers by (more than one pool, burned in the first):", dict(rep))
