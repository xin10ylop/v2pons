"""hook 0x4e346895 (family 0x1eef016f|60956835): receipts of the buys and sells of its traded pools (cached), to read the hook's cut:
token Transfer logs to/from the trader, the tx value vs the Swap's ETH, and the companion swaps/adds by 0x6f02324d."""
import sys, json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common20 import *
from chain import batch, rpc
P = load_pools(); T = load_txs()
pids = [p["pid"] for p in P.values() if p["hooks"] == "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544"]
E = load_events(set(pids))
want = []
for pid in pids:
    sw = (E.get(pid) or {}).get("swaps", [])
    b = [s for s in sw if s["a0"] < 0 and s["sender"] != "0x6f02324d20cc679d0e585290caa6b16bacbc0f77"][:5]
    se = [s for s in sw if s["a0"] > 0 and s["sender"] != "0x6f02324d20cc679d0e585290caa6b16bacbc0f77"][:3]
    want += [s["tx"] for s in b + se]
want = list(dict.fromkeys(want))
CACHE = os.path.join(HERE, "hookfee_rcpts.json"); TCACHE = os.path.join(HERE, "hookfee_txs.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
TX = json.load(open(TCACHE)) if os.path.exists(TCACHE) else {}
miss = [h for h in want if h not in R]
if miss: R.update(zip(miss, batch([("eth_getTransactionReceipt", [h]) for h in miss]))); json.dump(R, open(CACHE, "w"))
miss = [h for h in want if h not in TX]
if miss: TX.update(zip(miss, batch([("eth_getTransactionByHash", [h]) for h in miss]))); json.dump(TX, open(TCACHE, "w"))
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
Wd = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
out = []
for pid in pids:
    p = P[pid]; tok = p["token"]
    for s in (E.get(pid) or {}).get("swaps", []):
        if s["tx"] not in want or s["sender"] == "0x6f02324d20cc679d0e585290caa6b16bacbc0f77": continue
        r = R[s["tx"]]; t = TX[s["tx"]]; frm = t["from"].lower()
        trs = [("0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:], int(l["data"], 16)) for l in r["logs"] if l["address"].lower() == tok and l["topics"][0] == TRANSFER]
        comp = [x for x in E[pid]["swaps"] if x["tx"] == s["tx"] and x["sender"] == "0x6f02324d20cc679d0e585290caa6b16bacbc0f77"]
        row = {"pid": pid[:12], "rel": s["bn"] - p["launch_block"], "side": "buy" if s["a0"] < 0 else "sell", "a0": s["a0"], "a1": s["a1"],
               "value": int(t["value"], 16), "to": t["to"], "from": frm, "sel": t["input"][:10], "status": r["status"], "gas_used": int(r["gasUsed"], 16),
               "n_logs": len(r["logs"]), "log_addrs": collections.Counter(l["address"].lower()[:10] for l in r["logs"]).most_common(8),
               "transfers": [(a[:10], b[:10], v) for a, b, v in trs], "companion_swaps_eth": [x["a0"] for x in comp]}
        if s["a0"] < 0:
            got = sum(v for a, b, v in trs if b == frm)
            row["value_over_a0"] = row["value"] / -s["a0"]; row["trader_tokens_over_a1"] = got / s["a1"] if s["a1"] else None
            row["companion_eth_over_a0"] = sum(x["a0"] for x in comp) / -s["a0"]
        else:
            row["companion_eth_over_a0"] = sum(x["a0"] for x in comp) / s["a0"]
            sent = sum(v for a, b, v in trs if a == frm)
            row["trader_tokens_sent_over_a1"] = sent / -s["a1"] if s["a1"] else None
        out.append(row)
for r in out:
    print({k: v for k, v in r.items() if k not in ("transfers",)})
    print("     transfers", r["transfers"])
json.dump(out, open(os.path.join(HERE, "hookfee.json"), "w"), indent=1)
