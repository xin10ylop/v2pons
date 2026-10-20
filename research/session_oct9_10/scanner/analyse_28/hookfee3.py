"""Per swap: the hook's ETH take from the PoolManager's ERC6909 mint to the hook (event 0x1b3d7edb, id 0 = ETH) and token Transfers; ratio to the Swap's a0."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(os.path.join(HERE, "pids.json")))
P = load_pools(); T = load_txs(); E = load_events(set(ids["F1"] + ids["F2"]))
R = json.load(open(os.path.join(HERE, "hookfee_rcpts.json")))
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
T6909 = "0x1b3d7edb2e9c0b0e7c525b20aaaef0f5940d2ed71663c7d39266ecafac728859"
rows = []
for fam in ("F1", "F2"):
    for pid in ids[fam]:
        p = P[pid]; e = E[pid]; hook = p["hooks"]; tok = p["token"]
        for s in e["swaps"]:
            r = R.get(s["tx"]); t = T.get(s["tx"])
            if not r or not t: continue
            nsw = sum(1 for x in e["swaps"] if x["tx"] == s["tx"])
            if nsw != 1: continue
            mint_hook = sum(int(l["data"][66:130], 16) for l in r["logs"] if l["address"].lower() == PMA and l["topics"][0] == T6909 and l["topics"][2][-40:] == hook[2:] and int(l["topics"][3], 16) == 0)
            mint_hook_tok = sum(int(l["data"][66:130], 16) for l in r["logs"] if l["address"].lower() == PMA and l["topics"][0] == T6909 and l["topics"][2][-40:] == hook[2:] and int(l["topics"][3], 16) != 0)
            tok_tr = [(l["topics"][1][-40:], l["topics"][2][-40:], int(l["data"], 16)) for l in r["logs"] if l["address"].lower() == tok and l["topics"][0] == TR and len(l["topics"]) == 3]
            hook_logs = collections.Counter(l["topics"][0][:10] for l in r["logs"] if l["address"].lower() == hook)
            side = "buy" if s["a0"] < 0 else "sell"
            rows.append({"fam": fam, "pid": pid[:10], "rel": s["bn"] - p["launch_block"], "side": side, "a0": s["a0"], "a1": s["a1"], "val": t["value_wei"],
                         "to": t["to"][:10], "sel": t["selector"], "hook_eth": mint_hook, "hook_tok": mint_hook_tok,
                         "hook_eth_over_a0": mint_hook / abs(s["a0"]) if s["a0"] else None, "val_over_a0": t["value_wei"] / abs(s["a0"]) if s["a0"] < 0 and t["value_wei"] else None,
                         "tok_tr": [(a[:6], b[:6], v) for a, b, v in tok_tr][:4], "hook_logs": dict(hook_logs), "launch": s["tx"] == p["launch_tx"]})
for fam in ("F2", "F1"):
    print("=====", fam)
    for side in ("buy", "sell"):
        rr = [x for x in rows if x["fam"] == fam and x["side"] == side]
        print(side, len(rr), "hook_eth/|a0| values:", collections.Counter(round(x["hook_eth_over_a0"], 5) for x in rr).most_common(8))
        print("   hook_tok>0:", sum(1 for x in rr if x["hook_tok"] > 0), "val/|a0|:", collections.Counter(round(x["val_over_a0"], 4) if x["val_over_a0"] else None for x in rr).most_common(8))
    for x in [x for x in rows if x["fam"] == fam][:400]:
        if fam == "F1" or x["side"] == "sell":
            print("  ", x["pid"], x["rel"], x["side"], "a0 %d a1 %d val %d to %s sel %s hook_eth %d (%.5f) hook_tok %d val/a0 %s tok %s hooklogs %s" % (x["a0"], x["a1"], x["val"], x["to"], x["sel"], x["hook_eth"], x["hook_eth_over_a0"] or 0, x["hook_tok"], x["val_over_a0"] and round(x["val_over_a0"], 5), x["tok_tr"], x["hook_logs"]))
json.dump(rows, open(os.path.join(HERE, "hookfee.json"), "w"), indent=0)
