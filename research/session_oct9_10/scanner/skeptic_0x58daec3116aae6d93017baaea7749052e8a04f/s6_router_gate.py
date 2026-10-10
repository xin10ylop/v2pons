"""Skeptic step 6: is the bot router 0x1cbaf24d caller-gated? eth_call (read-only simulation, no transaction) of a v3.0 bot buy's own calldata
(c1120e3d; deadline word refreshed) at the latest state, from the original bot wallet and from an unrelated address (balance via state override)."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc
R = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
inp = ("0xc1120e3d" + "0000000000000000000000008876789976decbfcbbbe364623c63652db8c0904" + "0000000000000000000000008366a39cc670b4001a1121b8f6a443a643e40951"
       + "00000000000000000000000058216615f1d7d3419b57b6fe80d82fa51be11fc2" + "00000000000000000000000000000000000000000000015ca54060c791cd7b1e")
def call(frm, minout, value=173250000000000000):
    dl = int(time.time()) + 600
    data = inp + f"{minout:064x}" + f"{int(frm[2:],16):064x}" + f"{dl:064x}" + f"{10000:064x}" + f"{200:064x}" + "0" * 64
    try:
        r = rpc("eth_call", [{"from": frm, "to": R, "value": hex(value), "data": data, "gas": hex(900000)}, "latest", {frm: {"balance": hex(10**19)}}])
        return "ok " + r[:200]
    except Exception as e: return "revert " + str(e)[:300]
out = {}
for frm in ("0xdd9200659e6cfe60e93914c6ae24a728bc55c0f8", "0x00000000000000000000000000000000000dead1", "0x1111111111111111111111111111111111111111"):
    out[frm] = {"minout_1": call(frm, 1), "minout_huge": call(frm, 10**40)}
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s6_router_gate.json", "w"), indent=1)
