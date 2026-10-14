"""Step 4: per-pool records. Classes of a swap's transaction: fleet (tx.to is one of the fleet routers), sentinel (0xe71a69f4),
r57 (0x57ee6646, 6e-5 ETH via the Universal Router in every pool), other (anyone else). Writes s04_pools.json."""
import collections, datetime
from common import *
from common import _glob
FLEET_ROUTERS = {"0x628bd69ecbc135cdda02ffd6d6db918f5cd835ce", "0x543282f890f93e6961a6d3cbcd9e003cc88dcb3c"}
SENTINEL = "0xe71a69f434a719cd5afa411568b69716aab3b84a"; R57 = "0x57ee6646fe8748dc8c10ac96caae7ce2373ede5d"
def klass(t):
    if t is None: return "?"
    if t["to"] in FLEET_ROUTERS: return "fleet"
    if t["f"] == SENTINEL: return "sentinel"
    if t["f"] == R57: return "r57"
    return "other"
if __name__ == "__main__":
    d = jload("s01_inits.json"); dr = sorted(d["direct"], key=lambda c: c["block"])
    bts = {int(k): v for k, v in jload("s01_blockts.json").items()}
    head = jload("s02_head.json")["head"]
    ev = load_events(); tx = load_txs()
    byp = collections.defaultdict(list)
    for r in ev: byp[r["pid"]].append(r)
    pools = []; miss = 0
    for c in dr:
        L = c["block"]; rows = sorted(byp[c["pid"]], key=lambda r: (r["bn"], r["li"]))
        adds = [r for r in rows if r["t"] == "M" and ml_fields(r)["dl"] > 0]
        pulls = [r for r in rows if r["t"] == "M" and ml_fields(r)["dl"] < 0]
        add = adds[0] if adds else None
        p = dict(pid=c["pid"], L=L, ts=bts[L], launcher=c["from"], token=c["token"], init_nonce=c["nonce"], sqrt0=c["sqrt0"], tick0=c["tick0"],
                 init_tx=c["tx"])
        if add:
            m = ml_fields(add); t = tx.get(add["tx"]) or {}
            p.update(add_bn=add["bn"], add_off=add["bn"] - L, add_tx=add["tx"], add_from=t.get("f"), add_to=t.get("to"), add_value=t.get("v"),
                     add_sel=t.get("s"), add_il=t.get("il"), add_nonce=t.get("n"), tl=m["tl"], tu=m["tu"], liq=m["dl"], n_adds=len(adds))
        if pulls:
            t = tx.get(pulls[0]["tx"]) or {}
            p.update(pull_bn=pulls[0]["bn"], pull_off=pulls[0]["bn"] - L, pull_tx=pulls[0]["tx"], pull_from=t.get("f"), pull_ti=pulls[0]["ti"], pull_li=pulls[0]["li"])
        sw = []
        for r in rows:
            if r["t"] != "S": continue
            if pulls and (r["bn"], r["li"]) > (pulls[0]["bn"], pulls[0]["li"]): break
            s = swap_fields(r); t = tx.get(r["tx"])
            if t is None: miss += 1
            sw.append(dict(o=r["bn"] - L, bn=r["bn"], li=r["li"], ti=r["ti"], a0=s["a0"], a1=s["a1"], fee=s["fee"], sqrt=s["sqrt"], liq=s["liq"], tick=s["tick"],
                           k=klass(t), f=(t or {}).get("f"), to=(t or {}).get("to"), n=(t or {}).get("n"), tx=r["tx"], gp=(t or {}).get("gp")))
        p["swaps"] = sw
        fb = [s for s in sw if s["k"] == "fleet" and s["a0"] < 0]
        p["T"] = fb[0]["o"] if fb else None
        pools.append(p)
    for fp in _glob.glob(os.path.join(HERE, "s04_pools_*_cache.jsonl")): os.remove(fp)
    k = 0; size = 0
    for p in pools:
        line = json.dumps(p, separators=(",", ":")) + "\n"
        if size + len(line) > 1_800_000: k += 1; size = 0
        with open(os.path.join(HERE, f"s04_pools_{k:02d}_cache.jsonl"), "a") as f: f.write(line)
        size += len(line)
    jdump(dict(head=head), "s04_head.json")
    print("pools", len(pools), "swaps without tx", miss)
