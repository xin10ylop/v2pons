import sys, json, collections, random
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
from eth_utils import keccak
SP = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
D = json.load(open(SP + "/oct8_pools.json"))
oth = [p for p in D["pools"] if p["kind"] == "other"]
random.seed(1); smp = random.sample(oth, 40)
hit = 0; npool = 0
for p in smp:
    ls = logs({"address": PM, "topics": [T_SWAP, p["pid"]]}, p["block"], p["block"] + 30)
    if not ls: continue
    npool += 1
    txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
    if any(t["from"].lower() == "0xe71a69f434a719cd5afa411568b69716aab3b84a" for t in txs if t): hit += 1
print(f"dust tester on non-operator pools: bought within 30 blocks on {hit} of {npool} sampled 'other' pools that had any swap in their first 30 blocks")
# the code hash of the copy launchers
cp = [p for p in D["pools"] if p["kind"] == "copy"]
codes = batch([("eth_getCode", [p["to"], "latest"]) for p in cp])
print("copy launcher code hashes (latest):", collections.Counter(keccak(bytes.fromhex(c[2:])).hex() if c and len(c) > 2 else "empty" for c in codes))
