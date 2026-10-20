import json
from tr import *
S = json.load(open("../yday/seat.json"))["launches"]
P = {p["pid"]: p for p in json.load(open("../oct8_pools.json"))["pools"]}
picks = [S[5], S[30]]
for r in picks:
    p = P[r["pid"]]; d = p["from"].lower(); L = r["block"]; pull = r.get("pull_block")
    print(f"== copy launch {L} deployer {d} pull {pull}")
    for n, t in touching([d], L - 600, L + 2): print("   funding/deploy:", show(n, t, L))
    if pull:
        sw = None
        for n, t in touching([d], pull, pull + 600):
            print("   after pull:", show(n, t, pull))
            if t[1] == d and t[3] > 10**17: sw = (n, t[2])
        if sw:
            ins = touching([sw[1]], sw[0] - 5, sw[0] + 80)
            print(f"   sweep {sw[1][:12]}: {sum(1 for n, t in ins if t[2] == sw[1])} transfers in, outs:", [show(n, t, sw[0]) for n, t in ins if t[1] == sw[1]][:3])
save()
