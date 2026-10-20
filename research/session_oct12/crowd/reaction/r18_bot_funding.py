"""who funds the + 1 bot: its buys are value-0 calls from EOA 0x776e5a2a to contract 0x570759db, which takes WETH from the EOA for the pool. Every WETH
Transfer into the EOA (and WETH Deposits by it) from block START to the head, grouped by sender; the same for Transfers out. One
address and one value per topic, so any range is allowed. Paced at >= 1.5 s between calls (another fetch may be running)."""
from common import *
import rpc, collections
BOTC = "0x570759db4ca57e1b785ef3bff4250309a648b21a"; BOTE = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"
T_TR = tp("Transfer(address,address,uint256)"); T_DEP = tp("Deposit(address,uint256)")
START = int(sys.argv[1]) if len(sys.argv) > 1 else 74_000_000
head = json.load(open(J("r01_meta.json")))["head"]
def q(flt):
    time.sleep(1.5); return rpc.call("eth_getLogs", [dict(flt, fromBlock=hex(START), toBlock=hex(head))])
pad = lambda a: "0x" + a[2:].zfill(64)
WHO = BOTE        # the router 0x570759db takes the WETH from its caller: the EOA pays
tin = q({"address": WETH, "topics": [T_TR, None, pad(WHO)]})
tout = q({"address": WETH, "topics": [T_TR, pad(WHO)]})
dep = q({"address": WETH, "topics": [T_DEP, pad(WHO)]})
L = json.load(open(J("r01_launches.json"))); pools = {x["pool"] for x in L}; lw = {x["from"] for x in L}
def who(a):
    return "line pool" if a in pools else "launch wallet" if a in lw else "bot EOA" if a == BOTE else a
c_in = collections.Counter(); e_in = collections.defaultdict(float)
for l in tin:
    s = "0x" + l["topics"][1][-40:]; c_in[who(s)] += 1; e_in[who(s)] += int(l["data"], 16) / 1e18
c_out = collections.Counter(); e_out = collections.defaultdict(float)
for l in tout:
    r = "0x" + l["topics"][2][-40:]; k = "line pool" if r in pools else r; c_out[k] += 1; e_out[k] += int(l["data"], 16) / 1e18
print(f"WETH into {WHO} since block {START}: {len(tin)} transfers; by sender (count, ETH):")
for k, n in c_in.most_common(12): print(f"   {k}: {n} {e_in[k]:.4f}")
print(f"WETH deposits by it: {len(dep)}, {sum(int(l['data'], 16) for l in dep) / 1e18:.4f} ETH")
print(f"WETH out of it: {len(tout)} transfers; by recipient (count, ETH):")
for k, n in c_out.most_common(8): print(f"   {k}: {n} {e_out[k]:.4f}")
first = min([int(l["blockNumber"], 16) for l in tin + dep] or [0])
print("first funding block", first, rpc.STATS)
