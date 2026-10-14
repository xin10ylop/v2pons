"""The quote token HOOD (0x32ac8c..): its vault, mints/burns in 8 days, its v3 pools (USDG/HOOD 0x1c1f6e28 seen in the 740-B launches' dev buy),
balances, slot0 and the HOOD price in USDG/ETH; the HOOD held by the PoolManager and the hook. Prints s02b_quote.out; writes s02b_quote.json."""
from common import *
import rpc, collections
from eth_abi import decode
meta = json.load(open(J("s01_meta.json"))); head = meta["head"]
def ec(to, data, blk="latest"):
    try: return rpc.call("eth_call", [{"to": to, "data": data}, blk])
    except Exception as e: return "ERR " + str(e)[:100]
def bal(tok, a): r = ec(tok, "0x70a08231" + "0" * 24 + a[2:]); return int(r, 16) if r.startswith("0x") else r
v = ec(QUOTE, "0xfbfa77cf"); vault = "0x" + v[-40:]
vc = rpc.call("eth_getCode", [vault, "latest"])
print(f"HOOD vault() = {vault} code {len(vc) // 2 - 1} B; impl slot {rpc.call('eth_getStorageAt', [vault, '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc', 'latest'])}")
for nm, s in (("name()", "06fdde03"), ("symbol()", "95d89b41"), ("owner()", "8da5cb5b"), ("asset()", "38d52e0f"), ("token()", "fc0c546a"), ("totalAssets()", "01e1d114")):
    print(f"   vault {nm:14s} {ec(vault, '0x' + s)[:200]}")
print(f"HOOD totalSupply {int(ec(QUOTE, '0x18160ddd'), 16) / 1e18:.4f}")
# mints and burns (Transfer from/to 0) over 8 days
mints = jl(C("s02b_mint_cache.jsonl"))
if not mints:
    with open(C("s02b_mint_cache.jsonl"), "w") as f:
        for a in range(meta["start8"], head + 1, 1_000_000):
            b = min(a + 999_999, head)
            for flt in ({"address": QUOTE, "topics": [T_TRANSFER, topic_addr(Z)]}, {"address": QUOTE, "topics": [T_TRANSFER, None, topic_addr(Z)]}):
                for l in rpc.logs(flt, a, b): f.write(json.dumps(l) + "\n"); mints.append(l)
mi = [l for l in mints if int(l["topics"][1], 16) == 0]; bu = [l for l in mints if int(l["topics"][2], 16) == 0]
print(f"8 d: {len(mi)} mints {sum(int(l['data'], 16) for l in mi) / 1e18:.2f} HOOD to {collections.Counter('0x' + l['topics'][2][-40:] for l in mi).most_common(4)}; "
      f"{len(bu)} burns {sum(int(l['data'], 16) for l in bu) / 1e18:.2f} HOOD")
# v3 pools of HOOD: PoolCreated on the factory of 0x1c1f6e28
P3 = "0x1c1f6e283a72a68c15c816324363c794151cf913"; PWU = "0x52e65b17fb6e5ba00ed806f37afcd2daa50271ca"
out = {}
for p in (P3, PWU):
    t0 = "0x" + ec(p, "0x0dfe1681")[-40:]; t1 = "0x" + ec(p, "0xd21220a7")[-40:]; fee = int(ec(p, "0xddca3f43"), 16); fac = "0x" + ec(p, "0xc45a0155")[-40:]
    s0 = ec(p, "0x3850c7bd"); sp = W(s0, 0); L = int(ec(p, "0x1a686502"), 16)
    b0 = bal(t0, p); b1 = bal(t1, p)
    print(f"v3 pool {p} factory {fac} token0 {t0} token1 {t1} fee {fee} liquidity {L} sqrtP {sp} tick {sgn(W(s0, 1))}; balances {b0} / {b1}")
    out[p] = {"t0": t0, "t1": t1, "fee": fee, "sqrtP": sp, "L": L, "b0": b0, "b1": b1, "factory": fac}
# HOOD price: pool P3 token0/token1 order
p = out[P3]; x = (p["sqrtP"] / 2 ** 96) ** 2      # token1 per token0 in raw units
if p["t0"] == QUOTE: usdg_per_hood = x * 1e18 / 1e6
else: usdg_per_hood = (1 / x) * 1e18 / 1e6
q = out[PWU]; y = (q["sqrtP"] / 2 ** 96) ** 2
usdg_per_eth = y * 1e18 / 1e6 if q["t0"] == WETH else (1 / y) * 1e18 / 1e6
print(f"HOOD price {usdg_per_hood:.2f} USDG; ETH {usdg_per_eth:.1f} USDG; HOOD = {usdg_per_hood / usdg_per_eth:.5f} ETH")
hb = out[P3]["b0"] if out[P3]["t0"] == QUOTE else out[P3]["b1"]; ub = out[P3]["b1"] if out[P3]["t0"] == QUOTE else out[P3]["b0"]
print(f"USDG/HOOD pool depth: {hb / 1e18:.2f} HOOD + {ub / 1e6:.0f} USDG (~{(hb / 1e18 * usdg_per_hood + ub / 1e6) / usdg_per_eth:.1f} ETH total)")
# other HOOD v3 pools on the same factory: PoolCreated with HOOD as token0 or token1
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
pcs = []
for flt in ({"address": out[P3]["factory"], "topics": [T_PC, topic_addr(QUOTE)]}, {"address": out[P3]["factory"], "topics": [T_PC, None, topic_addr(QUOTE)]}):
    pcs += rpc.logs(flt, max(1, head - 9_000_000), head)
for l in pcs:
    pa = "0x" + l["data"][-40:]
    print(f"   HOOD v3 pool {pa} created block {int(l['blockNumber'], 16)} t0 {l['topics'][1][-40:][:10]} t1 {l['topics'][2][-40:][:10]} fee {int(l['topics'][3], 16)} "
          f"HOOD bal {bal(QUOTE, pa) / 1e18:.3f}")
print(f"HOOD held by the PoolManager {bal(QUOTE, PM) / 1e18:.3f}; by the hook {bal(QUOTE, '0x4eb1976978756bd56802d8162f2271844924e0cc') / 1e18:.3f}; by the locker 0xef785ad4 {bal(QUOTE, '0xef785ad4eea3cffa6c66f77eb454a61d544be4b6') / 1e18:.3f}")
json.dump({"pools": out, "usdg_per_hood": usdg_per_hood, "usdg_per_eth": usdg_per_eth, "hood_eth": usdg_per_hood / usdg_per_eth, "vault": vault}, open(J("s02b_quote.json"), "w"))
print(rpc.STATS)
