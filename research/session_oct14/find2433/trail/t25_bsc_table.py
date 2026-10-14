"""Table of the operator's BSC line (t22 rows): per launch the time, value, sender and nonce, the bot router's first buy (blocks after the
launch, BNB), every outside buy before it (who, size, block), the bot's buys and BNB in the window, the pull; then the per-hour summary."""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import jl, J, pct
R = "0x07cb61618b69234d954022ff738a015548715533"
rows = sorted({r["pid"]: r for r in jl(J("t22_pools_cache.jsonl"))}.values(), key=lambda r: r["L"])
tsc = {r["b"]: r["ts"] for r in jl(J("t25_ts_cache.jsonl"))}
need = [r["L"] for r in rows if r["L"] not in tsc]
txc = {r["h"]: r for r in jl(J("t25_tx_cache.jsonl"))}
with open(J("t25_ts_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 10):
        for b, x in zip(need[i:i + 10], xrpc.batch("bsc", "eth_getBlockByNumber", [[hex(b), False] for b in need[i:i + 10]], n=10)):
            tsc[b] = int(x["timestamp"], 16); f.write(json.dumps({"b": b, "ts": tsc[b]}) + "\n")
out = []; early_tx = []
for r in rows:
    sw = sorted(r["swaps"], key=lambda s: (s["b"], s["ix"]))
    bot = [s for s in sw if s["to"] == R and s["a0"] < 0]
    fb = bot[0] if bot else None
    pre = [s for s in sw if s["a0"] < 0 and s["to"] != R and (fb is None or (s["b"], s["ix"]) < (fb["b"], fb["ix"]))]
    sells = [s for s in sw if s["a0"] > 0]
    for s in pre: early_tx.append(s["tx"])
    out.append((r, sw, bot, fb, pre, sells))
need = [h for h in set(early_tx) if h not in txc]
with open(J("t25_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 10):
        for x in xrpc.batch("bsc", "eth_getTransactionByHash", [[h] for h in need[i:i + 10]], n=10):
            if x:
                y = {"h": x["hash"], "f": x["from"].lower(), "to": (x.get("to") or "").lower(), "sel": x["input"][:10], "nonce": int(x["nonce"], 16), "gp": int(x["gasPrice"], 16)}
                txc[y["h"]] = y; f.write(json.dumps(y) + "\n")
print("launch(UTC)      block      sender     nonce value     gas       botFirst(+blk,BNB)  outside-before-bot (+blk BNB who nonce)                  botBuys botBNB  sells pull+")
fbs = []; per_h = collections.Counter(); vals = collections.Counter(); pres = collections.Counter()
for r, sw, bot, fb, pre, sells in out:
    t = tsc[r["L"]]; per_h[time.strftime("%m-%d %H", time.gmtime(t))] += 1; vals[(int(r["v"]) / 1e18, r["gas"], r["sqrtP"])] += 1
    fbo = (fb["b"] - r["L"], round(-fb["a0"] / 1e18, 4)) if fb else None
    if fb: fbs.append(fb["b"] - r["L"])
    pr = [(s["b"] - r["L"], round(-s["a0"] / 1e18, 5), txc.get(s["tx"], {}).get("f", "?")[:10], txc.get(s["tx"], {}).get("nonce")) for s in pre]
    for p in pr: pres[p[2]] += 1
    print("%s %d %s %3d %10.7f %8d %-18s %-60s %4d %7.2f %4d %s" % (time.strftime("%m-%d %H:%M:%S", time.gmtime(t)), r["L"], r["from"][:10], r["nonce"], int(r["v"]) / 1e18, r["gas"], fbo, pr[:3],
          len(bot), sum(-s["a0"] for s in bot) / 1e18, len(sells), r["pull"] and r["pull"] - r["L"]))
print("\nlaunches", len(out), "first", time.strftime("%m-%d %H:%M", time.gmtime(tsc[out[0][0]["L"]])), "last", time.strftime("%m-%d %H:%M", time.gmtime(tsc[out[-1][0]["L"]])))
print("families (value, gas limit, sqrtP):", vals.most_common())
print("bot first buy, blocks after launch p10/p50/p90:", pct(fbs, .1), pct(fbs, .5), pct(fbs, .9), "min", min(fbs) if fbs else None)
print("pull after launch p10/p50/p90:", pct([r["pull"] - r["L"] for r, *_ in out if r["pull"]], .1), pct([r["pull"] - r["L"] for r, *_ in out if r["pull"]], .5), pct([r["pull"] - r["L"] for r, *_ in out if r["pull"]], .9))
print("launches per hour:", sorted(per_h.items()))
print("outside wallets buying before the bot:", pres.most_common(12))
