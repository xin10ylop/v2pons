"""Simulate a launch on the original launcher and on a copy, at latest, from a random address (eth_call with a balance state override)."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post
from eth_abi import encode
from decode import dec, TYPES, NAMES
RND = "0x" + os.urandom(20).hex(); RND2 = "0x" + os.urandom(20).hex()
def call(to, data, frm, value, override=True):
    p = [{"from": frm, "to": to, "data": data, "value": hex(value), "gas": hex(5_000_000)}, "latest"]
    if override: p.append({frm: {"balance": hex(10**21)}})
    r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": p})
    return r.get("result", r.get("error"))
def reenc(d, **kw):
    v = dict(d); v.update(kw)
    vals = [bytes.fromhex(v["salt"])] + [v[n] for n in NAMES[1:]]
    return "0x2fcb9108" + encode(TYPES, vals).hex()
def run(label, to, txin, value):
    d = dec(txin)
    print("==", label, to, "value", value / 1e18)
    print("  replay original calldata, random sender:", str(call(to, txin, RND, value))[:200])
    new = reenc(d, salt=os.urandom(32).hex(), recipient=RND2)
    print("  new salt, recipient = another random address, random sender:", str(call(to, new, RND, value))[:200])
    new2 = reenc(d, salt=os.urandom(32).hex(), recipient=RND)
    print("  new salt, recipient = sender:", str(call(to, new2, RND, value))[:200])
    print("  same, no balance override (sender has 0 ETH):", str(call(to, new2, RND, value, override=False))[:200])
    print("  same, value 0:", str(call(to, new2, RND, 0))[:200])
print("random sender", RND, "random recipient", RND2)
from chain import rpc
t = rpc("eth_getTransactionByHash", ["0x18310f611b09e1b90b9c787b556a68ae4b02f6d244311acb0b383fc4feeaa9e0"])
run("original launcher (tx 0x18310f61, a recent launch)", "0x3194e32622c5d860a0572c74edda99dcfd8fc827", t["input"], int(t["value"], 16))
t = rpc("eth_getTransactionByHash", ["0xb624262cfa369ef748332b0f00b8d4e19fb49c8a711798a2cdf85cf39437e9b0"])
run("copy 0x816d73e4 (Oct 8 14:59 copy launch)", "0x816d73e4f67b671d376973975da0afca1d738d78", t["input"], int(t["value"], 16))
# also: a copy launch's calldata sent to the original launcher
run("copy's calldata on the ORIGINAL launcher", "0x3194e32622c5d860a0572c74edda99dcfd8fc827", t["input"], int(t["value"], 16))
