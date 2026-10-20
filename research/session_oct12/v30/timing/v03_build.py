"""Per 3.0 pool: T (block of the bot router's first buy), the bot's buys/ETH, the pull, and every buy before T with its sender.
A bot buy = a Swap in a tx that also moves the pool token from the PoolManager into the bot router (checked against tx.to on every T)."""
import vc, json, collections
pools = json.load(open(vc.p("v01_launches.json"))); head = json.load(open(vc.p("v02_meta.json")))["head"]
mlp = json.load(open(vc.p("v02_ml.json")))["ml"]
sw = {}
for l in vc.lines("v02_swaps_cache.jsonl"):
    r = json.loads(l); sw[r["id"]] = r
botin = collections.defaultdict(set); mint = {}
for l in vc.lines("v02_botin_cache.jsonl"):
    for x in json.loads(l)["logs"]:
        tok = x["address"].lower(); frm = vc.topaddr(x["topics"][1])
        if frm == vc.Z: mint[tok] = int(x["blockNumber"], 16)
        elif frm == vc.PM: botin[tok].add(x["transactionHash"])
need = []
for r in pools:
    s = sorted(sw[r["id"]]["logs"], key=lambda x: (x["b"], x["li"]))
    bot = [x for x in s if x["tx"] in botin[r["tok"]]]
    T = bot[0]["b"] if bot else None
    pulls = sorted(x["b"] for x in mlp[r["id"]] if x["dl"] < 0)
    lim = T if T is not None else (pulls[0] if pulls else head)
    need += [x["tx"] for x in s if x["b"] <= lim and x["tx"] not in botin[r["tok"]]]
    if bot: need.append(bot[0]["tx"])
tx = vc.txs("v03_tx_cache.jsonl", need)
out = []
for r in pools:
    s = sorted(sw[r["id"]]["logs"], key=lambda x: (x["b"], x["li"]))
    bot = [x for x in s if x["tx"] in botin[r["tok"]]]
    L = r["block"]; T = bot[0]["b"] if bot else None
    pulls = sorted((x["b"], x["sender"], x["tx"]) for x in mlp[r["id"]] if x["dl"] < 0)
    mints = sorted(x["b"] for x in mlp[r["id"]] if x["dl"] > 0)
    lim = T if T is not None else (pulls[0][0] if pulls else head)
    pre = []
    for x in s:
        if x["b"] > lim or x["tx"] in botin[r["tok"]]: continue
        t = tx.get(x["tx"], {})
        pre.append({"d": x["b"] - L, "b": x["b"], "li": x["li"], "side": "buy" if x["a0"] < 0 else "sell", "eth": abs(x["a0"]) / 1e18, "from": t.get("from"), "to": t.get("to"),
                    "sel": t.get("input", "")[:10], "tx": x["tx"], "before_bot_in_T": (T is not None and x["b"] == T and x["li"] < bot[0]["li"])})
    t1 = tx.get(bot[0]["tx"], {}) if bot else {}
    bb = [x for x in bot if x["a0"] < 0]; bs = [x for x in bot if x["a0"] > 0]
    out.append(dict(L=L, t=r["t"], id=r["id"], tok=r["tok"], frm=r["frm"], nonce=r["nonce"], idx=r["idx"], T=T, d=(T - L) if T is not None else None,
                    t1_to=t1.get("to"), t1_from=t1.get("from"), t1_sel=t1.get("input", "")[:10], t1_eth=abs(bot[0]["a0"]) / 1e18 if bot else None, t1_li=bot[0]["li"] if bot else None, t1_tx=bot[0]["tx"] if bot else None,
                    nbuy=len(bb), eth_buy=sum(-x["a0"] for x in bb) / 1e18, nsell=len(bs), eth_sell=sum(x["a0"] for x in bs) / 1e18,
                    pull=pulls[0][0] if pulls else None, pull_sender=pulls[0][1] if pulls else None, pull_tx=pulls[0][2] if pulls else None, npull=len(pulls), mint=mints[0] if mints else None,
                    deploy=mint.get(r["tok"]), swaps_to=sw[r["id"]]["to"], pre=pre))
json.dump(out, open(vc.p("v03_pools.json"), "w"))
c = collections.Counter((o["T"] is not None, o["pull"] is not None) for o in out)
print("pools", len(out), "(hasT, pulled):", dict(c))
print("T tx.to:", collections.Counter(o["t1_to"] for o in out if o["T"] is not None), "sel:", collections.Counter(o["t1_sel"] for o in out if o["T"] is not None))
print("pulls per pool:", collections.Counter(o["npull"] for o in out), " pull sender:", collections.Counter(o["pull_sender"] for o in out).most_common(3))
print("deploy->L:", vc.q([o["L"] - o["deploy"] for o in out if o["deploy"]], .1), vc.q([o["L"] - o["deploy"] for o in out if o["deploy"]], .5), vc.q([o["L"] - o["deploy"] for o in out if o["deploy"]], .9), "no deploy seen", sum(1 for o in out if not o["deploy"]))
