"""the engine's wallet and v4 relay (public addresses, research/session_oct12/c1/common.py): ETH now, the wallet's nonce; the V3 path's costs
at the head's base fee: the relay deploy (~1.07M gas with the L1 part, RELAY_V3.md), a v3crowd trade's gas (s05: buy ~235k + sell ~152k).
Writes s11_balances.out (stdout)."""
from common import *
import rpc
WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
S = json.load(open(J("s00_probe.json"))); eth = S["eth_usd"]
b = rpc.batch("eth_getBalance", [[WALLET, "latest"], [RELAY, "latest"]]); n = int(rpc.call("eth_getTransactionCount", [WALLET, "latest"]), 16)
bf = int(rpc.call("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
w, r = int(b[0], 16) / 1e18, int(b[1], 16) / 1e18
print(f"WALLET {WALLET}: {w:.6f} ETH (${w * eth:.2f}), nonce {n}; v4 RELAY {RELAY}: {r:.6f} ETH (${r * eth:.2f}); base fee {bf / 1e9:.4f} gwei; ETH ${eth:,.2f}")
dep = 1_070_000 * bf / 1e18; trade = (235_000 + 152_000) * bf / 1e18
print(f"relay deploy ~1.07M gas: {dep:.7f} ETH (${dep * eth:.3f}); a v3crowd trade's gas ~387k: {trade:.7f} ETH (${trade * eth:.4f}); "
      f"135 trades a day: {135 * trade:.5f} ETH (${135 * trade * eth:.2f}) a day from the WALLET; the stake (0.002-0.004 ETH) from RELAY_V3")
print(rpc.STATS)
