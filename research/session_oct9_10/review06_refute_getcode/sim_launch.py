"""The engine's arm_launch timing on synthetic launches against the live feed and RPC.
At a feed block N (a pretend launch, one every ~1.5 s), exactly as arm_launch at c2d9fcb: a thread reads the state at 'latest'
(eth_call ArbSys.arbBlockNumber, the block a getCode at 'latest' reads; engine rpc(), tries=2, timeout=3) while the arm thread
polls for block N (wait_receipt's loop: tries=1, timeout=3, every 0.04 s); the arm is done at the later of the two.
Per launch: the state block the 'getCode' saw, the feed block when the arm finished.
A launcher deployed g blocks before the launch reads as '0x' iff state_block < N - g. The seat can fire iff the arm finished
while the engine's head was <= N + 6 (it fires on block N+6 or N+7; armed later, block N+8 says 'too late')."""
import os, sys, json, time, threading, asyncio
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": os.path.join(OUT, "sim_engine.jsonl")})
sys.path.insert(0, os.path.join(HERE, "src"))
import flip_engine as E
import websockets
DUR = float(sys.argv[1]); RES = os.path.join(OUT, "sim.jsonl")
seq = [0]; last_launch = [0.0]; lk = threading.Lock()

def poll_block(n, timeout=4.0, every=0.04):                     # wait_receipt's loop, a block for the receipt
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            r = E.rpc("eth_getBlockByNumber", [hex(n), False], tries=1, timeout=3)
            if r:
                return r
        except Exception:
            pass
        time.sleep(every)
    return None

def arm(n, t_seen):
    code = {}
    def fetch():
        s0 = seq[0]
        try:
            c = E.rpc("eth_call", [{"to": "0x0000000000000000000000000000000000000064", "data": "0xa3b1b31d"}, "latest"], tries=2, timeout=3)
            code["state_block"] = int(c, 16); code["seq_at_send"] = s0; code["seq_at_reply"] = seq[0]
        except Exception as e:
            code["err"] = str(e)[:100]
    ct = threading.Thread(target=fetch, daemon=True); ct.start()
    b = poll_block(n)
    rec_seq = seq[0]; rec_ms = round(1000 * (time.monotonic() - t_seen), 1)
    ct.join(3.0)
    arm_seq = seq[0]; arm_ms = round(1000 * (time.monotonic() - t_seen), 1)
    ev = {"N": n, "receipt": b is not None, "rec_seq_off": rec_seq - n, "rec_ms": rec_ms, "arm_seq_off": arm_seq - n, "arm_ms": arm_ms, **code}
    if "state_block" in code:
        ev["code_lag"] = n - code["state_block"]
    with lk:
        with open(RES, "a") as f:
            f.write(json.dumps(ev) + "\n")

async def feed():
    t_end = time.time() + DUR
    async with websockets.connect(E.FEED_URL, max_size=None, compression="deflate", ping_interval=10) as ws:
        while time.time() < t_end:
            f = json.loads(await ws.recv())
            for m in f.get("messages", []):
                s = m["sequenceNumber"]
                if s <= seq[0]:
                    continue
                seq[0] = s
                if time.monotonic() - last_launch[0] > 1.5:
                    last_launch[0] = time.monotonic()
                    threading.Thread(target=arm, args=(s, time.monotonic()), daemon=True).start()
    time.sleep(5)

asyncio.run(feed())
