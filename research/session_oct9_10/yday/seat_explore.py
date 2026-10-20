import pickle, sys, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, T_INIT, W, sgn, PM
from eth_utils import keccak
d = pickle.load(open("cache_seat.pkl", "rb"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
DUST = "e71a69f434a719cd5afa411568b69716aab3b84a"
hc = collections.Counter()
for i, p in enumerate(d["copies"]):
    c = d["code"][i]; cp = d["code_prev"][i]
    h = keccak(bytes.fromhex(c[2:])).hex() if c and len(c) > 2 else None
    hc[(h, len(c)//2-1 if c else None, len(cp)//2-1 if cp else None)] += 1
print(hc)
# per pool timeline
for i, p in enumerate(d["copies"][:49]):
    pid = p["pid"]; L = p["block"]; blocks = d["blocks"][pid]
    txs = {t["hash"]: t for b in blocks for t in b["transactions"]}
    ls = sorted(d["logs"][pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    rec = d["rec"][i]
    out = []
    pull = None
    for l in ls:
        bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            dl = sgn(W(l["data"], 2))
            if dl < 0 and pull is None: pull = bn
            out.append(f"ML+{bn-L}:{dl:.2e}")
            continue
        a0 = s128(W(l["data"], 0)); t = txs.get(l["transactionHash"])
        fr = t["from"][2:6] if t else "?"
        if t and t["from"][2:].lower() == DUST: fr = "DUST"
        out.append(f"+{bn-L}:{-a0/1e18:.5f}/{fr}/L{W(l['data'],3):.2e}")
    ts = int(blocks[0]["timestamp"], 16)
    print(time.strftime("%H:%M:%S", time.gmtime(ts)), L, p["fee"], "pull", (pull - L) if pull else None, rec["status"], " ".join(out[:16]))
