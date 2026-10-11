"""The 16 post-census C-1 pools (v16): their Swap/ModifyLiquidity logs, the bot's first buy (first swap whose tx goes to 0xd6d35b56; txs
fetched in launch order until found), the follow replay T+2 / hold 60 with the same math as sim.py, and the pull against T."""
import rpc, sys
from sim import *
from eth_utils import keccak
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
F = json.load(open(os.path.join(V, "fresh.json"))); head = int(rpc.call("eth_blockNumber", []), 16)
Q = int(0.0058e18); res = []
for x in F["c1"]:
    ls = rpc.call("eth_getLogs", [{"fromBlock": hex(x["bn"]), "toBlock": hex(min(head, x["bn"] + 3000)), "address": PM, "topics": [[T_SWAP, T_ML], x["pid"]]}])
    ls.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    ev = []
    for l in ls:
        bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); d = l["data"]
        if l["topics"][0] == T_SWAP:
            a0, a1 = sgn(W(d, 0)), sgn(W(d, 1))   # int128 sign-extended in the word
            ev.append(["s", bn, 0, li, x["pid"], "0x" + l["topics"][2][-40:], a0, a1, W(d, 2), W(d, 3), sgn(W(d, 4)), W(d, 5), l["transactionHash"]])
        else:
            ev.append(["m", bn, 0, li, x["pid"], "0x" + l["topics"][2][-40:], sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), d[2 + 64*3: 2 + 64*4], l["transactionHash"]])
    r = {"quote_side": 0, "dex": "v4", "launch_block": x["bn"], "fee": 100, "tick0": x["tick"], "sqrt_p0": x["sqrt"], "pool": x["pid"], "launch_ts": 0}
    P = Pool(r, {"kind": "v4", "ev": ev})
    trig = None; i = 0; buys = [s for s in P.sw if s[3]]
    while trig is None and i < len(buys) and i < 200:
        chunk = buys[i:i + 20]; i += 20
        txs = rpc.batch("eth_getTransactionByHash", [[s[8]] for s in chunk])
        for s, t in zip(chunk, txs):
            if t and (t.get("to") or "").lower() == BOT: trig = s; break
    o = {"pid": x["pid"], "token": x["token"], "lb": x["bn"], "age": head - x["bn"], "n_swaps": len(P.sw), "pull": P.first_pull, "trig": trig[0] if trig else None}
    if trig:
        a = trig[0] + 2; b = a + 60
        if b <= head:
            rr = P.replay(a, b, Q); o["ret"] = -1.0 if rr["pulled_le"] else rr["ret"]; o["pulled"] = rr["pulled_le"]
    res.append(o)
    print(f"{x['pid'][:12]} launch {x['bn']} age {o['age']} swaps {o['n_swaps']} bot trigger +{(o['trig'] - x['bn']) if o['trig'] else None} pull +{(P.first_pull - x['bn']) if P.first_pull else None}"
          f" (trig+{(P.first_pull - o['trig']) if (P.first_pull and o['trig']) else None}) trade T+2/H60 {o.get('ret')}")
rs = [o["ret"] for o in res if "ret" in o]
print(f"fresh: {len(res)} launches, {sum(1 for o in res if o['trig'])} triggered, traded {len(rs)}: mean {sum(rs)/len(rs):+.4f} med {pct(rs,0.5):+.4f} win {sum(1 for v in rs if v > 0)}/{len(rs)} lost {sum(1 for v in rs if v == -1)}")
json.dump(res, open(os.path.join(V, "fresh_replay.json"), "w")); print(rpc.STATS)
