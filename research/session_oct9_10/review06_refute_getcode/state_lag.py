"""feed head at send minus the block a state read at 'latest' runs on (ArbSys.arbBlockNumber via eth_call), and minus eth_getBlockByNumber('latest')"""
import asyncio, json, time, threading, urllib.request, collections, websockets, sys
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
seq = [0]
def rpc(m, p):
    r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=3))
    return r.get("result"), r.get("error")
out = collections.defaultdict(list)
def sampler():
    while True:
        if seq[0]:
            for kind in ("call", "block"):
                s0 = seq[0]
                try:
                    if kind == "call":
                        r, e = rpc("eth_call", [{"to": "0x0000000000000000000000000000000000000064", "data": "0xa3b1b31d"}, "latest"]); b = int(r, 16)
                    else:
                        r, e = rpc("eth_getBlockByNumber", ["latest", False]); b = int(r["number"], 16)
                    out[kind].append(s0 - b)
                except Exception as ex:
                    out[kind + "_err"].append(str(ex)[:60])
        time.sleep(0.5)
async def feed():
    async with websockets.connect("wss://feed.mainnet.chain.robinhood.com", max_size=None, compression="deflate") as ws:
        t0 = time.time()
        while time.time() - t0 < float(sys.argv[1]):
            f = json.loads(await ws.recv())
            for m in f.get("messages", []):
                seq[0] = max(seq[0], m["sequenceNumber"])
threading.Thread(target=sampler, daemon=True).start()
asyncio.run(feed())
for k, v in out.items():
    print(k, len(v), sorted(collections.Counter(v).items()) if not k.endswith("err") else v[:3])
