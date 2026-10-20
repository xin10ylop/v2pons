"""Probe eth_getLogs limits WITH an address filter. usage: probe_logs.py <url> <address> <topic0> [spans...]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
url, addr, t0 = sys.argv[1:4]
spans = [int(x) for x in sys.argv[4:]] or [43200, 10000, 5000, 1000, 100]
head = rpc.block_number(url)
for s in spans:
    t = time.time()
    try:
        r = rpc.call(url, "eth_getLogs", [{"fromBlock": hex(head - s), "toBlock": hex(head), "address": addr, "topics": [t0]}], max_retries=2)
        print(url, "span", s, "OK n=", len(r), "secs", round(time.time() - t, 2)); break
    except Exception as e:
        print(url, "span", s, "ERR", str(e)[:160])
print(json.dumps(rpc.STATS.get(url)))
