"""s11: Portal-side switches for the family. (a) storage at the head: the global bit flags (slot 0xa0, bit 0 = FeatureDisabled on
swapExactInput) and the per-token 'Unable to trade' flag (mapping slot 0xb8) for every family token; isSpammerBlocked for the family's
outside holders (it gates creation only, read for completeness). (b) admin events on the Portal over the window: SpammerBlockedStatusChanged,
BitFlagsChanged, FeeExemptionUpdated, RoleGranted/RoleRevoked, Upgraded (proxy), plus the token-level OwnershipTransferred after init.
-> data/s11.json, stdout"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_utils import keccak
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
P = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
fam = json.load(open(os.path.join(D, "s02_family.json")))["family"]
S = json.load(open(os.path.join(D, "s05_holders.json")))
def a32(a): return "0" * 24 + a[2:].lower()
flags = rpc.call("eth_getStorageAt", [P, "0xa0", "latest"])
print("Portal bit flags slot 0xa0:", flags, "bit0 (1 = swapExactInput enabled; clear = FeatureDisabled):", int(flags, 16) & 1)
blocked = []
for f in fam:
    s = "0x" + keccak(bytes.fromhex(a32(f["token"]) + "%064x" % 0xb8)).hex()
    v = int(rpc.call("eth_getStorageAt", [P, s, "latest"]), 16)
    if v & 0xff: blocked.append(f["token"])
print("family tokens with the per-token 'Unable to trade' flag set:", len(blocked), "of", len(fam))
outs = sorted(set(o["holder"] for o in S["rows"] if o["cls"] == ["outsider"]))
sp = [h for h in outs if int(rpc.ethcall(P, "0x" + keccak(text="isSpammerBlocked(address)").hex()[:8] + a32(h)) or "0x0", 16)]
print("outside holders with isSpammerBlocked = true:", len(sp), "of", len(outs))
sigs = ["SpammerBlockedStatusChanged(address,bool)", "BitFlagsChanged(uint256,uint256)", "FeeExemptionUpdated(address,bool)",
        "RoleGranted(bytes32,address,address)", "RoleRevoked(bytes32,address,address)", "Upgraded(address)", "AdminChanged(address,address)"]
T = {"0x" + keccak(text=s).hex(): s for s in sigs}
F1 = json.load(open(os.path.join(D, "s01.json")))
ev = rpc.logs_range(P, [list(T)], F1["from"], F1["head"], chunk=5000)
cnt = C.Counter(T[x["topics"][0]] for x in ev)
print("Portal admin events in the window", F1, dict(cnt))
for x in ev[:20]: print("  ", T[x["topics"][0]], int(x["blockNumber"], 16), x["transactionHash"], x["data"][:140])
own = 0
OT = "0x" + keccak(text="OwnershipTransferred(address,address)").hex()
for l in open(os.path.join(D, "toklogs_cache.jsonl")):
    j = json.loads(l)
    own += sum(1 for x in j["logs"] if x[4][0] == OT)
print("token OwnershipTransferred logs (all 56 tokens):", own, "(one per token = the initializer)")
json.dump({"flags": flags, "blocked_tokens": blocked, "spammer_blocked_holders": sp, "admin_events": dict(cnt),
           "admin_examples": [(T[x["topics"][0]], int(x["blockNumber"], 16), x["transactionHash"]) for x in ev[:50]]}, open(os.path.join(D, "s11.json"), "w"), indent=1)
