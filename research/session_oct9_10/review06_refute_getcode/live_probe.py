"""Run the c2d9fcb engine read-only (DRY_RUN=1, no wallet, no relay, ENTRY=seat, LAUNCH_SELECTORS=2fcb9108) against the real feed
and RPC. Every eth_getCode the engine makes is logged with its answer, plus, at each launch, 8 extra parallel getCode probes
(fresh connections, like urllib) and a background lag sampler: feed head at send minus the RPC's 'latest' block number."""
import os, sys, json, time, threading
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": os.path.join(OUT, "engine.jsonl"), "ENTRY": "seat", "LAUNCH_SELECTORS": "2fcb9108", "SEAT_FIRE_AT": "6",
                   "HALT_FILE": os.path.join(OUT, "HALTED")})
sys.path.insert(0, os.path.join(HERE, "src"))
import flip_engine as E
from eth_utils import keccak

PLOG = os.path.join(OUT, "probe.jsonl"); _pl = threading.Lock()
def plog(ev):
    ev["t"] = round(time.time(), 3)
    with _pl:
        with open(PLOG, "a") as f:
            f.write(json.dumps(ev) + "\n")

_rpc = E.rpc
def rpc(method, params, tries=4, timeout=10):
    seq0 = E.state["seq"]; t0 = time.monotonic()
    try:
        r = _rpc(method, params, tries, timeout)
    except Exception as e:
        if method in ("eth_getCode", "eth_getTransactionReceipt"):
            plog({"m": method, "seq_at_send": seq0, "err": str(e)[:200], "ms": round(1000 * (time.monotonic() - t0), 1)})
        raise
    if method == "eth_getCode":
        plog({"m": method, "who": "engine", "addr": params[0], "seq_at_send": seq0, "seq_at_reply": E.state["seq"], "len": len(r) // 2 - 1,
              "hash": keccak(bytes.fromhex(r[2:])).hex()[:16], "ms": round(1000 * (time.monotonic() - t0), 1)})
    elif method == "eth_getTransactionReceipt" and r:
        plog({"m": "receipt", "block": int(r["blockNumber"], 16), "seq_at_send": seq0, "ms": round(1000 * (time.monotonic() - t0), 1)})
    return r
E.rpc = rpc

_arm = E.arm_launch
def arm_launch(tx_hash, seq, ts, seen_at, to=None):
    def extra(i):
        s0 = E.state["seq"]; t0 = time.monotonic()
        try:
            c = _rpc("eth_getCode", [E.h0x(to), "latest"], tries=1, timeout=3)
            b = _rpc("eth_blockNumber", [], tries=1, timeout=3)
            plog({"m": "extra_getCode", "i": i, "launch_seq": seq, "seq_at_send": s0, "len": len(c) // 2 - 1, "rpc_head_after": int(b, 16), "ms": round(1000 * (time.monotonic() - t0), 1)})
        except Exception as e:
            plog({"m": "extra_getCode", "i": i, "launch_seq": seq, "err": str(e)[:200]})
    if to:
        for i in range(8):
            threading.Thread(target=extra, args=(i,), daemon=True).start()
    return _arm(tx_hash, seq, ts, seen_at, to)
E.arm_launch = arm_launch

def lag_sampler(k):
    while True:
        s0 = E.state["seq"]; t0 = time.monotonic()
        try:
            b = _rpc("eth_getBlockByNumber", ["latest", False], tries=1, timeout=3)
            plog({"m": "lag", "k": k, "feed_seq_at_send": s0, "rpc_head": int(b["number"], 16), "lag": s0 - int(b["number"], 16), "ms": round(1000 * (time.monotonic() - t0), 1)})
        except Exception as e:
            plog({"m": "lag", "k": k, "err": str(e)[:200]})
        time.sleep(0.5)

for k in range(2):
    threading.Thread(target=lag_sampler, args=(k,), daemon=True).start()
E.main()
