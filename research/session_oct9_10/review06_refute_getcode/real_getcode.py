"""The finding's exact read on real contracts: every contract created on the chain (a feed transaction with no `to`) is read with the
engine's rpc("eth_getCode", [addr, "latest"], tries=2, timeout=3) at the moment the feed shows its creation block + 7 and + 8
(the launch's place for a launcher copy deployed 7 or 8 blocks before). 5 s later the code is read again: only contracts that
exist then count. An empty first read is the '0x' the engine would hash to c5d24601..."""
import os, sys, json, time, threading, asyncio, collections
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": os.path.join(OUT, "rg_engine.jsonl")})
sys.path.insert(0, os.path.join(HERE, "src"))
import flip_engine as E
import websockets, rlp
from eth_account import Account
from eth_utils import keccak
DUR = float(sys.argv[1]); RES = os.path.join(OUT, "real_getcode.jsonl"); lk = threading.Lock()
seq = [0]; pending = collections.defaultdict(list)          # feed block -> [(addr, created_in, gap)]

def probe(addr, created, gap, n):
    s0 = seq[0]; t0 = time.monotonic()
    try:
        c = E.rpc("eth_getCode", [addr, "latest"], tries=2, timeout=3); first = len(c) // 2 - 1; err = None
    except Exception as e:
        first = None; err = str(e)[:80]
    ms = round(1000 * (time.monotonic() - t0), 1)
    time.sleep(5)
    try:
        later = len(E.rpc("eth_getCode", [addr, "latest"], tries=3, timeout=5)) // 2 - 1
    except Exception:
        later = None
    with lk:
        with open(RES, "a") as f:
            f.write(json.dumps({"addr": addr, "created": created, "gap": gap, "read_at_feed": s0, "first_len": first, "err": err, "ms": ms, "later_len": later,
                                "empty_first": first == 0 and bool(later)}) + "\n")

async def feed():
    t_end = time.time() + DUR
    async with websockets.connect(E.FEED_URL, max_size=None, compression="deflate", ping_interval=10) as ws:
        while time.time() < t_end:
            f = json.loads(await ws.recv())
            for m in f.get("messages", []):
                s = m["sequenceNumber"]; inner = (m.get("message") or {}).get("message") or {}
                if s <= seq[0] or (inner.get("header") or {}).get("kind") != 3:
                    continue
                seq[0] = s
                for addr, created, gap in pending.pop(s, []):
                    threading.Thread(target=probe, args=(addr, created, gap, s), daemon=True).start()
                for t in E.decode_batch(inner.get("l2Msg", "")):
                    tx = E.parse_tx(t)
                    if tx is None or tx[0] != "":
                        continue
                    try:
                        sender = Account.recover_transaction(t)
                    except Exception:
                        continue
                    addr = "0x" + keccak(rlp.encode([bytes.fromhex(sender[2:]), tx[3]]))[-20:].hex()
                    for gap in (7, 8):
                        pending[s + gap].append((addr, s, gap))
    time.sleep(8)

asyncio.run(feed())
R = [json.loads(l) for l in open(RES)]
for gap in (7, 8):
    r = [x for x in R if x["gap"] == gap and x["later_len"]]
    print(f"gap {gap}: contracts {len(r)}, first read empty ('0x') {sum(x['empty_first'] for x in r)}, read errors {sum(1 for x in r if x['err'])}")
