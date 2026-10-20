"""The crowd's own slippage limit: decode each burst buy's Universal Router V4_SWAP (SWAP_EXACT_IN_SINGLE amountOutMinimum, TAKE_ALL
minAmount) and compare it with what the buy got on the chain; then what it would get with our seat buy (each stake) ahead of it."""
import pickle, sys, os, json, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_INIT, T_SWAP, W, sgn
from eth_abi import decode
import v4math
Q96 = 1 << 96
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
def nof(x, fee): return x - (x * fee + 999_999) // 1_000_000
d = pickle.load(open(os.path.join(HERE, "cache_seat.pkl"), "rb"))
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
rows = []
for i, p in enumerate(d["copies"]):
    rec = d["rec"][i]; init = [l for l in rec["logs"] if l["topics"] and l["topics"][0] == T_INIT][0]; token = init["topics"][3][-40:]; fee = W(init["data"], 0)
    txs = {t["hash"]: t for b in d["blocks"][p["pid"]] for t in b["transactions"]}
    sw = sorted([l for l in d["logs"][p["pid"]] if l["topics"][0] == T_SWAP], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    prev_sp = W(init["data"], 3); prev_L = None
    for l in sw:
        a0 = s128(W(l["data"], 0)); a1 = s128(W(l["data"], 1)); sp = W(l["data"], 2); Lq = W(l["data"], 3); bn = int(l["blockNumber"], 16)
        t = txs.get(l["transactionHash"])
        if t and a0 < 0 and -a0 >= 2e14 and t["from"].lower() != DUST and (t["to"] or "").lower() == UR and bn - p["block"] <= 15:
            cmds, inputs, dl = decode(["bytes", "bytes[]", "uint256"], bytes.fromhex(t["input"][10:]))
            for c, x in zip(cmds, inputs):
                if c & 0x3f != 0x10: continue
                actions, params = decode(["bytes", "bytes[]"], x)
                mins = {}
                for a, pa in zip(actions, params):
                    if a == 0x06:
                        w = lambda k: int.from_bytes(pa[32 + 32 * k: 64 + 32 * k], "big")      # word 0 is the struct's offset (0x20)
                        mins["zero_for_one"] = w(5); mins["amount_in"] = w(6); mins["exact_in_min"] = w(7)
                    elif a == 0x0f:
                        cur, mn = decode(["address", "uint256"], pa); mins["take_all_min"] = mn
                    elif a == 0x0c:
                        cur, mx = decode(["address", "uint256"], pa); mins["settle_max"] = mx
            ours = {}
            for stake in (0.0012, 0.004, 0.012):
                X = int(stake * 1e18)
                sp_with = v4math.sqrt_after_buy(prev_sp, Lq, nof(X, fee))       # our buy just ahead of this one
                out_with = v4math.buy_out_int(int(sp_with), Lq, mins.get("amount_in", -a0), fee)
                ours[stake] = out_with
            minv = max(mins.get("exact_in_min", 0), mins.get("take_all_min", 0))
            rows.append({"L": p["block"], "off": bn - p["block"], "eth": -a0 / 1e18, "got": a1, "min": minv, "slack": (a1 / minv - 1) if minv else None,
                         "fails_with_ours": {s: (o < minv) for s, o in ours.items()}, **mins})
        prev_sp = sp
print(f"{len(rows)} crowd buys (real-size, via the Universal Router, by +15)")
nz = [r for r in rows if r["min"]]
print(f"  with a nonzero output minimum: {len(nz)}; slack got/min - 1: " + (f"min {min(r['slack'] for r in nz):.4%} median {st.median(r['slack'] for r in nz):.4%} max {max(r['slack'] for r in nz):.4%}" if nz else "-"))
for s in (0.0012, 0.004, 0.012):
    print(f"  stake {s}: crowd buys that would fail their own minimum with our seat buy just ahead: {sum(1 for r in rows if r['fails_with_ours'][s])}")
for r in rows[:6]: print("  ", {k: v for k, v in r.items()})
json.dump(rows, open(os.path.join(HERE, "seat_crowd_slip.json"), "w"), indent=1, default=str)
