"""Uniswap v4 hook permissions are the low 14 bits of the hook address. Per hooked candidate group: which callbacks the hooks enable
(beforeSwap can revert a swap, e.g. a sell; *ReturnsDelta can take a hidden cut that the Swap event does not show)."""
import pickle
from common import *
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); FAM = X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
BITS = [(13, "beforeInitialize"), (12, "afterInitialize"), (11, "beforeAddLiquidity"), (10, "afterAddLiquidity"), (9, "beforeRemoveLiquidity"),
        (8, "afterRemoveLiquidity"), (7, "beforeSwap"), (6, "afterSwap"), (5, "beforeDonate"), (4, "afterDonate"), (3, "beforeSwapReturnsDelta"),
        (2, "afterSwapReturnsDelta"), (1, "afterAddLiquidityReturnsDelta"), (0, "afterRemoveLiquidityReturnsDelta")]
def flags(h):
    v = int(h, 16) & 0x3FFF; return tuple(n for b, n in BITS if v >> b & 1)
Z = "0x" + "0" * 40
G = {"C-2 hooked sibling (4e451d1a, PM initialize)": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] != Z,
     "a98b3b9e hooked core (POSM 2020 B)": lambda r, k: "#a98b3b9e" in k and r["hooks"] != Z and r["fee"] == 3000,
     "f07d1c53 one-off": lambda r, k: "f07d1c53" in k,
     "58d59320 via 0xeb7c0347 (shared hook)": lambda r, k: "86b37100" in k,
     "c0b7d400 via POSM initializePool": lambda r, k: "f7020405#c0b7d400" in k,
     "d4e7eae4 hooked (PM initialize, WETH)": lambda r, k: "6276cbbe#d4e7eae4" in k and r["hooks"] != Z,
     "51faa3f1 (0x5bd1fbe7)": lambda r, k: "51faa3f1" in k,
     "c3cd7006 (0xc763b179)": lambda r, k: "c3cd7006" in k,
     "99e0b5e8 (0x18cab14c)": lambda r, k: "049a3b67" in k and r["hooks"] != Z}
out = {}
for g, f in G.items():
    hs = [rows[p]["hooks"] for p, k in FAM.items() if "@" not in k and f(rows[p], k)]
    c = C.Counter(flags(h) for h in hs)
    out[g] = {"pools": len(hs), "distinct_hooks": len(set(hs)), "flags": [[list(a), b] for a, b in c.most_common(3)]}
    print(f"{g}: pools {len(hs)}, distinct hooks {len(set(hs))}; flags {c.most_common(2)}")
json.dump(out, open(os.path.join(D, "hookflags.json"), "w"), indent=1)
