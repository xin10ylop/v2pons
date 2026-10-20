import asyncio, json, base64, time, sys, collections
import websockets
OUT = sys.argv[1]; DUR = float(sys.argv[2])
async def main():
    t0 = time.time(); n = 0
    async with websockets.connect("wss://feed.mainnet.chain.robinhood.com", open_timeout=10, max_size=None, compression="deflate") as ws:
        with open(OUT, "w") as f:
            while time.time() - t0 < DUR:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                f.write((raw if isinstance(raw, str) else raw.decode()) + "\n"); n += 1
    print("frames", n)
asyncio.run(main())
