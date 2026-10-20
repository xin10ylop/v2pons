"""Re-derive the freeze rule independently (read-only eth_call / eth_simulateV1 with state overrides)."""
import sys, json
sys.path.insert(0, __import__("os").path.dirname(__file__))
from rpc import raw, mslot, mslot2, hx, k
TOK = "0x950e681819a68f595bb3db313346393d64f66bb5"; US = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
DEAD = "0x000000000000000000000000000000000000dead"; FRESH = "0x00000000000000000000000000000000c0ffee01"
OTHER = "0x00000000000000000000000000000000c0ffee02"
EP = sys.argv[1] if len(sys.argv) > 1 else "pn"
head = int(raw("eth_blockNumber", [], EP)["result"], 16); B = hex(head)
print("endpoint", EP, "head", head)
s6 = raw("eth_getStorageAt", [TOK, "0x6", B], EP)["result"]; OP = "0x" + s6[-40:]
print("slot6", s6, "-> operator", OP)
bal = int(raw("eth_call", [{"to": TOK, "data": "0x70a08231" + "00" * 12 + US[2:]}, B], EP)["result"], 16)
print("balanceOf(us)", bal)
# locate balance mapping slot
bslot = None
for s in range(0, 12):
    v = int(raw("eth_getStorageAt", [TOK, mslot(US, s), B], EP)["result"], 16)
    if v == bal: bslot = s; break
print("balance mapping slot", bslot)
aslot_us = mslot2(OP, US, 1)
araw = int(raw("eth_getStorageAt", [TOK, aslot_us, B], EP)["result"], 16)
aview = raw("eth_call", [{"to": TOK, "data": "0xdd62ed3e" + "00" * 12 + OP[2:] + "00" * 12 + US[2:]}, B], EP)
print("raw allowance[op][us] (slot keccak(us.keccak(op.1)))", hex(araw), "odd" if araw & 1 else "even")
print("allowance(op,us) view", aview.get("result", aview.get("error")))
def xfer(frm, amt, ov=None, block=B, to=DEAD):
    data = "0xa9059cbb" + "00" * 12 + to[2:] + "%064x" % amt
    p = [{"from": frm, "to": TOK, "data": data, "gas": hex(500000)}, block]
    if ov: p.append(ov)
    r = raw("eth_call", p, EP)
    if "error" in r: return "REVERT " + json.dumps(r["error"])[:120]
    return "ok " + r["result"][:20]
print("\n[A] head: transfer(dead, 1%) from us:", xfer(US, bal // 100))
print("[A] head: transfer(pair, 1%) from us:", xfer(US, bal // 100, to="0x2de2620b04a0382390b18441cd033da7b798e57e"))
print("\n[B] our wallet, override allowance[op][us] parity:")
for v in (0, 2, 2**256 - 2, 1, 3, 2**256 - 1, 2**255):
    print("   value", hex(v)[:12] + ("..." if v > 2**40 else ""), "odd" if v & 1 else "even", "->", xfer(US, bal // 100, {TOK: {"stateDiff": {aslot_us: hx(v)}}}))
print("   slot6 zeroed (allowance left as is) ->", xfer(US, bal // 100, {TOK: {"stateDiff": {"0x" + "%064x" % 6: hx(0)}}}))
print("\n[C] fresh address with an overridden balance:")
fb = mslot(FRESH, bslot); fa = mslot2(OP, FRESH, 1)
for v in (0, 1, 2, 7, 2**256 - 1, 2**256 - 2):
    print("   allowance[op][fresh]", "odd" if v & 1 else "even", hex(v)[:10], "->", xfer(FRESH, 10**8, {TOK: {"stateDiff": {fb: hx(10**12), fa: hx(v)}}}))
# allowance from a NON-operator to fresh (odd): must not matter if the gate is operator-specific
na = mslot2(OTHER, FRESH, 1)
print("   allowance[other][fresh]=MAX (odd), op allowance 0 ->", xfer(FRESH, 10**8, {TOK: {"stateDiff": {fb: hx(10**12), na: hx(2**256 - 1)}}}))
