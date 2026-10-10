import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(os.path.join(HERE, "pids.json")))
P = load_pools(); T = load_txs(); E = load_events(set(ids["F1"] + ids["F2"]))
R = json.load(open(os.path.join(HERE, "hookfee_rcpts.json")))
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
fam = sys.argv[1]; nmax = int(sys.argv[2]) if len(sys.argv) > 2 else 6
shown = 0
for pid in ids[fam]:
    p = P[pid]; e = E[pid]
    hook = p["hooks"]; tok = p["token"]
    txs = [p["launch_tx"]] + [s["tx"] for s in e["swaps"] if s["tx"] in T]
    for h in list(dict.fromkeys(txs))[:nmax]:
        r = R.get(h); t = T.get(h)
        if not r: continue
        sw = [s for s in e["swaps"] if s["tx"] == h]
        print("== pid %s tx %s status %s from %s to %s sel %s val %.8f gasUsed %d" % (pid[:10], h[:10], r["status"], t["from"][:10], (t["to"] or "")[:10], t["selector"], t["value_eth"], int(r["gasUsed"], 16)))
        for s in sw: print("   SWAP a0 %d a1 %d fee %d sender %s" % (s["a0"], s["a1"], s["fee"], s["sender"][:10]))
        for l in r["logs"]:
            a = l["address"].lower(); t0 = l["topics"][0] if l["topics"] else ""
            tag = "PM" if a == PMA else ("HOOK" if a == hook else ("TOKEN" if a == tok else a[:10]))
            extra = ""
            if t0 == TR and len(l["topics"]) == 3:
                extra = "Transfer %s -> %s %d" % (l["topics"][1][-40:][:8], l["topics"][2][-40:][:8], int(l["data"], 16) if l["data"] != "0x" else 0)
            print("   ", tag, t0[:10], [x[-40:][:10] for x in l["topics"][1:]], extra or l["data"][:2 + 64 * 6])
    shown += 1
    if shown >= nmax: break
