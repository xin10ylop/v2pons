"""Every v3crowd launch from Oct 10 00:00 UTC to the head: the factory's PoolCreated (fee 100, WETH on one side) -> the creating tx -> those that
are the engine's v3crowd shape (to the V3 PositionManager, multicall ac9650d8, 836 bytes, value 0), decoded by v3dec (pool by CREATE2, checked
against PoolCreated). WETH-token1 launches are kept (flag qs 1: the engine skips them, but their tokens are part of the line). Also: whether the
launch wallet deployed the token itself (CREATE address of one of its earlier nonces), and a completeness check from the other side: every NPM
Mint whose lower tick is -887272 (topic) on a fee-100 WETH pool, and whether its pool was created in the same tx (a pre-created pool would
mean a launch the PoolCreated scan misses and a price the engine's copy gets wrong). Writes s01_launches.json, s01_launches.out."""
from common import *
import rpc, collections, rlp
from v3dec import decode_launch_v3
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
def ts(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
lo, hi = head - int((th - START_TS) * 9.7 * 1.3), head
while lo < hi:
    m = (lo + hi) // 2
    if ts(m) < START_TS: lo = m + 1
    else: hi = m
start = lo
print(f"head {head} {utc(th)}; start {start} {utc(ts(start))}; {(head - start) / (th - START_TS):.2f} blocks/s")
pc = []
for a in range(start, head + 1, 200000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 199999, head))
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"PoolCreated {len(pc)}; fee 100 with WETH {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
shapes = collections.Counter(); out = []
def create_addr(a, n): return "0x" + keccak(rlp.encode([bytes.fromhex(a[2:]), n]))[12:].hex()
for l, t in zip(cand, txs):
    to = (t.get("to") or "").lower(); n = (len(t["input"]) - 2) // 2; v = int(t["value"], 16)
    if not (to == NPM and t["input"][:10] == "0xac9650d8" and n == 836 and v == 0):
        shapes[(to[:10], t["input"][2:10], n)] += 1; continue
    d = decode_launch_v3(bytes.fromhex(t["input"][2:])); pool = "0x" + l["data"][-40:]
    if d is None or "0x" + d["pool"] != pool: print("undecoded/mismatch", l["transactionHash"]); continue
    frm = t["from"].lower(); nonce = int(t["nonce"], 16); tok = "0x" + d["token"]
    dep = [k for k in range(nonce) if create_addr(frm, k) == tok]
    out.append({"pool": pool, "token": tok, "qs": d["qs"], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": frm, "nonce": nonce,
                "ti": int(t["transactionIndex"], 16), "sqrt_p": d["sqrt_p"], "lo": d["lo"], "hi": d["hi"], "liq": d["liq"], "amount0": d["amount0"], "amount1": d["amount1"],
                "recipient": "0x" + d["recipient"], "deployed_by_launcher_nonce": dep[0] if dep else None, "gas": int(t["gas"], 16), "gp": int(t.get("gasPrice") or "0x0", 16)})
bl = sorted(set(x["lb"] for x in out)); blk = {}
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): blk[b] = int(r["timestamp"], 16)
for x in out: x["ts"] = blk[x["lb"]]
print(f"v3crowd-shaped launches {len(out)} (WETH token0 {sum(x['qs'] == 0 for x in out)}, token1 {sum(x['qs'] == 1 for x in out)})")
print(f"  per UTC day: {sorted(collections.Counter(time.strftime('%m-%d', time.gmtime(x['ts'])) for x in out).items())}")
print(f"  launch wallets distinct {len(set(x['from'] for x in out))}; launch nonce {sorted(collections.Counter(x['nonce'] for x in out).items())}")
print(f"  token deployed by the launch wallet at nonce: {sorted(collections.Counter(x['deployed_by_launcher_nonce'] for x in out).items(), key=str)}")
print(f"  recipient == launch wallet: {collections.Counter(x['recipient'] == x['from'] for x in out)}")
print("other fee-100 WETH pool creators:", shapes.most_common(10))
# the other side: NPM mints from tick -887272 on fee-100 WETH pools
LOW = "0x" + word(-887272)
mints = []
for a in range(start, head + 1, 200000):
    mints += rpc.logs({"topics": [T_MI, "0x" + word(NPM), LOW]}, a, min(a + 199999, head))
fee100weth = {"0x" + l["data"][-40:] for l in cand}
mm = [m for m in mints if m["address"].lower() in fee100weth]
created_in = {("0x" + l["data"][-40:]): l["transactionHash"] for l in cand}
ours = {x["pool"] for x in out}
not_same_tx = [m for m in mm if created_in.get(m["address"].lower()) != m["transactionHash"]]
print(f"NPM mints from tick -887272: {len(mints)}; on fee-100 WETH pools created in the window {len(mm)}; on v3crowd pools {sum(m['address'].lower() in ours for m in mm)}; "
      f"mint tx != the pool's creating tx: {len(not_same_tx)} (on v3crowd pools {sum(m['address'].lower() in ours for m in not_same_tx)})")
# WETH-token1 mints start from a negative upper bound instead; also mints whose upper tick is 887272 (the mirrored range)
HIGH = "0x" + word(887272)
mints1 = []
for a in range(start, head + 1, 200000):
    mints1 += rpc.logs({"topics": [T_MI, "0x" + word(NPM), None, HIGH]}, a, min(a + 199999, head))
mm1 = [m for m in mints1 if m["address"].lower() in fee100weth]
print(f"NPM mints up to tick 887272 on fee-100 WETH pools: {len(mm1)}; mint tx != creating tx: {sum(created_in.get(m['address'].lower()) != m['transactionHash'] for m in mm1)}")
json.dump({"head": head, "head_ts": th, "start": start, "start_ts": START_TS, "launches": out}, open(J("s01_launches.json"), "w"))
print(rpc.STATS)
