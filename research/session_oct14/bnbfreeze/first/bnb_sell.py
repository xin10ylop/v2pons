import json, time, urllib.request, urllib.error
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
URLS = ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com", "https://bsc-dataseed1.defibit.io"]
def rpc(m, p):
    last = None
    for U in URLS:
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r: return r["result"]
            last = r.get("error")
            if m == "eth_call": return {"error": last}
        except Exception as e: last = str(e)[:80]
    return {"error": last}
W = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
# the wallet's 5 transactions: find them in the blocks around the halt via the sell hash we know
h = "0x5623acf8b420470adb22f12bdbc0d2889f0dc233bb213d10a2eab2f42c5de30b"
t = rpc("eth_getTransactionByHash", [h]); r = rpc("eth_getTransactionReceipt", [h])
print("sell: to", t["to"], "nonce", int(t["nonce"], 16), "block", int(r["blockNumber"], 16), "status", r["status"], "gas used", int(r["gasUsed"], 16), "of", int(t["gas"], 16), "price", int(t["gasPrice"], 16) / 1e9, "gwei")
inp = t["input"]; w = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
print("selector", inp[:10], "amountIn", int(w[0], 16), "minOut BNB", int(w[1], 16) / 1e18, "to", "0x" + w[3][-40:], "deadline", int(w[4], 16), "path", ["0x" + x[-40:] for x in w[6:]])
tok = "0x" + w[6][-40:]; b = int(r["blockNumber"], 16)
blk = rpc("eth_getBlockByNumber", [hex(b), False]); print("block time", int(blk["timestamp"], 16), "deadline minus block time", int(w[4], 16) - int(blk["timestamp"], 16))
call = {"from": W, "to": t["to"], "data": inp, "gas": t["gas"]}
print("replay at block-1:", rpc("eth_call", [call, hex(b - 1)]))
print("replay now:", rpc("eth_call", [call, "latest"]))
bal = rpc("eth_call", [{"to": tok, "data": "0x70a08231" + W[2:].rjust(64, "0")}, "latest"]); print("token", tok, "balance now", int(bal, 16) if isinstance(bal, str) else bal)
alw = rpc("eth_call", [{"to": tok, "data": "0xdd62ed3e" + W[2:].rjust(64, "0") + t["to"][2:].rjust(64, "0")}, "latest"]); print("allowance to router", int(alw, 16) if isinstance(alw, str) else alw)
code = rpc("eth_getCode", [tok, "latest"]); print("token code bytes", (len(code) - 2) // 2 if isinstance(code, str) else code)
# a plain transfer of the balance to the pair, simulated, and a sell of 1% of it
if isinstance(bal, str) and int(bal, 16):
    amt = int(bal, 16)
    for frac in (1.0, 0.5, 0.01):
        a = int(amt * frac); d = inp[:10] + hex(a)[2:].rjust(64, "0") + "0" * 64 + inp[10 + 128:]
        print("sell", frac, "of the balance, minOut 0, now:", rpc("eth_call", [{"from": W, "to": t["to"], "data": d, "gas": hex(1500000)}, "latest"]))
json.dump({"tx": t, "receipt": r}, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb_sell1.json", "w"))
print("---- with a fresh deadline")
dl = hex(int(time.time()) + 600)[2:].rjust(64, "0")
amt = int(bal, 16)
pair = None
for frac in (1.0, 0.5, 0.01, 0.0001):
    a = int(amt * frac); d = inp[:10] + hex(a)[2:].rjust(64, "0") + "0" * 64 + inp[10 + 128: 10 + 256] + dl + inp[10 + 320:]
    print("sell", frac, "minOut 0:", rpc("eth_call", [{"from": W, "to": t["to"], "data": d, "gas": hex(1500000)}, "latest"]))
# plain token transfers from the wallet: to a fresh address, and to the pair
fac = rpc("eth_call", [{"to": t["to"], "data": "0xc45a0155"}, "latest"]); fac = "0x" + fac[-40:]
pr = rpc("eth_call", [{"to": fac, "data": "0xe6a43905" + tok[2:].rjust(64, "0") + "bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c".rjust(64, "0")}, "latest"]); pair = "0x" + pr[-40:]
print("pair", pair)
for dest in ("0x000000000000000000000000000000000000dEaD", pair):
    print("transfer 1% to", dest[:12], ":", rpc("eth_call", [{"from": W, "to": tok, "data": "0xa9059cbb" + dest[2:].lower().rjust(64, "0") + hex(amt // 100)[2:].rjust(64, "0"), "gas": hex(300000)}, "latest"]))
print("transferFrom by the router, 1%:", rpc("eth_call", [{"from": t["to"], "to": tok, "data": "0x23b872dd" + W[2:].rjust(64, "0") + pair[2:].rjust(64, "0") + hex(amt // 100)[2:].rjust(64, "0"), "gas": hex(300000)}, "latest"]))
res = rpc("eth_call", [{"to": pair, "data": "0x0902f1ac"}, "latest"]); print("reserves", int(res[2:66], 16), int(res[66:130], 16))
print("token0", rpc("eth_call", [{"to": pair, "data": "0x0dfe1681"}, "latest"])[-40:])
for sel, name in (("0x8da5cb5b", "owner"), ("0x313ce567", "decimals"), ("0x18160ddd", "totalSupply")):
    print(name, rpc("eth_call", [{"to": tok, "data": sel}, "latest"]))
