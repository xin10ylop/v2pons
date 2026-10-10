import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); C = json.load(open("cache/postwin.json"))
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
F4 = [p for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1]
E = load_events(set(p["pid"] for p in F4))
out = {}
for g, hz in (("F4a", True), ("F4b", False)):
    ps = [p for p in F4 if p["hooks_zero"] == hz]
    ages = []; never = 0
    for p in ps:
        e = E[p["pid"]]; lb = e["adds"][0]["bn"]
        pulls = [x["bn"] for x in e["pulls"]] + [x["bn"] for x in C["ml"] if x["pid"] == p["pid"] and x["dl"] < 0]
        if pulls: ages.append(min(pulls) - lb)
        else: never += 1
    ages.sort()
    q = lambda a: [a[int(round(f * (len(a) - 1)))] for f in (.1, .25, .5, .75, .9)] if a else None
    print(g, len(ps), "pulled by head (block %d): %d, never: %d; pull age from live p10/25/50/75/90 %s" % (C["head"], len(ages), never, q(ages)))
    print("   pulled within 3000: %d, 3000-10000: %d, 10000-100000: %d, >100000: %d" % (sum(1 for a in ages if a <= 3000), sum(1 for a in ages if 3000 < a <= 10000), sum(1 for a in ages if 10000 < a <= 100000), sum(1 for a in ages if a > 100000)))
    out[g] = {"n": len(ps), "pulled_by_head": len(ages), "never": never, "age_q": q(ages)}
sw = C["f4b_swaps"]
snd = collections.Counter((x["sender"][:10], "B" if x["a0"] < 0 else "S") for x in sw)
print("F4b swaps live+3000..+12000:", len(sw), "by sender/side:", snd.most_common(12))
out["f4b_post_senders"] = snd.most_common(20)
json.dump(out, open("postwin_ana.json", "w"), indent=1)
