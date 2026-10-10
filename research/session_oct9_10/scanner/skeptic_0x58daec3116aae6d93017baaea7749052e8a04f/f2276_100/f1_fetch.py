"""Skeptic f2276/100, step 1: an out-of-sample window and full transaction attribution.
(a) every PM Initialize after the census head (85,203,897) to now - 3,100 blocks; keep the fee-100 / ts-1 / hooks-0 / ETH pools, fetch
    their launch txs and keep the POSM ac9650d8 2,276-byte ones; (b) their Swap + ModifyLiquidity logs launch..launch+3000;
(c) the transaction of EVERY swap and pull in those pools and in a seeded random sample of 60 census pools of the family
    (the census only has the first 8 swaps' txs). Caches to data/*.json; reruns resume."""
import sys, os, json, random, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import load_families, load_events
K = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
START = 85_203_898

def cached(name, fn):
    p = os.path.join(D, name)
    if os.path.exists(p): return json.load(open(p))
    r = fn(); json.dump(r, open(p, "w")); return r

head = cached("head.json", lambda: int(rpc("eth_blockNumber", []), 16) - 10)
END = head - 3100
def get_inits():
    out = []
    for a in range(START, END + 1, 100_000):
        out += logs({"address": PM, "topics": [T_INIT]}, a, min(END, a + 99_999))
    return out
inits = cached("inits.json", get_inits)
cand = []
for l in inits:
    c0 = "0x" + l["topics"][2][-40:]; d = l["data"]
    fee, ts, hooks, sp = W(d, 0), sgn(W(d, 1)), "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], W(d, 3)
    if c0 == "0x" + "0" * 40 and fee == 100 and ts == 1 and int(hooks, 16) == 0:
        cand.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "sp0": sp, "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "li": int(l["logIndex"], 16)})
print("inits", len(inits), "fee100 ts1 ETH", len(cand))
def get_ltx():
    r = batch([("eth_getTransactionByHash", [c["tx"]]) for c in cand]); return r
ltx = cached("ltx.json", get_ltx)
fresh = []
for c, t in zip(cand, ltx):
    if t and t["to"] == POSM and t["input"][:10] == "0xac9650d8" and (len(t["input"]) - 2) // 2 == 2276:
        c.update({"from": t["from"], "nonce": int(t["nonce"], 16), "input": t["input"], "value": int(t["value"], 16)}); fresh.append(c)
print("fresh family launches", len(fresh), "of", len(cand))
def get_ev():
    out = {}
    pids = [c["pid"] for c in fresh]
    for i in range(0, len(fresh), 20):
        grp = fresh[i:i + 20]
        a = min(c["bn"] for c in grp); b = max(c["bn"] for c in grp) + 3000
        lg = logs({"address": PM, "topics": [[T_SWAP, T_ML], [c["pid"] for c in grp]]}, a, b)
        for l in lg: out.setdefault(l["topics"][1], []).append(l)
    return out
ev = cached("fresh_logs.json", get_ev)
print("fresh pools with logs", len(ev), "logs", sum(len(v) for v in ev.values()))
json.dump(fresh, open(os.path.join(D, "fresh_launches.json"), "w"))
# the census sample
F = load_families(); pids = F[K]["pids"]
rnd = random.Random(20261010); samp = sorted(rnd.sample(pids, 60))
json.dump(samp, open(os.path.join(D, "census_sample.json"), "w"))
E = load_events(set(samp))
hashes = set()
for pid in samp:
    for s in E[pid]["swaps"]: hashes.add(s["tx"])
    for s in E[pid]["pulls"]: hashes.add(s["tx"])
for pid, lg in ev.items():
    for l in lg: hashes.add(l["transactionHash"])
txp = os.path.join(D, "txs.jsonl")
have = set()
if os.path.exists(txp):
    for line in open(txp): have.add(json.loads(line)["hash"])
todo = sorted(hashes - have)
print("txs needed", len(hashes), "to fetch", len(todo))
with open(txp, "a") as f:
    for i in range(0, len(todo), 500):
        ch = todo[i:i + 500]
        r = batch([("eth_getTransactionByHash", [h]) for h in ch])
        for h, t in zip(ch, r):
            if t is None: continue
            f.write(json.dumps({"hash": h, "from": t["from"], "to": t["to"], "nonce": int(t["nonce"], 16), "value": int(t["value"], 16), "bn": int(t["blockNumber"], 16),
                                "ti": int(t["transactionIndex"], 16), "gas": int(t["gas"], 16), "gp": int(t.get("gasPrice", "0x0"), 16),
                                "prio": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "input": t["input"] if len(t["input"]) < 6000 else t["input"][:6000]}) + "\n")
        f.flush(); print("  fetched", i + len(ch), flush=True); time.sleep(0.3)
