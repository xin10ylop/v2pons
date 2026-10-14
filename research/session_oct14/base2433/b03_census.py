"""Base: every Uniswap v4 launch of the 2.433 operator's shape in the last H hours (fee 5000, tick spacing 100, the hook of its 09:42 UTC
Oct 14 launch b02, or any launch sent to its launcher 0xd93bef10), each pool's swaps to +600 split into the operator's 31 buyer wallets and
outsiders, and the liquidity removals (logs from Tenderly's public Base gateway) (ModifyLiquidity with negative delta: a pull). Public endpoint, read-only.
usage: python3 b03_census.py [hours, default 24]"""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.3   # keeps old logs (publicnode: ~20 min only)
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
buyers = {a.lower() for a, n, b in json.load(open(SRC + "c16_rh_wallets_xchain.json"))["buyers_bsc"]}
H = float(sys.argv[1]) if len(sys.argv) > 1 else 24
head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16); start = head - int(H * 1800)
sg = lambda x: x - (1 << 256) if x >= (1 << 255) else x
def logs(flt, a, b, step=500):
    out = []
    for s in range(a, b + 1, step):
        out += xr.batch("base_t", "eth_getLogs", [[dict(flt, fromBlock=hex(s), toBlock=hex(min(s + step - 1, b)))]], n=1)[0] or []
    return out
ini = logs({"address": PM, "topics": [T_INIT]}, start, head)
cand = [l for l in ini if int(l["data"][2:66], 16) == 5000 and int(l["data"][66:130], 16) == 100]
print(f"base head {head} ({H:g} h = blocks {start}..{head}): {len(ini)} v4 Initialize, fee 5000/ts 100: {len(cand)}")
txs = xr.batch("base", "eth_getTransactionByHash", [[l["transactionHash"]] for l in cand], n=20) if cand else []
shapes = collections.Counter()
rows = []
for l, t in zip(cand, txs):
    d = l["data"]; hook = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]; sp = int(d[2 + 64 * 3: 2 + 64 * 4], 16)
    c0, c1 = "0x" + l["topics"][2][-40:], "0x" + l["topics"][3][-40:]
    shapes[((t.get("to") or "")[:10], t["input"][:10], (len(t["input"]) - 2) // 2, hook[:10], c0 == "0x" + "0" * 40)] += 1
    rows.append((int(l["blockNumber"], 16), l["topics"][1], c0, c1, hook, sp, t))
print("launch shapes (to, selector, bytes, hook, ETH-quoted):", shapes.most_common(12))
ours = [r for r in rows if r[6]["from"].lower() in buyers or (r[6].get("to") or "").lower().startswith("0xd93bef10") or r[3].endswith("a777")]
print(f"the operator's candidates (launcher 0xd93bef10, a buyer wallet launching, or a token ending a777): {len(ours)}")
for blk, pid, c0, c1, hook, sp, t in ours:
    tok = c1 if c0 == "0x" + "0" * 40 else c0
    code = xr.batch("base", "eth_getCode", [[tok, "latest"]], n=1)[0]
    ch = keccak(bytes.fromhex(code[2:])).hex()[:12] if len(code) > 2 else "-"
    end = min(blk + 600, head)
    sw = logs({"address": PM, "topics": [T_SWAP, pid]}, blk, end)
    ml = logs({"address": PM, "topics": [T_ML, pid]}, blk, head, step=500) if head - blk < 30000 else []
    stx = xr.batch("base", "eth_getTransactionByHash", [[x["transactionHash"]] for x in sw], n=20) if sw else []
    b_in = b_out = o_in = o_out = 0.0; first_out = None; ob = []
    for x, tx in zip(sw, stx):
        a0 = sg(int(x["data"][2:66], 16)) / 1e18; f = (tx or {}).get("from", "").lower(); off = int(x["blockNumber"], 16) - blk
        if f in buyers:
            if a0 < 0: b_in -= a0
            else: b_out += a0
        else:
            if a0 < 0: o_in -= a0; ob.append((off, round(-a0, 4), f[:10]))
            else: o_out += a0
    pulls = [(int(m["blockNumber"], 16) - blk, sg(int(m["data"][2 + 64 * 2: 2 + 64 * 3], 16))) for m in ml if sg(int(m["data"][2 + 64 * 2: 2 + 64 * 3], 16)) < 0]
    adds = [int(m["blockNumber"], 16) - blk for m in ml if sg(int(m["data"][2 + 64 * 2: 2 + 64 * 3], 16)) > 0]
    print(f"  L {blk} {time.strftime('%m-%d %H:%M', time.gmtime(int(xr.batch('base','eth_getBlockByNumber',[[hex(blk), False]],n=1)[0]['timestamp'],16)))} "
          f"from {t['from'][:10]} to {(t.get('to') or '')[:10]} {t['input'][:10]} {(len(t['input'])-2)//2} B val {int(t['value'],16)/1e18:.4f} "
          f"token ..{tok[-6:]} code {ch} hook {hook[:10]} sqrtP {sp}")
    print(f"      swaps to +600: {len(sw)}; buyers in {b_in:.3f} out {b_out:.3f}; outsiders in {o_in:.3f} out {o_out:.3f} first outsider buys {ob[:4]}; "
          f"liquidity adds at {adds[:3]} pulls at {[p[0] for p in pulls][:3]}")
