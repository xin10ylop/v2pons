"""Live probe (today, from this container, not the box): for transactions seen in the sequencer feed, how long until the public
RPC serves their receipt (what arm_launch waits on), in ms and in feed blocks. 60 s."""
import sys, json, time, asyncio, threading, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import os
os.environ.setdefault("LOG_PATH", "/dev/null")
import flip_engine as E
res = []; seq_now = {"s": 0}
def poll(h, seq, t0):
    while time.monotonic() - t0 < 6:
        try:
            r = E.rpc("eth_getTransactionReceipt", ["0x" + h], tries=1, timeout=3)
            if r:
                res.append({"ms": round(1000 * (time.monotonic() - t0)), "blocks": seq_now["s"] - seq, "block": int(r["blockNumber"], 16), "seq": seq}); return
        except Exception:
            pass
        time.sleep(0.04)
    res.append({"ms": None, "blocks": None, "seq": seq})
async def main():
    import websockets
    t_end = time.monotonic() + float(os.environ.get("PROBE_S", "60")); last = 0
    async with websockets.connect(E.FEED_URL, open_timeout=10, max_size=None, compression="deflate") as ws:
        while time.monotonic() < t_end:
            raw = await ws.recv(); fr = json.loads(raw)
            for m in fr.get("messages", []):
                seq = m.get("sequenceNumber"); inner = (m.get("message") or {}).get("message") or {}
                if seq is None or (inner.get("header") or {}).get("kind") != 3: continue
                seq_now["s"] = seq; txs = E.decode_batch(inner.get("l2Msg", ""))
                if txs and time.monotonic() - last > 1.0:
                    tx = E.parse_tx(txs[0])
                    if tx: last = time.monotonic(); threading.Thread(target=poll, args=(tx[4], seq, time.monotonic()), daemon=True).start()
    time.sleep(6)
asyncio.run(main())
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "seat_rpc_lag_probe.json"), "w"))
ok = [r for r in res if r["ms"] is not None]
print(f"{len(res)} txs probed, {len(ok)} receipts served; feed->receipt ms p10/50/90 {[sorted(r['ms'] for r in ok)[int(q*(len(ok)-1))] for q in (.1,.5,.9)] if ok else '-'}; "
      f"feed blocks elapsed p10/50/90 {[sorted(r['blocks'] for r in ok)[int(q*(len(ok)-1))] for q in (.1,.5,.9)] if ok else '-'}; block==seq {sum(1 for r in ok if r['block']==r['seq'])}/{len(ok)}")
