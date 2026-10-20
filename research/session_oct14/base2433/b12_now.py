"""The 2.433 operator's state on Base now, and who the four wallets are that bought in the 10:30 and 10:35 pools without being among the
31 known buyers (b10_pools.out tags them OUTSIDER): (1) the launch wallet's +1 call to the bot contract (4977dff6: the per-launch funding of
the buyer fleet) decoded into its address list for the 09:42, 10:30 and 10:35 pools, and whether the four are in it; (2) nonces and
balances now of the 31 buyers, the collector, the launch wallets and the four; their nonces on BNB Chain, Ethereum and Robinhood;
(3) any new fee-5000/ts-100 Initialize after b09's head (52593544); (4) the launch wallets' transactions in each launch window (L..L+8)
and at the pull; (5) the gaps between launches. Read-only: publicnode for the state now, Tenderly for old blocks.
usage: python3 b12_now.py"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.25
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"; BOT = "0x987d5db84d105c1f49391af409cc34c6050fb1d0"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
pools = json.load(open(os.path.join(HERE, "b10_pools.json")))
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/c16_rh_wallets_xchain.json"
buyers = [a.lower() for a, n, b in json.load(open(SRC))["buyers_bsc"]]
COLLECT = "0x8f79d153630b327cc84487804f152972cce93cb4"
launch_wallets = {L: p["wallet"] for L, p in pools.items()}
four = sorted({r["from"] for p in pools.values() for r in p["rows"] if r.get("actor") == "OUTSIDER"})
print("the four non-listed wallets:", four)

# (1) the +1 funding call of each real pool: its address list
print("\n(1) the launch wallet's +1 call to the bot contract (4977dff6), decoded")
funded_all = set()
for L in ("52590807", "52592240", "52592379"):
    Lb = int(L); w = launch_wallets[L]
    B = xr.call("base_t", "eth_getBlockByNumber", [hex(Lb + 1), True])
    for t in B["transactions"]:
        if t["from"].lower() == w and (t.get("to") or "").lower() == BOT and t["input"][:10] == "0x4977dff6":
            inp = t["input"]; words = [inp[10 + 64 * k: 74 + 64 * k] for k in range((len(inp) - 10) // 64)]
            n = int(words[2], 16); addrs = ["0x" + x[24:] for x in words[3:3 + n]]
            amts = [int(x, 16) for x in words[3 + n + 1: 3 + n + 1 + n]] if len(words) >= 3 + 2 * n + 1 else []
            print(f"  pool {L}: tx {t['hash']} value {int(t['value'], 16) / 1e18:.4f} ETH, {n} addresses" + (f", amounts {min(amts) / 1e18:.4f}..{max(amts) / 1e18:.4f} ETH (sum {sum(amts) / 1e18:.4f})" if amts else ""))
            funded_all |= set(addrs)
            print(f"    in the 31-buyer list: {sum(a in buyers for a in addrs)}; the four present: {[a[:10] for a in four if a in addrs]}")
print(f"  funded addresses over the three pools: {len(funded_all)}; of them not among the 31 buyers: {sorted(a for a in funded_all if a not in buyers)}")

# (2) nonces and balances now
print("\n(2) state now (publicnode)")
addrs = buyers + [COLLECT] + list(launch_wallets.values()) + four
ns = [int(x, 16) for x in xr.batch("base", "eth_getTransactionCount", [[a, "latest"] for a in addrs], n=20)]
bs = [int(x, 16) for x in xr.batch("base", "eth_getBalance", [[a, "latest"] for a in addrs], n=20)]
head = int(xr.call("base", "eth_blockNumber", []), 16); hb = xr.call("base", "eth_getBlockByNumber", [hex(head), False])
print(f"  head {head} at {time.strftime('%H:%M:%S UTC', time.gmtime(int(hb['timestamp'], 16)))} (now {time.strftime('%H:%M:%S UTC', time.gmtime())})")
print(f"  31 buyers: nonce sum {sum(ns[:31])} (20,405 at 10:11), ETH {sum(bs[:31]) / 1e18:.4f} (0.0006 at 10:11)")
print(f"  collector {COLLECT[:10]}: nonce {ns[31]} (1 at 10:11), {bs[31] / 1e18:.4f} ETH (8.46 at 10:11)")
for i, (L, w) in enumerate(launch_wallets.items()):
    print(f"  launch wallet {w[:10]} (pool {L}): nonce {ns[32 + i]}, {bs[32 + i] / 1e18:.4f} ETH")
k = 32 + len(launch_wallets)
for i, a in enumerate(four):
    print(f"  four: {a}: nonce {ns[k + i]}, {bs[k + i] / 1e18:.4f} ETH")
for ch in ("bsc", "eth", "rh"):
    try:
        x = [int(v, 16) for v in xr.batch(ch, "eth_getTransactionCount", [[a, "latest"] for a in four], n=4)]
        print(f"  the four on {ch}: nonces {x}")
    except Exception as e:
        print(f"  the four on {ch}: unreadable ({str(e)[:80]})")

# (3) new launches since b09's head
print("\n(3) fee-5000/ts-100 Initialize after 52593544")
new = []
for s in range(52593545, head + 1, 400):
    for l in xr.call("base", "eth_getLogs", [{"address": PM, "topics": [T_INIT], "fromBlock": hex(s), "toBlock": hex(min(s + 399, head))}]) or []:
        d = l["data"]
        if int(d[2:66], 16) == 5000 and int(d[66:130], 16) == 100:
            new.append((int(l["blockNumber"], 16), l["transactionHash"], "0x" + l["topics"][3][-40:]))
print(f"  {len(new)} new: {new}" if new else f"  none up to {head}")

# (4) the launch wallets' transactions in each window and at the pull
print("\n(4) the launch wallet's transactions, L..L+8 and the pull block")
for L, p in pools.items():
    Lb = int(L); w = p["wallet"]; blocks = list(range(Lb, Lb + 9)) + ([Lb + p["pull"]["off"]] if p["pull"] else [])
    Bs = xr.batch("base_t", "eth_getBlockByNumber", [[hex(b), True] for b in blocks], n=5)
    print(f"  pool {L} wallet {w[:10]}:")
    for b, B in zip(blocks, Bs):
        for t in B["transactions"]:
            if t["from"].lower() == w:
                print(f"    +{b - Lb:<3} to {(t.get('to') or 'CREATE')[:10]} {t['input'][:10]} {(len(t['input']) - 2) // 2:>4} B value {int(t['value'], 16) / 1e18:.4f} ETH gas {int(t['gas'], 16)} prio {int(t.get('maxPriorityFeePerGas', '0x0'), 16) / 1e9:.4f} gwei")

# (5) the gaps
print("\n(5) launches and gaps")
Ls = sorted(int(L) for L in pools)
ts = [int(xr.call("base_t", "eth_getBlockByNumber", [hex(L), False])["timestamp"], 16) for L in Ls]
for i, (L, t) in enumerate(zip(Ls, ts)):
    print(f"  {time.strftime('%H:%M:%S', time.gmtime(t))} block {L}" + (f"  +{(t - ts[i - 1]) / 60:.1f} min" if i else ""))
print(f"  since the last launch: {(int(hb['timestamp'], 16) - ts[-1]) / 60:.1f} min")
print(f"\nrequests: {xr.STATS}")
