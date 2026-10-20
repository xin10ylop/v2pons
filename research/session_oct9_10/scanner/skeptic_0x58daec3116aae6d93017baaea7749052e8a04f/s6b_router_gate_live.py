"""Skeptic step 6b: the router-gate test on still-live v3.0 pools (read-only eth_call, no transaction): the bot's buy calldata (c1120e3d) with a small
value, minOut 1, from an unrelated address; and the same with minOut = 10**40 (must revert on the minOut check if the call is reached)."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc
R = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
L0 = 25725498245903809899643
TOK = ["0x0e5c3b9b7802556db82340c97d88c8e608de729f", "0x1e9f708655801ba4a165b70719893e2365ff4e73", "0x1cbd67cad87cb2cb017d12c059bb2e66197b6058"]
def call(frm, tok, minout, value=10**15):
    dl = int(time.time()) + 600
    data = ("0xc1120e3d" + "0000000000000000000000008876789976decbfcbbbe364623c63652db8c0904" + "0000000000000000000000008366a39cc670b4001a1121b8f6a443a643e40951"
            + f"{int(tok[2:],16):064x}" + f"{L0 // 4:064x}" + f"{minout:064x}" + f"{int(frm[2:],16):064x}" + f"{dl:064x}" + f"{10000:064x}" + f"{200:064x}" + "0" * 64)
    try:
        r = rpc("eth_call", [{"from": frm, "to": R, "value": hex(value), "data": data, "gas": hex(900000)}, "latest", {frm: {"balance": hex(10**19)}}])
        return "ok " + r[:130]
    except Exception as e: return "revert " + str(e)[:160]
out = {}
for tok in TOK:
    for frm in ("0x00000000000000000000000000000000000dead1", "0xdd9200659e6cfe60e93914c6ae24a728bc55c0f8"):
        out[f"{tok}|{frm}"] = {"minout_1": call(frm, tok, 1), "minout_huge": call(frm, tok, 10**40)}
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s6b_router_gate_live.json", "w"), indent=1)
