"""Hook permission bits (v4: the low 14 bits of the hook address) for the hooked candidate lines; are the hook addresses reused; codes known?"""
from cands import *
FL = ["AFTER_REMOVE_LIQ_RETURNS_DELTA", "AFTER_ADD_LIQ_RETURNS_DELTA", "AFTER_SWAP_RETURNS_DELTA", "BEFORE_SWAP_RETURNS_DELTA", "AFTER_DONATE", "BEFORE_DONATE",
      "AFTER_SWAP", "BEFORE_SWAP", "AFTER_REMOVE_LIQ", "BEFORE_REMOVE_LIQ", "AFTER_ADD_LIQ", "BEFORE_ADD_LIQ", "AFTER_INIT", "BEFORE_INIT"]
codes = {}
for l in open(os.path.join(CEN, "cache", "codes.jsonl")):
    x = json.loads(l); codes[x["addr"]] = x
rows = rows_nonvbot()
for name in ("a98b_hook", "564f_weth_hook", "C1_eth"):
    rs = [r for r in rows if CANDS[name](r)]
    hk = C.Counter(r["hooks"] for r in rs)
    flags = C.Counter()
    for h, n in hk.items():
        v = int(h, 16) & 0x3FFF
        flags[tuple(FL[i] for i in range(14) if v >> i & 1)] += n
    print(name, "pools", len(rs), "distinct hooks", len(hk), "top", hk.most_common(3), "\n   flag sets:", flags.most_common(5),
          "\n   hook code known:", sum(1 for h in hk if h in codes), " token==hook:", sum(1 for r in rs if r["hooks"] == r["token"]))
