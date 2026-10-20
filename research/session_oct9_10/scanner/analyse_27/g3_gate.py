import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_27")
from load import *
from rpcc import call, call_many
P = load_pools()
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
OPWALLET = "0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"  # the only swapper
OURWALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
RAND = "0x1111111111111111111111111111111111111111"
def pad(a): return a[2:].rjust(64, "0")
sels = {"allowed(address)":"d63a8e11", "isOpen()":"47535d7b"}
# test a few pools: hook + launch contract
for p in g3[2:7]:
    hook = p["hooks"]; lc = p["launch_to"]
    print("=== pool", p["pid"][:10], "hook", hook, "launch_to", lc)
    for tgt_name, tgt in (("hook", hook), ("launch", lc)):
        for addr_name, addr in (("op", OPWALLET), ("ours", OURWALLET), ("rand", RAND)):
            for sn, sel in sels.items():
                data = "0x" + sel + (pad(addr) if "address" in sn else "")
                try:
                    r = call("eth_call", [{"to": tgt, "data": data}, "latest"])
                    tag = r if r in (None,) else (("TRUE" if r.endswith("1") else ("FALSE" if r.endswith("".join(["0"]*64)) else r)) if r else r)
                    if sn == "isOpen()" and addr_name != "op": continue
                    print("   %-6s %-4s %-14s -> %s" % (tgt_name, addr_name, sn, tag))
                except Exception as e:
                    print("   %-6s %-4s %-14s ERR %s" % (tgt_name, addr_name, sn, str(e)[:80]))
