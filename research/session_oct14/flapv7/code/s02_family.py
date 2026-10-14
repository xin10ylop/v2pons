"""s02: the v7 line's launches in the window. Version-7 candidates = tokens ending 8888 (impl 0x88881b6f... checked by code); fetch every
candidate's launch tx and receipt (archive-free: blocks/txs/receipts are history). Family = Portal, selector 87ef5b30, calldata 1540 B,
quote BNB, value 0.11 BNB at 2 s.f. (census strict key), plus the launch receipt's TokenVersionSet = 7 and tax 0/0, no extension.
-> data/txs_cache.jsonl (launch txs + receipts, trimmed), data/s02_family.json (one row per family launch), data/s02.out"""
import sys, os, json, collections as C, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_utils import keccak
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
def k(s): return "0x" + keccak(text=s).hex()
T = {k("TokenVersionSet(address,uint8)"): "ver", k("TokenQuoteSet(address,address)"): "quote", k("FlapTokenAsymmetricTaxSet(address,uint256,uint256)"): "atax",
     k("FlapTokenTaxSet(address,uint256)"): "tax", k("TokenExtensionEnabled(address,bytes32,address,uint8)"): "ext",
     k("TokenCurveSetV2(address,uint256,uint256,uint256)"): "curve", k("TokenDexSupplyThreshSet(address,uint256)"): "thresh",
     k("TokenBought(uint256,address,address,uint256,uint256,uint256,uint256)"): "bought", k("TokenMigratorSet(address,uint8)"): "migr",
     k("TokenCreated(uint256,address,uint256,address,string,string,string)"): "created"}
cr = []
for l in open(os.path.join(D, "creates_cache.jsonl")):
    cr.extend(json.loads(l)["rows"])
print("creates", len(cr), "blocks", min(r["b"] for r in cr), max(r["b"] for r in cr))
v7 = [r for r in cr if r["token"].endswith("8888")]
print("8888 tokens", len(v7))
cache = os.path.join(D, "txs_cache.jsonl"); have = {}
if os.path.exists(cache):
    for l in open(cache):
        j = json.loads(l); have[j["h"]] = j
need = [r["tx"] for r in v7 if r["tx"] not in have]
fh = open(cache, "a")
for i in range(0, len(need), 25):
    hs = need[i:i + 25]
    txs = rpc.batch([("eth_getTransactionByHash", [h]) for h in hs], urls=rpc.HIST)
    rcs = rpc.batch([("eth_getTransactionReceipt", [h]) for h in hs], urls=rpc.HIST)
    for h, t, rc in zip(hs, txs, rcs):
        if not t or not rc: continue
        o = {"h": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": t["input"][2:10], "clen": (len(t["input"]) - 2) // 2,
             "value": int(t["value"], 16), "type": int(t.get("type", "0x0"), 16), "gp": int(t.get("gasPrice", "0x0"), 16),
             "prio": int(t.get("maxPriorityFeePerGas", t.get("gasPrice", "0x0")), 16), "nonce": int(t["nonce"], 16), "b": int(t["blockNumber"], 16),
             "ti": int(t["transactionIndex"], 16), "status": int(rc["status"], 16), "gasUsed": int(rc["gasUsed"], 16),
             "logs": [[x["address"].lower(), x["topics"], x["data"][:2 + 64 * 6]] for x in rc["logs"]]}
        fh.write(json.dumps(o) + "\n"); have[h] = o
    if i % 500 == 0: print("txs", i, len(need), flush=True)
fh.close()
rows = []; shapes = C.Counter()
for r in v7:
    t = have.get(r["tx"])
    if not t: continue
    ev = {}
    for a, tps, d in t["logs"]:
        nm = T.get(tps[0]) if tps else None
        if a != PORTAL or not nm: continue
        w = [d[2 + 64 * i: 2 + 64 * (i + 1)] for i in range((len(d) - 2) // 64)]
        if nm in ("ver", "quote", "atax", "tax", "ext", "curve", "thresh", "migr"):
            if not w or ("0x" + w[0][-40:]) != r["token"]: continue
            if nm == "ver": ev["ver"] = int(w[1], 16)
            elif nm == "quote": ev["quote"] = "0x" + w[1][-40:]
            elif nm == "atax": ev["tax"] = f"{int(w[1],16)}/{int(w[2],16)}"
            elif nm == "tax": ev.setdefault("tax", f"{int(w[1],16)}/{int(w[1],16)}")
            elif nm == "ext": ev["ext"] = "0x" + w[2][-40:]
            elif nm == "curve": ev["r"], ev["h"], ev["k"] = int(w[1], 16), int(w[2], 16), int(w[3], 16)
            elif nm == "thresh": ev["thresh"] = int(w[1], 16)
            elif nm == "migr": ev["migr"] = int(w[1], 16)
        elif nm == "bought":
            # TokenBought(ts, token, buyer, amount, eth, fee, postPrice) in the launch tx = the creator buy
            if ("0x" + w[1][-40:]) == r["token"]:
                ev.setdefault("cbuy", []).append({"buyer": "0x" + w[2][-40:], "amount": int(w[3], 16), "eth": int(w[4], 16), "fee": int(w[5], 16)})
    val = t["value"] / 1e18
    v2 = float(f"{val:.2g}") if val > 0 else 0.0
    row = {"token": r["token"], "b": r["b"], "ts": r["ts"], "tx": r["tx"], "creator": r["creator"], "from": t["from"], "to": t["to"], "sel": t["sel"],
           "clen": t["clen"], "value": t["value"], "v2sf": v2, "prio": t["prio"], "gp": t["gp"], "type": t["type"], "nonce": t["nonce"], "ti": t["ti"],
           "status": t["status"], **ev, "name": r["name"], "symbol": r["symbol"]}
    shapes[(t["to"][:10], t["sel"], t["clen"], v2, ev.get("ver"), ev.get("tax"), ev.get("quote", "?")[:10])] += 1
    rows.append(row)
print("v7 candidate shapes (to, sel, clen, value 2sf, ver, tax, quote):")
for s, n in shapes.most_common(25): print(" ", n, s)
fam = [r for r in rows if r["to"] == PORTAL and r["sel"] == "87ef5b30" and r["clen"] == 1540 and r["v2sf"] == 0.11 and r.get("ver") == 7
       and r.get("quote", "0x" + "0" * 40) == "0x" + "0" * 40 and r.get("tax", "0/0") == "0/0" and r["status"] == 1]
print("family launches", len(fam), "ext", C.Counter(r.get("ext") for r in fam), "prio", C.Counter(r["prio"] for r in fam).most_common(6))
print("values", C.Counter(r["value"] for r in fam).most_common(5), "wallets", len(set(r["from"] for r in fam)), "nonce0", sum(1 for r in fam if r["nonce"] == 0))
json.dump({"all_v7": rows, "family": fam}, open(os.path.join(D, "s02_family.json"), "w"))
