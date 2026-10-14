"""BSC: what the operator's router 0x07cb6161 launches besides the fee-5000 v4 line: for a sample of router-minted tokens (t24) spread over
time, the deploy tx (sender, value, nonce), then the token's Transfers in the next 60 blocks: where the launch wallet sent the tokens
(the pool/pair), that address's code size and, for a pair, its factory(); the launch tx (to, selector, value)."""
import sys, json, time, collections, random
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_TRANSFER, unpad, pad, jl, J
R = "0x07cb61618b69234d954022ff738a015548715533"
def call(c, m, p):
    for i in range(12):
        try: time.sleep(0.5); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if any(k in str(e).lower() for k in ("429", "rate", "timed out", "timeout")): time.sleep(5 * (i + 1)); continue
            raise
m = sorted({r["tok"]: r for r in jl(J("t24_mints_cache.jsonl"))}.values(), key=lambda r: r["b"])
inits = {i["c1"] for i in jl(J("t21_bsc_inits_cache.jsonl"))}
cand = [r for r in m if r["tok"] not in inits]
random.seed(3); samp = sorted(random.sample(cand, min(int(sys.argv[1]) if len(sys.argv) > 1 else 16, len(cand))), key=lambda r: r["b"])
fam = collections.Counter()
for r in samp:
    dep = call("bsc", "eth_getTransactionByHash", [r["tx"]]); w = dep["from"].lower()
    tl = call("bsc48", "eth_getLogs", [{"address": r["tok"], "fromBlock": hex(r["b"]), "toBlock": hex(r["b"] + 60), "topics": [T_TRANSFER, pad(w)]}])
    dest = [(unpad(l["topics"][2]), l["transactionHash"]) for l in tl]
    info = []
    for d, h in dest[:1]:
        code = call("bsc", "eth_getCode", [d, "latest"])
        fac = None
        try: fac = "0x" + call("bsc", "eth_call", [{"to": d, "data": "0xc45a0155"}, "latest"])[-40:]
        except Exception: pass
        lt = call("bsc", "eth_getTransactionByHash", [h])
        info = [d, (len(code) - 2) // 2, fac, lt["to"], lt["input"][:10], (len(lt["input"]) - 2) // 2, int(lt["value"], 16) / 1e18, int(lt["gas"], 16)]
    key = (info[2], info[3], info[4], info[5], round(info[6], 7)) if info else ("no launch in 60 blocks",)
    fam[key] += 1
    print(r["b"], r["tok"], "deployer", w[:10], "nonce", int(dep["nonce"], 16), "deploy value", int(dep["value"], 16) / 1e18, "-> launch", info, flush=True)
print("families (factory, launch to, selector, calldata len, value):")
for k, n in fam.most_common(): print("  ", k, n)
