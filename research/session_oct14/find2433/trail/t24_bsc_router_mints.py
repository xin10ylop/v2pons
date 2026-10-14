"""BSC: every token minted to the operator's BSC bot router 0x07cb6161 (Transfer from 0x0 to the router = a 7422a284 deploy) from a start
block to the head; 48 Club public RPC, topic-only getLogs in 5,000-block ranges. Rows in t24_mints_cache.jsonl."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_TRANSFER, pad, jl, J
R = "0x07cb61618b69234d954022ff738a015548715533"; Z = "0x" + "0" * 40
A0 = int(sys.argv[1]); STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
def call(c, m, p):
    for i in range(12):
        try: time.sleep(0.5); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if any(k in str(e).lower() for k in ("429", "rate", "timed out", "timeout")): time.sleep(5 * (i + 1)); continue
            raise
h = int(call("bsc", "eth_blockNumber", []), 16)
done = {r["a"] for r in jl(J("t24_done_cache.jsonl"))}
with open(J("t24_mints_cache.jsonl"), "a") as f, open(J("t24_done_cache.jsonl"), "a") as fd:
    for s in range(A0, h + 1, STEP):
        if s in done: continue
        e = min(h, s + STEP - 1)
        L = call("bsc48", "eth_getLogs", [{"fromBlock": hex(s), "toBlock": hex(e), "topics": [T_TRANSFER, pad(Z), pad(R)]}])
        for l in L: f.write(json.dumps({"b": int(l["blockNumber"], 16), "tok": l["address"].lower(), "tx": l["transactionHash"], "amt": l["data"][:66]}) + "\n")
        f.flush()
        if e < h: fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), flush=True)
print("head", h)
