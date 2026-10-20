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
    byh = {}
    for l in sw: byh.setdefault(l["transactionHash"], l)
    txs = {t["hash"]: (int(b["number"], 16), t) for b in P["blocks"] if b for t in b["transactions"]}
    # walk swaps; for each bot buy: minOut vs actual out and vs quote at various states
    states = [(b0, SP0)]
    out = []
    for l in sw:
        bn = int(l["blockNumber"], 16); d = l["data"]; a0 = s128(W(d, 0)); a1 = s128(W(d, 1)); sp = W(d, 2)
        h = l["transactionHash"]
        if h in txs and txs[h][1]["to"].lower().startswith("0x1cbaf24d") and txs[h][1]["input"][:10] == "0xc1120e3d" and a0 < 0:
            inp = txs[h][1]["input"]; words = [int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16) for i in range((len(inp) - 10) // 64)]
            v = int(txs[h][1]["value"], 16)
            q0 = v4math.buy_out_int(SP0, L0, v, 2500)                 # quote from the launch state
            qprev = v4math.buy_out_int(states[-1][1], L0, v, 2500)    # quote from the state just before
            mo = words[4] if len(words) > 4 else None
            out.append((bn - b0, v / 1e18, a1, mo, round(mo / a1, 4) if mo else None, round(mo / q0, 4) if mo else None, round(mo / qprev, 4) if mo else None,
                        [hex(w)[:12] if w > 1e30 else w for w in words[:10]]))
        states.append((bn, sp))
    print("==", pid[:12], m["src"])
    for o in out[:4]: print("   +%d val %.4f out %.4e minOut %s | minOut/out %s /quote_launch %s /quote_prev %s | words %s" % o)
