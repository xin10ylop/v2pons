"""Skeptic step 3: the pools with a non-operator buy ahead of the bot's buy. Full swap sequence to the pull (from/to where the census has the tx),
the pull's offset vs the bot buy and vs the outsider buy; whether the outsider sold and at what return; and the control group's pull timing."""
import sys, json, collections, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
rows = json.load(open(HERE + "/rows.json"))
T = load_txs()
OUT = {"0xfeda1c58462150b4cb94c63efce3647e78f883eb", "0x9a12867607c191a7191c08e3d8dea7018e277416", "0x9f3b9a449dfaa2fdfb4dd5e1d8c47b9f12d051ea"}
pids = [r["pid"] for r in rows if any(x["from"] in OUT for x in r["pre_bot"])]
E = load_events(set(pids))
res = []
for r in rows:
    if r["pid"] not in pids: continue
    e = E[r["pid"]]; b0 = r["b0"]
    o = next(x for x in r["pre_bot"] if x["from"] in OUT)
    print(f"\n{r['sub']} {r['pid'][:12]} b0 {b0} {datetime.datetime.utcfromtimestamp(r['ts']).strftime('%m-%d %H:%M:%S')} launch_from {r['from'][:10]} n{r['nonce']} bot +{r['bot_off']} {r['bot_eth']:.4f} pull {r['pull_off']} (bot+{None if r['pull_off'] is None else r['pull_off']-r['bot_off']}, outsider+{None if r['pull_off'] is None else r['pull_off']-o['off']})")
    lim = (r["pull_off"] or 200) + 2
    osold = None
    for i, s in enumerate(e["swaps"]):
        off = s["bn"] - b0
        if off > lim: break
        t = T.get(s["tx"])
        fr = t["from"] if t else "?"; to = t["to"] if t else "?"
        a0 = s["a0"] / 1e18
        tag = "BUY " if s["a0"] < 0 else "SELL"
        print(f"   +{off:4d} {tag} {abs(a0):.6g} ETH tok {abs(s['a1'])/1e18:.6g} from {fr[:10]} to {to[:10]} sel {t['selector'] if t else '?'}")
        if s["a0"] > 0 and t and t["from"] == o["from"]: osold = (off, s["a0"])
    for pl in e["pulls"][:2]:
        t = T.get(pl["tx"]); print(f"   PULL +{pl['bn']-b0} from {t['from'][:10] if t else '?'} to {t['to'][:10] if t else '?'} dl {pl['dl']}")
    res.append({"pid": r["pid"], "sub": r["sub"], "ts": r["ts"], "outsider": o["from"], "o_off": o["off"], "o_eth": o["eth"], "bot_off": r["bot_off"], "pull_off": r["pull_off"], "osold": osold})
json.dump(res, open(HERE + "/s3_outsiders.json", "w"), indent=1)
