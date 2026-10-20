"""A-system and B-system address sets from: crowd lists, bonding-curve list creators, loop traces (lch), B deployers/funders."""
import json, glob
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/"
b = json.load(open(D + "b_list.json"))
A = set(b["A"]); B = set(b["B"])
Asys = set(A); Bsys = set(B)
for c in json.load(open(D + "lists.json")).values():
    if c["creator"]: (Asys if c["nA"] else Bsys).add(c["creator"])
def loopaddrs(fn):
    s = set()
    for l in open(fn):
        try: d = json.loads(l)
        except Exception: continue
        for k in ("addr", "cap_to", "from"):
            if isinstance(d.get(k), str) and d[k].startswith("0x") and len(d[k]) == 42: s.add(d[k].lower())
    return s
Asys |= loopaddrs(D + "lch/loop_A.log") | loopaddrs(D + "lch/loopback_A.log")
Bsys |= loopaddrs(D + "lch/loop_B2.log") | loopaddrs(D + "lch/loop_B0605.log") | loopaddrs(D + "lch/loopback_B.log")
for f in ["0xca04a1e3", "0x069688d0", "0x5736fabe", "0xe27bfddf", "0xca847f04"]:
    try: r = json.load(open(D + "lch/tr/%s.json" % f))
    except Exception: continue
    Bsys.add(r["launch"]["deployer"])
    for h in r["back"]:
        Bsys.add(h["addr"])
        for x in h["incoming"]:
            if x["nonce"] < 50: Bsys.add(x["from"])
    for h in r["fwd"]:
        Bsys.add(h["addr"])
        for x in h["out"]:
            if x["eth"] > 0.05: Bsys.add(x["to"])
Bsys.add("0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a")
Bsys -= {""}; Asys -= {""}
