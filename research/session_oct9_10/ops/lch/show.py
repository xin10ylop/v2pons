import json, sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FAM = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/launches.json"))["fam"]
def tg(a): return ("[" + FAM[a] + "]") if a in FAM else ""
for f in sorted(glob.glob(os.path.dirname(os.path.abspath(__file__)) + "/tr/*.json"), key=lambda f: json.load(open(f))["launch"]["b0"]) if len(sys.argv) < 2 else sys.argv[1:]:
    r = json.load(open(f)); L = r["launch"]
    print("==", L["utc"], L["family"], L["pid"][:10], "fee", L["fee"], "deployer", L["deployer"], "launch blk", L["b0"], "pull", L["pull_bn"])
    for h in r["back"]:
        inc = h["incoming"]
        if not inc: print("   back hop", h["hop"], h["addr"], "NO incoming value tx in", h["scanned_from"], "-", h["scanned_to"]); continue
        for x in inc: print("   back hop", h["hop"], h["addr"][:12], "<-", x["from"], tg(x["from"]), round(x["eth"], 4), "ETH (sender nonce %d)" % x["nonce"], x["utc"], x["bn"], x["hash"][:12])
        if "stop" in h: print("      stop:", h["stop"])
    fs = r.get("funder_sends")
    if fs:
        import collections
        c = collections.Counter(x["tag"] or ("deployer" if x["to"] == L["deployer"] else "other") for x in fs)
        print("   deployer's funder also sent %d txs: %s, total %.3f ETH" % (len(fs), dict(c), sum(x["eth"] for x in fs)))
    for h in r["fwd"]:
        for x in h["out"]: print("   fwd hop", h["hop"], h["addr"][:12], "->", x["to"], tg(x["to"]), round(x["eth"], 4), "ETH nonce", x["nonce"], x["sel"], x["utc"], x["bn"], x["hash"][:12])
        if not h["out"]: print("   fwd hop", h["hop"], h["addr"][:12], "no outgoing tx in", h["scanned"])
    ci = r.get("collector_in")
    if ci:
        import collections
        c = collections.Counter(x["tag"] or "other" for x in ci)
        print("   collector received %d transfers +-100 blocks: %s total %.3f ETH" % (len(ci), dict(c), sum(x["eth"] for x in ci)))
