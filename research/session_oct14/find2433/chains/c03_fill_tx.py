"""Read the two Ethereum fill transactions: input, all logs, and a call trace if the public endpoint offers one (read-only)."""
import sys, json; sys.path.insert(0, '.'); import rpcx
rpcx.ALLOWED |= {"debug_traceTransaction", "trace_transaction"}
F = ["0xaa30eaf45ee3768e8061a2032344ac005e886abd840e8472396c79d47c9ceb05", "0x015d516d4aa6acda5fdaaad43981ce7e482a130192912483847aa963bcdd25a5"]
out = {}
for h in F:
    t = rpcx.call("eth_h", "eth_getTransactionByHash", [h]); r = rpcx.call("eth_h", "eth_getTransactionReceipt", [h])
    print("FILL", h, "block", int(t["blockNumber"], 16), "from", t["from"], "to", t["to"], "status", r["status"], "gasUsed", int(r["gasUsed"], 16))
    print("  input", t["input"][:1400])
    for l in r["logs"]:
        print("  LOG", l["address"], [x[:66] for x in l["topics"]], l["data"][:400])
    tr = None
    for ep in ["eth_h", "eth_d", "eth_m"]:
        for m, p in [("trace_transaction", [h]), ("debug_traceTransaction", [h, {"tracer": "callTracer"}])]:
            try:
                tr = rpcx.call(ep, m, p); print("  trace via", ep, m); break
            except Exception as e: print("  trace fail", ep, m, str(e)[:100])
        if tr: break
    out[h] = {"tx": t, "receipt": r, "trace": tr}
json.dump(out, open("c03_fill_txs.json", "w"), indent=1)
def walk(c, d=0):
    v = int(c.get("value", "0x0"), 16)
    print("  " * d, c.get("type"), c.get("from"), "->", c.get("to"), "val %.6f" % (v / 1e18), c.get("input", "")[:10], c.get("error", ""))
    for x in c.get("calls", []) or []: walk(x, d + 1)
for h, o in out.items():
    tr = o["trace"]
    if isinstance(tr, dict): print("CALLTREE", h); walk(tr)
    elif isinstance(tr, list):
        print("TRACE", h)
        for x in tr:
            a = x.get("action", {}); print("  ", x.get("type"), a.get("from"), "->", a.get("to"), "val %.6f" % (int(a.get("value", "0x0"), 16) / 1e18), (a.get("input") or "")[:10], x.get("traceAddress"))
