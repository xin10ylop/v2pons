"""eth_call at latest: launch(...) on the original launcher from a fresh random address, with calldata of the most recent real launch in launcher_txs.json."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
from chain import post, rpc
from eth_abi import encode, decode
from decode import dec, TYPES, NAMES
LCH = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
T = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/launcher_txs.json"))
h, t = max(T.items(), key=lambda kv: kv[1]["bn"])
RND = "0x" + os.urandom(20).hex()
print("template launch tx", h, "block", t["bn"], "sender", t["from"], "nonce", t["nonce"], "value", t["value"] / 1e18)
d = dec(t["input"]); print("decoded:", {k: (v if not isinstance(v, str) or len(v) < 70 else v[:70]) for k, v in d.items()})
print("random sender", RND, "latest nonce/balance:", int(rpc("eth_getTransactionCount", [RND, "latest"]), 16), int(rpc("eth_getBalance", [RND, "latest"]), 16))
def call(data, value, override=True, frm=RND):
    p = [{"from": frm, "to": LCH, "data": data, "value": hex(value), "gas": hex(5_000_000)}, "latest"]
    if override: p.append({frm: {"balance": hex(10**21)}})
    r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": p})
    if "result" in r: return "SUCCESS " + r["result"]
    e = r["error"]; msg = e.get("message"); dat = e.get("data")
    if dat and dat.startswith("0x08c379a0"): msg += " | reason=" + decode(["string"], bytes.fromhex(dat[10:]))[0]
    return "REVERT/ERR " + str(msg) + (" data=" + dat[:20] if dat else "")
def reenc(**kw):
    v = dict(d); v.update(kw)
    return "0x2fcb9108" + encode(TYPES, [bytes.fromhex(v["salt"])] + [v[n] for n in NAMES[1:]]).hex()
def show(label, res):
    print(" -", label, "->", res[:300])
    if res.startswith("SUCCESS"):
        tok, pid, tid = decode(["address", "bytes32", "uint256"], bytes.fromhex(res[10:]))
        print("     decoded return: token", tok, "poolId 0x" + pid.hex()[:16] + "..", "position NFT id", tid)
v = t["value"]
show("A exact replay, sender has 0 ETH (no override)", call(t["input"], v, override=False))
show("B exact replay, sender given 1000 ETH via state override", call(t["input"], v))
# why B reverts: predicted token address for the same salt/args already has code (CREATE2 collision)?
pred = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": LCH, "data": "0x54bc5062" + encode(["bytes32", "string", "string", "string", "uint256"], [bytes.fromhex(d["salt"]), d["name"], d["symbol"], d["s3"], d["u84"]]).hex()}, "latest"]})
pa = "0x" + pred["result"][-40:]; pc = rpc("eth_getCode", [pa, "latest"])
print("   predictTokenAddress(salt,name,symbol,uri,supply) of the template =", pa, "; code there now:", (len(pc) - 2) // 2, "bytes")
lg = rpc("eth_getTransactionReceipt", [h]); toks = {x["address"].lower() for x in lg["logs"]}
print("   the template's real token (from its receipt logs) is among:", pa.lower() in toks)
salt = os.urandom(32).hex()
show("C new salt, recipient = random sender, value = template value, 1000 ETH override", call(reenc(salt=salt, recipient=RND), v))
show("D same as C but recipient = a different random address", call(reenc(salt=os.urandom(32).hex(), recipient="0x" + os.urandom(20).hex()), v))
show("E same as C, value 0", call(reenc(salt=os.urandom(32).hex(), recipient=RND), 0))
show("F same as C, recipient = 0x0", call(reenc(salt=os.urandom(32).hex(), recipient="0x" + "00" * 20), v))
show("G same as C, sent from 0x000...dEaD with no override but gas price 0 (pure EVM check)", call(reenc(salt=os.urandom(32).hex(), recipient=RND), v, override=False, frm="0x000000000000000000000000000000000000dEaD"))
