import sys, os, pickle, json, collections, random
sys.path.insert(0, ".."); sys.path.insert(0, ".")
from chain import batch
from eth_utils import keccak
from fams import families
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]
F = families(P, pids)
want = ["L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0",
        "L:OURS-orig", "L:0x58daec31|0xac9650d8|len2276|fee100|ts1|v0", "L:0x8366a39c|0x6276cbbe|len196|fee500|ts1|v0", "L:OURS-copy"]
random.seed(3)
toks = []
for w in want:
    s = random.sample(F[w], 4)
    toks += [(w, P[pids[i]]["token"]) for i in s]
r = batch([("eth_getCode", [t, "latest"]) for _, t in toks])
KNOWN = {"06fdde03": "name", "95d89b41": "symbol", "313ce567": "decimals", "18160ddd": "totalSupply", "70a08231": "balanceOf", "a9059cbb": "transfer", "dd62ed3e": "allowance",
         "095ea7b3": "approve", "23b872dd": "transferFrom", "8da5cb5b": "owner", "715018a6": "renounceOwnership", "f2fde38b": "transferOwnership", "42966c68": "burn", "79cc6790": "burnFrom",
         "40c10f19": "mint", "d505accf": "permit", "7ecebe00": "nonces", "3644e515": "DOMAIN_SEPARATOR", "84b0196e": "eip712Domain", "39509351": "increaseAllowance", "a457c2d7": "decreaseAllowance"}
def selectors(code):
    b = bytes.fromhex(code[2:]); out = set(); i = 0
    while i < len(b):
        op = b[i]
        if op == 0x63 and i + 5 < len(b) and b[i + 5] in (0x14, 0x81, 0x80, 0x82) or (op == 0x63 and i + 6 < len(b) and b[i+5] == 0x81 ):
            out.add(b[i + 1:i + 5].hex())
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return out
res = collections.defaultdict(list)
for (w, t), c in zip(toks, r):
    c = c or "0x"
    sels = selectors(c)
    unk = sorted(s for s in sels if s not in KNOWN)
    res[w].append({"token": t, "size": (len(c) - 2) // 2, "hash": keccak(bytes.fromhex(c[2:])).hex()[:12], "known": sorted(KNOWN[s] for s in sels if s in KNOWN), "unknown": unk})
for w, v in res.items():
    print("==", w)
    for x in v: print("  ", x["token"], x["size"], x["hash"], "unknown sel:", x["unknown"][:12], "| known:", ",".join(x["known"]))
json.dump(res, open("tokcode.json", "w"), indent=1)
