"""Which pool state does the volume bot's minOut come from? minOut = floor(0.99 * quote)?; compare with buy_out_int at the state after each
earlier swap (k = number of swaps included); report the matching state's block lag behind the bot's buy, and the slippage room."""
import pickle, sys
sys.path.insert(0, "/home/user/v2pons/src"); sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
import v4math
from chain import T_SWAP, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
D = pickle.load(open("adv/cache.pkl", "rb"))
SP0 = 1604517591721945638372359205383840; L0 = 49279426163460954002188
for pid, P in D.items():
    m = P["meta"]; b0 = m["b0"]
    sw = sorted([l for l in P["logs"] if l["topics"][0] == T_SWAP], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    txs = {t["hash"]: (int(b["number"], 16), t) for b in P["blocks"] if b for t in b["transactions"]}
    states = [(b0, SP0, "launch")]; rows = []
    for l in sw:
        bn = int(l["blockNumber"], 16); d = l["data"]; a0 = s128(W(d, 0)); a1 = s128(W(d, 1)); sp = W(d, 2); h = l["transactionHash"]
        if h in txs and (txs[h][1]["to"] or "").lower().startswith("0x1cbaf24d") and a0 < 0 and bn - b0 <= 45:
            inp = txs[h][1]["input"]; mo = int(inp[10 + 64 * 4: 10 + 64 * 5], 16); v = int(txs[h][1]["value"], 16)
            best = None
            for k, (sbn, ssp, tag) in enumerate(states):
                q = v4math.buy_out_int(ssp, L0, v, 2500)
                for f in (0.99, 0.95, 0.97, 0.98):
                    if abs(int(q * f) - mo) <= max(2, mo * 1e-9):
                        best = (k, sbn - b0, tag, f)
            # the max front-run (ETH) that keeps the bot's output >= minOut, from the state just before the bot's buy
            sp_before = states[-1][1]
            lo, hi = 0, int(0.2e18)
            while hi - lo > int(1e13):
                mid = (lo + hi) // 2
                sp2, _ = v4math.sqrt_after_buy(sp_before, L0, mid - (mid * 2500 + 999999) // 10**6), None
                out = v4math.buy_out_int(int(sp2), L0, v, 2500)
                if out >= mo: lo = mid
                else: hi = mid
            rows.append((bn - b0, v / 1e18, best, lo / 1e18, len(states) - 1))
        states.append((bn, sp, f"+{bn-b0}{'B' if a0 < 0 else 'S'}"))
    print("==", pid[:12], m["src"], "| bot buys (+off, ETH, matched quote state (k, its block offset, tag, factor), max front-run ETH before revert, swaps before):")
    for r in rows[:3]: print("    ", r)
