"""Validate the replay: on our own live trades of the last 6 h (chain), remove our two swaps, replay our buy at the head of its block and our
sell at the head of its block (ours were not always first in the block, so small differences are expected), compare with the real ETH out."""
import pickle, statistics as st
from common import *
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]
err = []; zero = []
for p in P:
    if not p["ours"]: continue
    ob = [s for s in p["sw"] if s["who"] == "ours" and s["buy"]]; os_ = [s for s in p["sw"] if s["who"] == "ours" and not s["buy"]]
    if len(ob) != 1 or len(os_) != 1: continue
    b, s = ob[0], os_[0]
    if s["q"] == 0 or s["L"] == 0: zero.append(p["pid"]); continue
    # exact model: our buy at its true position, others re-applied, our sell at its true position
    sw = [x for x in p["sw"] if x["who"] != "ours"]
    ib = p["sw"].index(b); isell = p["sw"].index(s)
    pre = [x for x in p["sw"][:ib]]
    sp, L = (pre[-1]["sp"], pre[-1]["L"]) if pre else (p["sp0"], p["L0"])
    tokens = v4math.buy_out_int(sp, L, b["q"], p["fee"])
    sp = buy_state(sp, L, b["q"], p["fee"])
    for x in p["sw"][ib + 1:isell]:
        if x["L"] > 0: L = x["L"]
        sp = buy_state(sp, L, x["q"], p["fee"]) if x["buy"] else sell_state(sp, L, x["t"], p["fee"])
    eth = v4math.sell_out_int(sp, L, s["t"], p["fee"])
    err.append(((tokens - b["t"]) / b["t"], (eth - s["q"]) / s["q"], p["fee"]))
print(f"our trades replayed: {len(err)}; token-out rel. error median {st.median(abs(e[0]) for e in err):.2e} max {max(abs(e[0]) for e in err):.2e}; "
      f"sell ETH-out rel. error median {st.median(abs(e[1]) for e in err):.2e} max {max(abs(e[1]) for e in err):.2e}")
print("our sells with 0 ETH out / 0 liquidity (excluded):", len(zero))
