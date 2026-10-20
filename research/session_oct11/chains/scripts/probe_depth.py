"""For candidate public RPCs: test address-filtered eth_getLogs at a given depth (blocks back) and span."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import rpc
addr, t0 = sys.argv[1], sys.argv[2]
tests = [(int(a), int(b)) for a, b in (x.split(":") for x in sys.argv[3].split(","))]
for url in sys.argv[4:]:
    try:
        h = rpc.block_number(url)
    except Exception as e:
        print(url, "blockNumber ERR", str(e)[:120]); continue
    for back, span in tests:
        try:
            r = rpc.call(url, "eth_getLogs", [{"fromBlock": hex(h-back), "toBlock": hex(h-back+span), "address": addr, "topics": [t0]}], max_retries=2)
            print(url, f"back={back} span={span} OK n={len(r)}")
        except Exception as e:
            print(url, f"back={back} span={span} ERR", str(e)[:130])
