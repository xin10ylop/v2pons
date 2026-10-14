"""HyperEVM: mints to the admin's router copy 0x948f63b2 in 1,000-block windows (~16 min) every 2 h over the last 52 h (the RPC ignores
historical block numbers for state and caps logs at 1,000 blocks)."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx
rpcx.EP["hyper"] = "https://rpc.hyperliquid.xyz/evm"; rpcx.BT["hyper"] = 1.0; rpcx.PACE["hyper"] = 1.5
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
r = "0x948f63b29061be270486a390342dedd39d7deb5a"
h = int(rpcx.call("hyper", "eth_blockNumber", []), 16) - 5; out = []
print("router copy nonce now", int(rpcx.call("hyper", "eth_getTransactionCount", [r, "latest"]), 16))
for k in range(0, 27):
    b = h - int(k * 7200 / 0.984) - 999
    for i in range(6):
        try:
            x = rpcx.call("hyper", "eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(b + 999), "topics": [T, pad("0x" + "0" * 40), pad(r)]}]); break
        except Exception as e:
            x = None; time.sleep(5 * (i + 1))
    out.append({"hours_ago": 2 * k, "b": b, "mints": None if x is None else len(x)})
    print(2 * k, "h ago, block", b, "mints in 1,000 blocks:", None if x is None else len(x), flush=True)
json.dump(out, open("c22_hyper_sample.json", "w"))
