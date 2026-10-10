import sys, json, collections, statistics as st
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
keys = ["create|60808060|3740|2500|25|true", "create|60808060|3708|2500|25|true"]
mine = set(pid for k in keys for pid in F[k]["pids"])
crowd = ["0x9909d019032fbaa169ecad03b38c17d8a2a9d1f8", "0x66a51cca839825efff7af7cb7b41146d711e9c25", "0xc56a36ee45fc84aa9ad6968c6e1b8a37e5b378c2", "0x9f6550ebe9ffd8971718eb2156ee181c28999eab",
         "0xf7edc24925a50cb190966000ad9a642eae9aec21", "0xa753b8eca9543e6354e84eab4116127d847fb5de", "0x0b410a5f0594fd4500acccd4b97b91da8987c40c", "0x8c80ee5efb297c1e797c87427fac0c44074e96ea",
         "0xc735c70d9d484f2e2bb6c01b626f9b6d92e1122a", "0xb8c4eeab9ff0dada19d108385ab84da4d8beb435", "0x83ff8e81fd29de9bfc8cb312f6734f33e385eed4", "0x69f42771fa050528478705c206309461fc7c3543",
         "0xcc3bb9613fdee20ec8fae6f61333819f2d2c4bc1", "0x6b954abc45ab0e1b8fa72a08641bbad25cd7c2d7"]
# where else do these wallets appear (first-8 swap txs anywhere in the census)
where = collections.defaultdict(lambda: collections.Counter())
for h, t in T.items():
    if t["from"] in crowd and "swap" in (t.get("kind") or []):
        for pid, kind, rank in t.get("refs") or []:
            if kind == "swap":
                where[t["from"]]["mine" if pid in mine else (P[pid]["known"] + ":" + P[pid]["family"][:20] if pid in P else "?")] += 1
for w in crowd:
    print(w[:10], dict(where[w].most_common(6)))
# trap test: dev dump (first sell >= 1 ETH) offset vs an outsider buy (not crowd, not dust, not launch) before the first crowd buy
E = load_events(mine)
rows = []
cs = set(crowd)
for pid in sorted(mine, key=lambda p: P[p]["launch_block"]):
    pl = Pool(P[pid], E.get(pid), T, M)
    bs = pl.buys()
    fc = next((x for x in bs if x["from"] in cs), None)
    lim = (fc["bn"], fc["li"]) if fc else (pl.b0 + 3001, 0)
    outs = [x for x in bs if (x["bn"], x["li"]) < lim and x["from"] not in cs and x["from"] != DUST]
    dump = next((x for x in pl.seq if not x["buy"] and x["eth"] >= int(1e18)), None)
    rows.append({"pid": pid[:12], "first_crowd_rel": fc["bn"] - pl.b0 if fc else None, "outsiders": [(x["bn"] - pl.b0, round(x["eth"] / 1e18, 6), x["from"][:10] if x["from"] else None, x["to"][:10] if x["to"] else None) for x in outs],
                 "dump_rel": dump["bn"] - pl.b0 if dump else None, "dump_eth": round(dump["eth"] / 1e18, 3) if dump else None, "dump_from": dump["from"] if dump else None,
                 "eth_buys_before_dump": round(sum(x["eth"] for x in bs if not dump or x["bn"] < dump["bn"]) / 1e18, 3)})
for r in rows: print(r)
json.dump({"where": {w: dict(where[w]) for w in crowd}, "rows": rows}, open("fam4_crowd.json", "w"), indent=1)
