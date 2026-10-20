"""v3crowd launches: the V3 factory's PoolCreated (fee 100, WETH on one side) from block START to the head, kept when the creating tx is the
line's launch: value-0 multicall ac9650d8 of 836 bytes to the PositionManager 0x73991a25, decoded by W/v3dec.py (exactly
[createAndInitialize, mint, refundETH]). Writes r01_launches.json, r01_meta.json, and a census of the other fee-100 WETH launch shapes."""
from common import *
import rpc, collections
from v3dec import decode_launch_v3
START = int(sys.argv[1]) if len(sys.argv) > 1 else 78_700_000
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
pc = []; a = START; step = 400_000
while a <= head:
    b = min(a + step - 1, head); pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, b); a = b + 1
print(f"head {head} {utc(th)}; PoolCreated {len(pc)} since {START}")
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"fee 100 with WETH: {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
out = []; other = collections.Counter()
for l, t in zip(cand, txs):
    to = (t.get("to") or "").lower() if t else ""; n = (len(t["input"]) - 2) // 2 if t else 0; v = int(t["value"], 16) if t else -1
    key = (to[:10], t["input"][:10] if t else None, n, v > 0)
    d = decode_launch_v3(bytes.fromhex(t["input"][2:])) if t and to == NPM and n == 836 and v == 0 else None
    if not d: other[key] += 1; continue
    pool = "0x" + l["data"][-40:]
    if pool[2:] != d["pool"]: other[("pool-mismatch",) + key] += 1; continue
    out.append({"pool": pool, "token": "0x" + d["token"], "qs": d["qs"], "lb": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"],
                "from": t["from"].lower(), "nonce": int(t["nonce"], 16), "sqrt_p": d["sqrt_p"], "hi": d["hi"], "lo": d["lo"], "liq": d["liq"], "a1": d["amount1"], "a0": d["amount0"], "rcpt": "0x" + d["recipient"]})
bl = sorted(set(x["lb"] for x in out)); ts = {}
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): ts[b] = int(r["timestamp"], 16)
for x in out: x["ts"] = ts[x["lb"]]
out.sort(key=lambda x: (x["lb"], x["ti"]))
print(f"line launches {len(out)}; qs1 {sum(x['qs'] for x in out)}; first {utc(out[0]['ts'])} last {utc(out[-1]['ts'])}")
days = collections.Counter(time.strftime('%m-%d', time.gmtime(x['ts'])) for x in out); print("per day", sorted(days.items()))
print("launch wallets", len({x['from'] for x in out}), collections.Counter(x['from'] for x in out).most_common(5))
print("other fee-100 WETH shapes", other.most_common(12))
json.dump(out, open(J("r01_launches.json"), "w")); json.dump({"head": head, "head_ts": th, "start": START}, open(J("r01_meta.json"), "w"))
print("rpc", rpc.STATS)
