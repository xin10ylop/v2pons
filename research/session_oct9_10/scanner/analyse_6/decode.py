"""Decode the launch calls of the four families (constant words, token metadata, inner selectors)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools(); F = load_families(); T = load_txs()
KEYS = ["0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true",
        "0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true",
        "0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true",
        "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true"]
def words(inp): return [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
def s(h):
    try: return bytes.fromhex(h).rstrip(b"\0").decode()
    except Exception: return None
out = {}
for k in KEYS:
    ws = [words(T[P[pid]["launch_tx"]]["input"]) for pid in F[k]["pids"]]
    const = {i: ws[0][i] for i in range(min(len(w) for w in ws)) if all(w[i] == ws[0][i] for w in ws)}
    txs = [T[P[pid]["launch_tx"]] for pid in F[k]["pids"]]
    meta = []
    if k.split("|")[1] == "7fde822e":
        for w in ws:
            # string tails: name word 11/12, symbol 13/14, image 15.., socials
            meta.append({"name": s(w[12]), "symbol": s(w[14])})
    out[k] = {"const_words": {i: v for i, v in const.items()}, "n_words": len(ws[0]), "tokens_meta": meta[:15],
              "gas_price_gwei": sorted(set(round(t["gas_price"] / 1e9, 4) for t in txs if t.get("gas_price"))), "max_prio": sorted(set(str(t["max_prio"]) for t in txs)),
              "types": sorted(set(t["type"] for t in txs)), "gas": pct([t["gas"] for t in txs]), "from": sorted(set(t["from"] for t in txs))}
    if k.startswith("0x0000ffff"):
        inp = txs[0]["input"]
        sels = sorted(set(inp[i:i + 8] for i in range(10, len(inp) - 8, 2) if inp[i:i + 8] in ("f7020405", "dd46508f", "695c5bf5", "3593564c", "ac9650d8")))
        out[k]["inner_selectors_found"] = sels
        out[k]["example_words"] = words(inp)
json.dump(out, open(os.path.join(HERE, "decode.json"), "w"), indent=1)
for k, v in out.items():
    print("=====", k)
    for a, b in v.items(): print(" ", a, json.dumps(b)[:1500])
