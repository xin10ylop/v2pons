"""Verify the claimed wind-down transactions by hash and the hub wallet's state now."""
import kc, json
H = {"pull": "0x501ab4dcc593f47c73813bdfe7daa9f47cf68e3277d98be450cd817d054d093d",
     "sweep_last_wallet": "0x9a33f2d4b668784b5e7de2a411fcf59729cd881bc839e13fb397171a5053326f",
     "hub_inflow_1305": "0xe4f1b38affb3fdc0e0ed87045f867f03e00191f339d0536a6d4b79e267d06b88",
     "bridge_test": "0x0bad72bd9db03b99a0563d8daac9914ee7d04a9df82c2fb9ef54c9e64d5541b3",
     "bridge_main": "0x9b57f4e6d10fa22ca39d066d5bf1113f94dfc938411459b3a34eefb6ac5247f3",
     "relay_fill_1": "0x8d18b0ee04940255815ec638c86e90570bb8dfd6fb3a360e677a62fa86b8ddcf",
     "relay_fill_2": "0xc04476ce4a9676852106a1e35ad37b2be0aaa9425a28af70a5d45cebb922f5d3",
     "fp_typo_pull": "0x501ab4dc593f47c73813bdfe7daa9f47cf68e3277d98be450cd817d054d093d"}
out = {}
for k, h in H.items():
    try: t = kc.R.call("eth_getTransactionByHash", [h])
    except Exception as e: t = None; print(k, "ERR", str(e)[:100]); continue
    if not t: print(k, "NOT FOUND"); continue
    r = kc.R.call("eth_getTransactionReceipt", [h]); b = int(t["blockNumber"], 16)
    tsb = int(kc.R.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
    print("%-18s block %d %s from %s to %s value %.6f nonce %d sel %s status %s logs %d" % (k, b, kc.ts(tsb), t["from"], t["to"], int(t["value"], 16) / 1e18, int(t["nonce"], 16), t["input"][:10], r["status"], len(r["logs"])))
    if k.startswith("relay_fill"):
        for l in r["logs"]: print("     log", l["address"], l["topics"][0][:10], len(l["data"]))
for a in ("0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d", "0x3fd5c7ca6a06b568b6ceccfea414a63a91acb2a7"):
    print(a, "now: balance %.8f nonce %d" % (int(kc.R.call("eth_getBalance", [a, "latest"]), 16) / 1e18, int(kc.R.call("eth_getTransactionCount", [a, "latest"]), 16)))
