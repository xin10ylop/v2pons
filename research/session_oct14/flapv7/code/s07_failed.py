"""s07: failed attempts. A reverted transaction leaves no log, so for every sender EOA of an outsider / crowd buy (tx.from), every
transaction it sent in its window is found by bisecting its archive nonce (eth_getTransactionCount at past blocks, sentio/blockmachine):
window = [its first family buy block, its last move-out block] if it exited fully, else [first buy, head]. Each nonce step is located to a
block, the block's transactions are read, and the sender's transaction there is classified by status and target (Portal / the token /
a router seen in the family / other). Senders with more than CAP transactions in the window are not enumerated (counted apart).
-> data/s07_failed.json, data/blocks_cache.jsonl (only the matching txs are kept)"""
import sys, os, json, collections as C, threading, queue, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 60
S = json.load(open(os.path.join(D, "s05_holders.json"))); HEAD = json.load(open(os.path.join(D, "s06_head.json")))["head"]
toks = set(o["token"] for o in S["rows"])
routers = set()
for o in S["rows"]:
    for b in o["buys"]:
        if b["fp"][:10] != PORTAL[:10]: routers.add(b["fp"].split(":")[0])
# per sender EOA: windows
W = {}
for o in S["rows"]:
    grp = "outsider" if o["cls"] == ["outsider"] else ("crowd" if "crowd" in o["cls"] else None)
    if not grp: continue
    still = o["first_out"] is None or (o["bal_logs"] > 0)
    last = HEAD if still else max(x["b"] for x in o["outs"])
    for b in o["buys"]:
        e = b["from"]
        w = W.setdefault(e, {"eoa": e, "grp": set(), "lo": b["b"], "hi": last, "tokens": set(), "early": False})
        w["grp"].add(grp); w["lo"] = min(w["lo"], b["b"]); w["hi"] = max(w["hi"], last); w["tokens"].add(o["token"])
        if b["off"] < 100: w["early"] = True
print("senders", len(W), C.Counter(tuple(sorted(w["grp"])) for w in W.values()), flush=True)
def nonce(a, blk):
    return int(rpc.call("eth_getTransactionCount", [a, hex(blk)], urls=rpc.HIST), 16)
bcache = os.path.join(D, "blocks_cache.jsonl"); BC = {}
if os.path.exists(bcache):
    for l in open(bcache):
        try: j = json.loads(l); BC[(j["b"], j["from"])] = j["txs"]
        except Exception: pass
lk = threading.Lock(); bfh = open(bcache, "a")
def txs_from(blk, a):
    if (blk, a) in BC: return BC[(blk, a)]
    B = rpc.call("eth_getBlockByNumber", [hex(blk), True], urls=rpc.HIST)
    out = []
    for t in B["transactions"]:
        if t["from"].lower() != a: continue
        rc = rpc.call("eth_getTransactionReceipt", [t["hash"]], urls=rpc.HIST)
        inp = t["input"].lower()
        out.append({"h": t["hash"], "b": blk, "nonce": int(t["nonce"], 16), "to": (t.get("to") or "").lower(), "sel": inp[2:10],
                    "status": int(rc["status"], 16), "gasUsed": int(rc["gasUsed"], 16), "gas": int(t["gas"], 16),
                    "has_family_token": [x for x in toks if x[2:] in inp]})
    with lk:
        BC[(blk, a)] = out; bfh.write(json.dumps({"b": blk, "from": a, "txs": out}) + "\n"); bfh.flush()
    return out
res = {}; Q = queue.Queue()
for e in W: Q.put(e)
def work():
    while True:
        try: e = Q.get_nowait()
        except queue.Empty: return
        w = W[e]
        try:
            lo, hi = w["lo"] - 1, w["hi"]
            n0, n1 = nonce(e, lo), nonce(e, hi)
            r = {"eoa": e, "grp": sorted(w["grp"]), "early": w["early"], "lo": lo, "hi": hi, "n_tx": n1 - n0, "txs": []}
            if n1 - n0 > CAP: r["skipped"] = True
            else:
                # locate each nonce step: smallest block B in (lo, hi] with nonce(B) >= k + 1 for k in [n0, n1)
                cache = {lo: n0, hi: n1}
                def nn(b):
                    if b not in cache: cache[b] = nonce(e, b)
                    return cache[b]
                blocks = set()
                for k in range(n0, n1):
                    a_, b_ = lo, hi
                    while b_ - a_ > 1:
                        m = (a_ + b_) // 2
                        if nn(m) >= k + 1: b_ = m
                        else: a_ = m
                    blocks.add(b_)
                for blk in sorted(blocks): r["txs"] += txs_from(blk, e)
        except Exception as ex:
            r = {"eoa": e, "grp": sorted(w["grp"]), "error": str(ex)[:200]}
        with lk:
            res[e] = r
            if len(res) % 25 == 0: print("senders done", len(res), flush=True)
th = [threading.Thread(target=work) for _ in range(6)]
for t in th: t.start()
for t in th: t.join()
json.dump({"head": HEAD, "cap": CAP, "routers": sorted(routers), "res": res}, open(os.path.join(D, "s07_failed.json"), "w"))
def tgt(t):
    if t["to"] == PORTAL: return "portal"
    if t["to"] in toks: return "token"
    if t["to"][:10] in routers: return "router"
    return "other"
for grp in ("outsider", "crowd"):
    for early in (True, False):
        g = [r for r in res.values() if grp in r.get("grp", []) and r.get("early") == early]
        en = [r for r in g if not r.get("skipped") and "error" not in r]
        allt = [t for r in en for t in r["txs"]]
        fails = [t for t in allt if t["status"] == 0]
        print(f"\n{grp} {'bought<+100' if early else 'bought>=+100'}: senders {len(g)}, enumerated {len(en)}, skipped(>{CAP} txs) {sum(1 for r in g if r.get('skipped'))}, errors {sum(1 for r in g if 'error' in r)}")
        print("   txs in windows", len(allt), "by target/status", C.Counter((tgt(t), t["status"]) for t in allt))
        print("   FAILED txs touching the Portal/token/router or a family token in calldata:",
              [(r["eoa"], t["h"], tgt(t), t["sel"]) for r in en for t in r["txs"] if t["status"] == 0 and (tgt(t) != "other" or t["has_family_token"])][:20])
        print("   failed (any target):", len(fails), "senders with a failure:", len(set(r["eoa"] for r in en if any(t["status"] == 0 for t in r["txs"]))))
