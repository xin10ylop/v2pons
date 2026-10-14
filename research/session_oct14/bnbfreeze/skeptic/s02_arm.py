"""How is the mark written? eth_simulateV1: operator approve(fresh, amount) then fresh transfers. Also time/far-future independence,
the archive flip block for our wallet, and the marking tx itself. Read-only."""
import sys, json
sys.path.insert(0, __import__("os").path.dirname(__file__))
from rpc import raw, mslot, mslot2, hx, k
TOK = "0x950e681819a68f595bb3db313346393d64f66bb5"; US = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
OP = "0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"; DEAD = "0x000000000000000000000000000000000000dead"
FRESH = "0x00000000000000000000000000000000c0ffee01"; OTHER = "0x00000000000000000000000000000000c0ffee02"
EP = sys.argv[1] if len(sys.argv) > 1 else "pn"
def a32(x): return "00" * 12 + x[2:]
def approve(to, amt): return "0x095ea7b3" + a32(to) + "%064x" % amt
def transfer(to, amt): return "0xa9059cbb" + a32(to) + "%064x" % amt
def allowance(o, s): return "0xdd62ed3e" + a32(o) + a32(s)
fb = mslot(FRESH, 0)
ov = {TOK: {"stateDiff": {fb: hx(10**12)}}, OP: {"balance": hex(10**18)}, OTHER: {"balance": hex(10**18)}, FRESH: {"balance": hex(10**18)}}
def sim(calls, block_ov=None):
    bs = {"stateOverrides": ov, "calls": calls}
    if block_ov: bs["blockOverrides"] = block_ov
    r = raw("eth_simulateV1", [{"blockStateCalls": [bs], "validation": False, "traceTransfers": False}, "latest"], EP)
    if "error" in r: return "ERR " + json.dumps(r["error"])[:200]
    out = []
    for c in r["result"][0]["calls"]:
        st = "ok" if c["status"] == "0x1" else "REVERT(" + (c.get("returnData") or "")[:12] + ")"
        logs = [(l["topics"][0][:10] + ".." + l["topics"][0][-6:], (l.get("data") or "")[:18]) for l in c.get("logs", [])]
        out.append((st, c.get("returnData", "")[-8:], logs))
    return out
print("Approval(address,address,uint256) topic0 =", "0x" + k(b"Approval(address,address,uint256)").hex())
print("\n[D] operator approve(fresh, amt) then fresh.transfer(dead, 1e8), then allowance(op,fresh) view:")
for amt in (0, 1, 2, 10, 2**256 - 2, 2**256 - 1):
    r = sim([{"from": OP, "to": TOK, "data": approve(FRESH, amt)},
             {"from": FRESH, "to": TOK, "data": transfer(DEAD, 10**8)},
             {"from": FRESH, "to": TOK, "data": allowance(OP, FRESH)}])
    print("   amt", hex(amt)[:10], "->", r if isinstance(r, str) else [(x[0], x[1]) for x in r], r[0][2] if not isinstance(r, str) else "")
print("\n[D'] NON-operator approve(fresh, MAX) then fresh transfers:")
r = sim([{"from": OTHER, "to": TOK, "data": approve(FRESH, 2**256 - 1)}, {"from": FRESH, "to": TOK, "data": transfer(DEAD, 10**8)}])
print("   ", r if isinstance(r, str) else [(x[0], x[2]) for x in r])
print("\n[E] our wallet, far-future block (number +10M, time +1 year):")
head = int(raw("eth_blockNumber", [], EP)["result"], 16)
blk = raw("eth_getBlockByNumber", [hex(head), False], EP)["result"]
for dn, dt in ((1, 1), (200000, 86400 * 3), (10_000_000, 86400 * 365)):
    r = sim([{"from": US, "to": TOK, "data": transfer(DEAD, 10**9)}], {"number": hex(head + dn), "time": hex(int(blk["timestamp"], 16) + dt)})
    print("   +%d blocks +%ds ->" % (dn, dt), r if isinstance(r, str) else r[0][0])
