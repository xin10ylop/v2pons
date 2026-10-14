"""Retry the flaky simulations, the stored value an operator approve writes, the archive flip block, and our marking tx. Read-only."""
import sys, json, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from rpc import raw, mslot, mslot2, hx
TOK = "0x950e681819a68f595bb3db313346393d64f66bb5"; US = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
OP = "0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"; DEAD = "0x000000000000000000000000000000000000dead"
FRESH = "0x00000000000000000000000000000000c0ffee01"; OTHER = "0x00000000000000000000000000000000c0ffee02"
def a32(x): return "00" * 12 + x[2:]
def approve(to, amt): return "0x095ea7b3" + a32(to) + "%064x" % amt
def transfer(to, amt): return "0xa9059cbb" + a32(to) + "%064x" % amt
def allowance(o, s): return "0xdd62ed3e" + a32(o) + a32(s)
ov = {TOK: {"stateDiff": {mslot(FRESH, 0): hx(10**12)}}, OP: {"balance": hex(10**18)}, OTHER: {"balance": hex(10**18)}, FRESH: {"balance": hex(10**18)}}
def sim(calls, block_ov=None):
    bs = {"stateOverrides": ov, "calls": calls}
    if block_ov: bs["blockOverrides"] = block_ov
    for i in range(8):
        r = raw("eth_simulateV1", [{"blockStateCalls": [bs], "validation": False}, "latest"], "pn")
        if "error" in r and "signer" in str(r["error"]): time.sleep(1); continue
        break
    if "error" in r: return "ERR " + json.dumps(r["error"])[:160]
    return [("ok" if c["status"] == "0x1" else "REVERT(%s)" % (c.get("returnData") or "")[:10], c.get("returnData", "")) for c in r["result"][0]["calls"]]
print("[D] operator approve(fresh, amt): fresh transfer outcome, stored allowance(op,fresh)")
for amt in (0, 1, 2, 3, 10, 2**256 - 2, 2**256 - 1):
    r = sim([{"from": OP, "to": TOK, "data": approve(FRESH, amt)}, {"from": FRESH, "to": TOK, "data": transfer(DEAD, 10**8)},
             {"from": FRESH, "to": TOK, "data": allowance(OP, FRESH)}])
    print("   amt %-10s" % hex(amt)[:10], r if isinstance(r, str) else (r[1][0], "stored=" + hex(int(r[2][1], 16))[:14]))
print("[D'] non-operator approve(fresh, amt): fresh transfer outcome, stored allowance(other,fresh)")
for amt in (1, 2**256 - 1):
    r = sim([{"from": OTHER, "to": TOK, "data": approve(FRESH, amt)}, {"from": FRESH, "to": TOK, "data": transfer(DEAD, 10**8)},
             {"from": FRESH, "to": TOK, "data": allowance(OTHER, FRESH)}])
    print("   amt %-10s" % hex(amt)[:10], r if isinstance(r, str) else (r[1][0], "stored=" + hex(int(r[2][1], 16))[:14]))
print("[D''] our wallet after operator approve(us, amt):")
for amt in (0, 2, 2**256 - 2, 1):
    r = sim([{"from": OP, "to": TOK, "data": approve(US, amt)}, {"from": US, "to": TOK, "data": transfer(DEAD, 10**9)}])
    print("   amt %-10s" % hex(amt)[:10], r if isinstance(r, str) else r[1][0])
print("[E] our wallet, far-future blocks:")
head = int(raw("eth_blockNumber", [], "pn")["result"], 16); ts = int(raw("eth_getBlockByNumber", [hex(head), False], "pn")["result"]["timestamp"], 16)
for dn, dt in ((1, 1), (200000, 86400 * 3), (10_000_000, 86400 * 365)):
    r = sim([{"from": US, "to": TOK, "data": transfer(DEAD, 10**9)}], {"number": hex(head + dn), "time": hex(ts + dt)})
    print("   +%d blocks +%d s ->" % (dn, dt), r if isinstance(r, str) else r[0][0])
print("[F] archive: transfer(dead, 1) from us around the marking block")
for ep in ("se", "bm", "pk"):
    out = []
    for b in (127550543, 127550559, 127550560, 127550561):
        r = raw("eth_call", [{"from": US, "to": TOK, "data": transfer(DEAD, 1), "gas": hex(300000)}, hex(b)], ep)
        out.append((b, "ok" if "result" in r else "REVERT" if "revert" in str(r.get("error")).lower() else str(r.get("error"))[:60]))
    print("  ", ep, out)
    if all(o[1] in ("ok", "REVERT") for o in out): break
print("[G] token logs in block 127550560:")
for ep in ("se", "bm", "pk", "pn"):
    r = raw("eth_getLogs", [{"address": TOK, "fromBlock": hex(127550560), "toBlock": hex(127550560)}], ep)
    if "result" in r: break
for l in r.get("result", []):
    tx = raw("eth_getTransactionByHash", [l["transactionHash"]], ep).get("result") or {}
    print("   tx", l["transactionHash"], "from", tx.get("from"), "to", tx.get("to"), "gasPrice", int(tx.get("gasPrice", "0x0"), 16) / 1e9, "nonce", int(tx.get("nonce", "0x0"), 16))
    print("   input", tx.get("input"))
    print("   topics", l["topics"], "data", l["data"])
