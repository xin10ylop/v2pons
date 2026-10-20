"""connect once to the Arbitrum sequencer feed, read one frame, close"""
import asyncio, json, sys, time
async def main():
    import websockets
    url = "wss://arb1-feed.arbitrum.io/feed"
    t0 = time.time()
    try:
        async with websockets.connect(url, open_timeout=15, max_size=None, ping_interval=None, compression="deflate") as ws:
            print("handshake OK in %.2fs" % (time.time()-t0))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            print("frame bytes:", len(raw) if isinstance(raw,(bytes,str)) else type(raw))
            try:
                f = json.loads(raw); msgs = f.get("messages", [])
                print("messages in frame:", len(msgs))
                if msgs:
                    m = msgs[0]; inner = (m.get("message") or {}).get("message") or {}; hdr = inner.get("header") or {}
                    print("seq:", m.get("sequenceNumber"), "kind:", hdr.get("kind"), "ts:", hdr.get("timestamp"), "has l2Msg:", bool(inner.get("l2Msg")))
                    print("top keys:", list(f.keys()))
            except Exception as e:
                print("frame not JSON head:", (raw[:120] if isinstance(raw,(bytes,bytearray)) else str(raw)[:120]))
    except Exception as e:
        print("FEED ERROR:", type(e).__name__, str(e)[:200])
        code = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "status_code", None)
        print("status_code:", code)
asyncio.run(main())
