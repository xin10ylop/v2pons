"""Anatomy of each shape: target and hook code sizes, the calldata words of a sample launch, and the receipt of 2 sample launches per shape
(every log: emitter, topic0, decoded where known). Caches receipts in cache/s02_rcpt_cache.jsonl. Prints s02_anatomy.out."""
from common import *
import rpc, collections
X = json.load(open(J("s01_launches.json")))
R = {r["transactionHash"]: r for r in jl(C("s02_rcpt_cache.jsonl"))}
SIG = {T_INIT: "Initialize", T_SWAP: "Swap", T_ML: "ModifyLiquidity", T_TRANSFER: "Transfer",
       "0x" + keccak(text="Approval(address,address,uint256)").hex(): "Approval",
       "0x" + keccak(text="UserOperationEvent(bytes32,address,address,uint256,bool,uint256,uint256)").hex(): "UserOperationEvent",
       "0x" + keccak(text="BeforeExecution()").hex(): "BeforeExecution",
       "0x" + keccak(text="AccountDeployed(bytes32,address,address,address)").hex(): "AccountDeployed",
       "0x" + keccak(text="Deposited(address,uint256)").hex(): "Deposited",
       "0x" + keccak(text="OwnershipTransferred(address,address)").hex(): "OwnershipTransferred",
       "0x" + keccak(text="Deposit(address,uint256)").hex(): "WETH.Deposit",
       "0x" + keccak(text="Withdrawal(address,uint256)").hex(): "WETH.Withdrawal",
       "0x" + keccak(text="Donate(bytes32,address,uint256,uint256)").hex(): "Donate"}
codes = {}
def code(a):
    if a not in codes: codes[a] = rpc.call("eth_getCode", [a, "latest"])
    return codes[a]
for s, v in X.items():
    print(f"===== {s}: {len(v)} launches")
    for to in sorted({r["to"] for r in v}):
        print(f"  target {to} code {len(code(to)) // 2 - 1} B keccak {keccak(bytes.fromhex(code(to)[2:])).hex()[:12]}")
    for hk in sorted({r["hook"] for r in v}):
        if int(hk, 16): print(f"  hook {hk} code {len(code(hk)) // 2 - 1} B flags {hook_flags(hk)}")
    print("  launch wallets:", collections.Counter(r["from"] for r in v).most_common(6))
    print("  fee/ts/sqrtP/tick:", collections.Counter((r["fee"], r["ts"], r["sqrtP"], r["tick"]) for r in v).most_common(4))
    for r in v[-2:]:
        t = rpc.call("eth_getTransactionByHash", [r["tx"]])
        inp = t["input"][2:]
        print(f"  sample {r['tx']} block {r['lb']} from {r['from']} to {r['to']} value {r['value'] / 1e18} sel {inp[:8]} words:")
        for i in range(0, min((len(inp) - 8) // 64, 140)):
            w = inp[8 + 64 * i: 8 + 64 * (i + 1)]
            if int(w, 16): print(f"     w{i:3d} {w}")
        if r["tx"] not in R:
            R[r["tx"]] = rpc.call("eth_getTransactionReceipt", [r["tx"]])
            with open(C("s02_rcpt_cache.jsonl"), "a") as f: f.write(json.dumps(R[r["tx"]]) + "\n")
        rc = R[r["tx"]]
        print(f"   receipt status {rc['status']} gasUsed {int(rc['gasUsed'], 16)} logs {len(rc['logs'])}")
        for l in rc["logs"]:
            nm = SIG.get(l["topics"][0], l["topics"][0][:10]) if l["topics"] else "anon"
            extra = ""
            if nm == "Transfer" and len(l["topics"]) == 3: extra = f"{l['topics'][1][-40:][:10]}->{l['topics'][2][-40:][:10]} {int(l['data'], 16) if l['data'] != '0x' else ''}"
            elif nm == "Swap": extra = f"a0 {sgn(W(l['data'], 0))} a1 {sgn(W(l['data'], 1))} sender {l['topics'][2][-40:][:10]}"
            elif nm == "ModifyLiquidity": extra = f"lo {sgn(W(l['data'], 0))} hi {sgn(W(l['data'], 1))} dL {sgn(W(l['data'], 2))} sender {l['topics'][2][-40:][:10]}"
            elif nm == "UserOperationEvent": extra = f"sender {l['topics'][2][-40:]} paymaster {l['topics'][3][-40:]} success {W(l['data'], 1)}"
            print(f"     {l['address'][:12]} {nm:18s} {extra}")
print(rpc.STATS)
