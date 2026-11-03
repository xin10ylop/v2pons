#!/usr/bin/env python3
"""v3slot.py HOURS: who else buys in our seat in the V3 crowd's pools (0-20 blocks after its routers' first buy, 0.0005 ETH and up), and
what happened to them: the pool pulled (a Burn) within 100 blocks of their buy. Against the base: every pumped pool, pulled within 100
blocks of the routers' first buy. Our V3 relay is marked. Read-only, public RPC."""
import os, sys, json, collections
import hlib as H
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 48
url = H.CH["rh"]["rpc"]; V3PM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; V3F = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
V3R = {"0x7feb3ecbacbd0cc23ec46659d541636d58749a97", "0x80e49ed118b932d9538ec817ef8b29fbac31e080", "0xaf9d6fa019328d8cf8598d0d5be22cc6622b09f1", "0xfc7241d4356564e32b16e8e4838c648efceb8144"}
OURS = {"0x55a1b4ee149aedf71a8cb5b72b52d1fed463bb46": "OUR V3 relay"}
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex(); T_SW3 = "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()
T_BURN3 = "0x" + keccak(text="Burn(address,int24,int24,uint128,uint256,uint256)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
head = int(H.rpc(url, "eth_blockNumber", []), 16); lo = head - int(HOURS * 36000)
pc = []
for a in range(lo, head + 1, 20000):
    pc += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19999)), "address": V3F, "topics": [T_PC]}]) or []
tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in pc], size=50, workers=4, tries=8)
pools = [{"pool": "0x" + l["data"][2:][64 + 24:128], "bn": int(l["blockNumber"], 16), "launcher": t["from"].lower()} for l, t in zip(pc, tx)
         if t and (t.get("to") or "").lower() == V3PM and (len(t["input"]) - 2) // 2 == 836 and int(t["value"], 16) == 0 and "0x" + l["topics"][1][26:] == WETH]
print(f"last {HOURS:g} h: {len(pools)} V3 crowd launches", flush=True)
cache_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/crowd_tx.json")
tc = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
rows = []; base = []
for p in pools:
    hi = min(head, p["bn"] + 2000)
    sw = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(hi), "address": p["pool"], "topics": [T_SW3]}]) or []
    need = [s["transactionHash"] for s in sw if s["transactionHash"] not in tc]
    for h, x in zip(need, H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=8) if need else []):
        tc[h] = [x["from"].lower(), (x.get("to") or "").lower()] if x else [None, None]
    rf = min((int(s["blockNumber"], 16) for s in sw if tc.get(s["transactionHash"], [None, None])[1] in V3R and sg(s["data"][2:66]) > 0), default=None)
    if rf is None or rf - p["bn"] > 600: continue
    bu = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"] + 1), "toBlock": hex(hi), "address": p["pool"], "topics": [T_BURN3]}]) or []
    pull = min((int(b["blockNumber"], 16) for b in bu if int(b["data"][2:66], 16) > 0), default=None)
    base.append(pull is not None and pull - rf <= 100)
    for s in sw:
        b = int(s["blockNumber"], 16); f, to = tc.get(s["transactionHash"], [None, None])
        if rf <= b <= rf + 20 and sg(s["data"][2:66]) >= 5 * 10 ** 14 and to not in V3R and f != p["launcher"] and f is not None:
            rows.append({"who": OURS.get(to, (to or "")[:10]), "from": f[:10], "off": b - rf, "eth": round(sg(s["data"][2:66]) / 1e18, 4),
                         "pulled100": pull is not None and pull - b <= 100, "pull_after": (pull - b) if pull else None})
json.dump(tc, open(cache_p, "w"))
print(f"pumped pools (the routers' first buy within 600 blocks): {len(base)}; pulled within 100 blocks of that first buy: {sum(base)} ({sum(base) / max(1, len(base)):.0%})")
ours = [r for r in rows if r["who"].startswith("OUR")]; others = [r for r in rows if not r["who"].startswith("OUR")]
for name, rs in (("OURS", ours), ("everyone else", others)):
    print(f"  {name:14s} early buys {len(rs):3d}  pool pulled within 100 blocks of their buy: {sum(r['pulled100'] for r in rs)}")
print("every early outside buy (who, sender, blocks after the routers' first buy, ETH, pulled within 100, pull after the buy):")
for r in sorted(rows, key=lambda r: (not r["who"].startswith("OUR"), r["off"])):
    print(f"   {r['who']:12s} {r['from']}  +{r['off']:2d}  {r['eth']:.4f}  pulled100 {str(r['pulled100']):5s} pull +{r['pull_after']}")
