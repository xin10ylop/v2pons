"""Can our relay buy AND sell on an F4b pool (hook code 1578ffdd, afterSwap + beforeAddLiquidity)? eth_call only (nothing is sent), at the latest
state, with state overrides: the FlipRelay runtime (contracts/FlipRelay.json, immutables pm = PoolManager, owner = OWNER) at RELAY_AT with 1 ETH;
(1) buy 0.0058 ETH; (2) the token's balance slot found by probing balanceOf under storage overrides; (3) sell that many tokens.
Control: the same on a hookless pool (F1, never pulled). Results in honeypot_sim.json."""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import post, PM
from load import *
from eth_utils import keccak
OWNER = "0x" + "c0" * 20; RELAY_AT = "0x" + "f1" * 20
art = json.load(open("/home/user/v2pons/contracts/FlipRelay.json"))
code = bytearray.fromhex(art["deployedBytecode"][2:])
ids = sorted(art["immutableReferences"], key=int); assert len(ids) == 2
for ast_id, val in zip(ids, (PM, OWNER)):
    for r in art["immutableReferences"][ast_id]: code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
RELAY_CODE = "0x" + code.hex()
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x[2:].lower().zfill(64)
def call(to, data, ov, frm=OWNER):
    r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"from": frm, "to": to, "data": data, "gas": hex(3_000_000)}, "latest", ov]})
    return r.get("result"), r.get("error")
def keyw(p): return w("0x" + "0" * 40) + w(p["token"]) + w(p["fee"]) + w(p["tick_spacing"]) + w(p["hooks"])
SEL_BUY = "0x" + keccak(text="buy((address,address,uint24,int24,address),uint256,uint256,uint256)").hex()[:8]
SEL_SELL = "0x" + keccak(text="sell((address,address,uint24,int24,address),uint256,uint256)").hex()[:8]
assert SEL_BUY == "0x5ed06f60" and SEL_SELL == "0x137f1fdd", (SEL_BUY, SEL_SELL)
P = load_pools(); C = json.load(open("cache/postwin.json"))
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
E = load_events()
def alive(pid):
    e = E[pid]
    return not e["pulls"] and not any(x["pid"] == pid and x["dl"] < 0 for x in C["ml"])
F4b = [p for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["fee"] == 500 and p["tick_spacing"] == 1 and not p["hooks_zero"]]
tests = [p for p in F4b if alive(p["pid"])][:3]
ctl = [p for p in P.values() if p["calldata_len"] == 54500][:1]
out = []
for p in tests + ctl:
    ov = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}}
    res, err = call(RELAY_AT, SEL_BUY + keyw(p) + w(int(0.0058e18)) + w(0) + w(0), ov)
    row = {"pid": p["pid"], "hooks": p["hooks"], "token": p["token"], "buy_out": int(res, 16) if res else None, "buy_err": err}
    toks = int(res, 16) if res else 10**18
    slot = None
    for s in list(range(0, 12)) + [51, 52, 101, 102, 201]:
        key = "0x" + keccak(bytes.fromhex(w(RELAY_AT) + w(s))).hex()
        r2, e2 = call(p["token"], "0x70a08231" + w(RELAY_AT), {p["token"]: {"stateDiff": {key: "0x" + w(toks)}}})
        if r2 and int(r2, 16) == toks: slot = s; break
    row["balance_slot"] = slot
    if slot is not None:
        key = "0x" + keccak(bytes.fromhex(w(RELAY_AT) + w(slot))).hex()
        ov2 = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}, p["token"]: {"stateDiff": {key: "0x" + w(toks)}}}
        r3, e3 = call(RELAY_AT, SEL_SELL + keyw(p) + w(0) + w(0), ov2)
        row["sell_out_wei"] = int(r3, 16) if r3 else None; row["sell_err"] = e3
        row["round_trip"] = (int(r3, 16) / 0.0058e18 - 1) if r3 and res else None
    out.append(row); print(json.dumps(row)[:600])
json.dump(out, open("honeypot_sim.json", "w"), indent=1)
