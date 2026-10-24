#!/usr/bin/env python3
"""census_fast.py DAYS OUT.json: census.py's main(), unchanged, with a faster RPC wrapper (read-only; HELIUS_API_KEY).

census.py's rpc() sleeps 5-50 s on every 429 per thread and runs 3 threads, so on this Helius key it reached only 1.5-3 calls/s on
the 30-day run. Here: one shared, adaptive limiter (the gap between calls grows 15% on a 429, with a 0.3 s pause for everyone, and
shrinks 1% on a success, between GAP_MIN and 1 s), 8 threads. Prints call/429 counters and the gap with the progress lines."""
import json, os, sys, time, threading, collections, urllib.request, urllib.error, concurrent.futures
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C

GAP_MIN = float(os.environ.get("RPC_GAP", "0.11")); THREADS = int(os.environ.get("RPC_THREADS", "8"))
_lock = threading.Lock(); _next = [0.0]; _gap = [max(GAP_MIN, 0.15)]; STATS = collections.Counter()


def rpc(m, p):
    err = None; k = 0; n429 = 0
    while k < 12 and n429 < 80:                                         # a 429 does not use up one of the 12 tries
        with _lock:
            wait = _next[0] - time.time(); _next[0] = max(_next[0], time.time()) + _gap[0]
        if wait > 0:
            time.sleep(wait)
        STATS["calls"] += 1
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(C.U[0], json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json"}), timeout=40))
            if "result" in r:
                with _lock:
                    _gap[0] = max(GAP_MIN, _gap[0] * 0.99); STATS["gap_ms"] = int(_gap[0] * 1000)
                return r["result"]
            err = r.get("error"); STATS["rpc_error"] += 1
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429:
                STATS["429"] += 1
                with _lock:
                    _gap[0] = min(1.0, _gap[0] * 1.15); _next[0] = max(_next[0], time.time()) + 0.3
                n429 += 1; continue
            STATS[f"http{e.code}"] += 1
        except Exception as e:
            err = e; STATS["exc"] += 1
        k += 1; time.sleep(1.0 * k)
    raise RuntimeError(f"{m}: {str(err)[:100]}")


class _Pool(concurrent.futures.ThreadPoolExecutor):
    def __init__(self, n=None):
        super().__init__(THREADS)


_print = print


def _p(*a, **k):
    _print(*a, f"[{dict(STATS)}]", **k) if a and str(a[0]).startswith("  ") else _print(*a, **k)


if __name__ == "__main__":
    C.rpc = rpc
    C.cf = type("cf", (), {"ThreadPoolExecutor": _Pool})
    C.print = _p
    t = time.time()
    C.main(float(sys.argv[1]), sys.argv[2])
    _print(f"elapsed {time.time() - t:.0f} s, {dict(STATS)}", flush=True)
