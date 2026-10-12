"""Can an outsider move the crowd's tokens into their pool (the sell's transfer)? For each template: the balances and allowances mapping slots,
found by probing balanceOf/allowance under eth_call state overrides. Then for EVERY launch's token, on the head's state: (a) transfer(pool, 1e18)
from a fresh outside address given 1e18 tokens by override (a sell lock refuses exactly this: RELAY_V3.md section 3); (b) transferFrom(outsider ->
pool, 1e18) called by SwapRouter02 with the allowance set (the router's way); (c) transfer to another fresh address. And each token's name,
symbol, decimals, totalSupply, the launch wallet's and the pool's balance (who holds the supply). Writes s03_tokens.json and s03_transfer_test.out."""
from common import *
import rpc, collections
L = json.load(open(J("s01_launches.json")))["launches"]; R = {r["token"]: r for r in json.load(open(J("s02_codes.json")))}
OUT = "0x5afe0000000000000000000000000000000c0ffe"; OUT2 = "0x5afe0000000000000000000000000000000beef1"
def mslot(key, slot): return "0x" + keccak(bytes.fromhex(word(key)) + bytes.fromhex(word(slot))).hex()
def call(to, data, ov=None, frm=None, tag="latest"):
    p = [{"to": to, "data": data, **({"from": frm} if frm else {})}, tag] + ([ov] if ov else [])
    return rpc.call("eth_call", p)
AMT = 10 ** 18; V = "0x" + word(5 * 10 ** 18)
slots = {}
for key in sorted({(r["size"], r["skel"]) for r in R.values()}):
    tok = [x["token"] for x in L if (R[x["token"]]["size"], R[x["token"]]["skel"]) == key][-1]
    bs = None
    for s in range(0, 12):
        r = call(tok, "0x70a08231" + word(OUT), {tok: {"stateDiff": {mslot(OUT, s): V}}})
        if int(r, 16) == 5 * 10 ** 18: bs = s; break
    al = None
    for s in range(0, 12):
        inner = keccak(bytes.fromhex(word(OUT)) + bytes.fromhex(word(s)))
        sl = "0x" + keccak(bytes.fromhex(word(ROUTER02)) + inner).hex()
        r = call(tok, "0xdd62ed3e" + word(OUT) + word(ROUTER02), {tok: {"stateDiff": {sl: V}}})
        if int(r, 16) == 5 * 10 ** 18: al = s; break
    slots[key] = (bs, al); print(f"template {key}: balances slot {bs}, allowances slot {al} (probed on {tok})")
res = {}; items = []
for x in L:
    tok, pool = x["token"], x["pool"]; bs, al = slots[(R[tok]["size"], R[tok]["skel"])]
    inner = keccak(bytes.fromhex(word(OUT)) + bytes.fromhex(word(al)))
    ov = {tok: {"stateDiff": {mslot(OUT, bs): "0x" + word(AMT), "0x" + keccak(bytes.fromhex(word(ROUTER02)) + inner).hex(): "0x" + word(AMT)}}}
    items += [(tok, "a", [{"from": OUT, "to": tok, "data": "0xa9059cbb" + word(pool) + word(AMT)}, "latest", ov]),
              (tok, "b", [{"from": ROUTER02, "to": tok, "data": "0x23b872dd" + word(OUT) + word(pool) + word(AMT)}, "latest", ov]),
              (tok, "c", [{"from": OUT, "to": tok, "data": "0xa9059cbb" + word(OUT2) + word(AMT)}, "latest", ov])]
    for nm, d in (("name", "0x06fdde03"), ("symbol", "0x95d89b41"), ("decimals", "0x313ce567"), ("supply", "0x18160ddd"),
                  ("bal_launcher", "0x70a08231" + word(x["from"])), ("bal_pool", "0x70a08231" + word(pool))):
        items.append((tok, nm, [{"to": tok, "data": d}, "latest"]))
C = J("s03_call_cache.jsonl"); have = {(r["tok"], r["k"]): r["r"] for r in jl(C)}
todo = [it for it in items if (it[0], it[1]) not in have]
def one_by_one(chunk):
    out = []
    for tok, k, p in chunk:
        try: out.append({"ok": rpc.call("eth_call", p)})
        except RuntimeError as e: out.append({"err": str(e)[:200]})
    return out
with open(C, "a") as f:
    for i in range(0, len(todo), 20):
        ch = todo[i:i + 20]
        d = rpc._post([{"jsonrpc": "2.0", "id": j, "method": "eth_call", "params": p} for j, (_, _, p) in enumerate(ch)]); rpc.STATS["items"] += len(ch)
        with open(rpc.LOG, "a") as lf: lf.write(json.dumps({"t": time.time(), "m": "eth_call", "n": len(ch)}) + "\n")
        d = sorted(d, key=lambda z: z["id"])
        for (tok, k, _), z in zip(ch, d):
            r = {"ok": z["result"]} if "result" in z else {"err": json.dumps(z.get("error"))[:200]}
            have[(tok, k)] = r; f.write(json.dumps({"tok": tok, "k": k, "r": r}) + "\n")
def dec_str(h):
    try:
        b = bytes.fromhex(h[2:]); o = int.from_bytes(b[:32], "big"); n = int.from_bytes(b[o:o + 32], "big"); return b[o + 32:o + 32 + n].decode(errors="replace")
    except Exception: return "?"
toks = []; cnt = collections.Counter(); fails = []
for x in L:
    tok = x["token"]; g = lambda k: have[(tok, k)]
    t = {"token": tok, "pool": x["pool"], "lb": x["lb"], "ts": x["ts"], "qs": x["qs"], "from": x["from"], "codehash": R[tok]["codehash"], "size": R[tok]["size"],
         "name": dec_str(g("name").get("ok", "0x")), "symbol": dec_str(g("symbol").get("ok", "0x")),
         "decimals": int(g("decimals")["ok"], 16) if "ok" in g("decimals") else None, "supply": int(g("supply")["ok"], 16) if "ok" in g("supply") else None,
         "bal_launcher": int(g("bal_launcher")["ok"], 16) if "ok" in g("bal_launcher") else None, "bal_pool": int(g("bal_pool")["ok"], 16) if "ok" in g("bal_pool") else None}
    for k in "abc":
        r = g(k); t["t_" + k] = "true" if r.get("ok") and int(r["ok"] or "0x0", 16) == 1 else ("empty" if r.get("ok") == "0x" else r.get("err") or r.get("ok"))
        cnt[(R[tok]["size"], k, t["t_" + k])] += 1
        if t["t_" + k] != "true": fails.append((tok, k, t["t_" + k]))
    toks.append(t)
json.dump(toks, open(J("s03_tokens.json"), "w"))
print("transfer tests (template size, test, result):"); [print(f"   {k}: {n}") for k, n in sorted(cnt.items(), key=str)]
print("failures:", fails[:10])
print("decimals:", collections.Counter(t["decimals"] for t in toks), " supply:", collections.Counter(t["supply"] for t in toks).most_common(4))
print("launch wallet's balance now (tokens):", collections.Counter(round((t["bal_launcher"] or 0) / 1e18, 3) for t in toks).most_common(6))
print("pool's balance / supply (now):", collections.Counter(round((t["bal_pool"] or 0) / t["supply"], 2) if t["supply"] else None for t in toks).most_common(6))
print("names (sample):", [(t["name"], t["symbol"]) for t in toks[-12:]])
print(rpc.STATS)
