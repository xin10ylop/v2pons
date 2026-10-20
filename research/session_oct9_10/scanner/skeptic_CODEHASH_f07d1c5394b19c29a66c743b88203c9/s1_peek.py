import json, collections
D=json.load(open("g3_raw.json")); G=D["pools"]; E=D["events"]; T=D["txs"]
c=collections.Counter()
for p in G[:6]:
    e=E[p["pid"]]; lb=p["launch_block"]
    print("==", p["pid"][:12], "lb", lb, "from", p["launch_from"], "nonce", p["launch_nonce"], "to", p["launch_to"], "hook", p["hooks"], "token", p["token"], "sqrt", p["sqrt_p0"], "tick0", p["tick0"])
    for s in e["swaps"]:
        t=T.get(s["tx"]); 
        print("  swap +%d ti%d sender %s a0 %.6f a1 %d tick %d fee %d | from %s to %s sel %s len %s val %s" % (s["bn"]-lb, s["ti"], s["sender"][:10], s["a0"]/1e18, s["a1"], s["tick"], s["fee"], t and t["from"], t and t["to"], t and t["selector"], t and t["calldata_len"], t and t["value_eth"]))
    for s in e["pulls"]:
        t=T.get(s["tx"])
        print("  pull +%d ti%d lo %d hi %d dl %d sender %s | from %s to %s sel %s" % (s["bn"]-lb, s["ti"], s["lo"], s["hi"], s["dl"], s["sender"][:10], t and t["from"], t and t["to"], t and t["selector"]))
    for s in e["adds"]:
        print("  add +%d lo %d hi %d dl %d sender %s" % (s["bn"]-lb, s["lo"], s["hi"], s["dl"], s["sender"][:10]))
