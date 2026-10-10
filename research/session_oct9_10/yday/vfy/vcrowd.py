"""For every paper trade that sells: each crowd buy landing between our buy (end of B) and our sell (head of S): would it still
fill with our buy ahead of it? Its own amountOutMinimum decoded from its Universal Router calldata (ExactInputSingle:
c0, c1, fee, tickSpacing, hooks, zeroForOne, amountIn, amountOutMinimum)."""
import json, sys
from vprice import *
OUT = {r["block"]: r for r in json.load(open("vprice_out.json"))}
def decode_min(inp, token, fee):
    h = inp[10:]; tw = "0" * 24 + token
    for k in range(0, len(h) - 64 * 8, 64):
        if h[k:k + 64] == tw and int(h[k - 64:k], 16) == 0 and int(h[k + 64:k + 128], 16) == fee:
            zfo = int(h[k + 64 * 4:k + 64 * 5], 16); ain = int(h[k + 64 * 5:k + 64 * 6], 16); amin = int(h[k + 64 * 6:k + 64 * 7], 16)
            return zfo, ain, amin
    return None
issues = []; checked = 0; undecoded = 0
for blk, o in sorted(OUT.items()):
    if not o["results"]: continue
    R = json.load(open(f"raw/{blk}.json")); tok = R["token"].lower(); fee = o["fee_ppm"]
    tx = {t["h"]: t for b in R["blocks"] for t in b["txs"]}
    ev = sorted(R["near"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [{"bn": int(l["blockNumber"], 16), "a0": sg(word(l["data"], 0) & ((1 << 128) - 1), 128), "a1": sg(word(l["data"], 1) & ((1 << 128) - 1), 128), "sp": word(l["data"], 2), "L": word(l["data"], 3), "tx": l["transactionHash"]}
          for l in ev if l["topics"][0] == T_SWAP and "0x" + l["topics"][2][-40:] != RELAY]
    sw = [x for x in sw if not (x["tx"] in tx and tx[x["tx"]]["from"] == WALLET)]
    for stake, RR in o["results"].items():
        X = int(round(float(stake) * 1e18)); xn = nof(X, fee)
        for var, r in RR.items():
            if r["exit"] in ("buy_reverted", "pull_first", "pull_at_or_before_buy"): continue
            B, S = r["buy_block"], r["sell_land_block"]
            prevs = [x for x in sw if x["bn"] <= B]; spB = prevs[-1]["sp"] if prevs else None; L = prevs[-1]["L"]
            s = Q96 / (Q96 / spB + xn / L); prev = spB
            for x in sw:
                if x["bn"] <= B: continue
                if x["bn"] >= S: break
                if x["a0"] < 0:
                    t = tx.get(x["tx"]); dec = decode_min(t["input"], tok, fee) if t and t["input"] else None
                    got = v4math.buy_out_int(int(s), L, -x["a0"], fee); real = x["a1"]
                    checked += 1
                    if dec is None: undecoded += 1; issues.append((blk, stake, var, x["bn"] - B, "undecoded", -x["a0"] / 1e18))
                    else:
                        zfo, ain, amin = dec
                        if got < amin: issues.append((blk, o["time_utc"][11:], stake, var, f"B+{x['bn'] - B}", round(-x["a0"] / 1e18, 6), "REVERTS", round(got / amin, 4), round(real / amin, 4)))
                    s = Q96 / (Q96 / s + (Q96 / x["sp"] - Q96 / prev))
                else:
                    s = s + (x["sp"] - prev)
                prev = x["sp"]
print("crowd buys checked", checked, "undecoded", undecoded)
for i in issues: print(i)
