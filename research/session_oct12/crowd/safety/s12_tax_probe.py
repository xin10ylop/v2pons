"""A transfer tax or a burn on transfer would make what arrives differ from what leaves. For every token (349): TaxProbe.sol (research only) at
a fresh address holding 1e24 tokens (balances slot 0, s03), transfer 1e22 to the pool (a sell's transfer) and 1e22 to another fresh address;
what left the sender and what arrived, exactly. eth_call, state overrides, the head's state. Writes s12_tax_probe.out."""
from common import *
import rpc, solcx, collections
from eth_abi import encode, decode
P = "0x7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a"; OTHER = "0x5afe0000000000000000000000000000000beef2"
code = "0x" + [v for k, v in solcx.compile_files([J("TaxProbe.sol")], output_values=["bin-runtime"], solc_version="0.8.26", optimize=True, optimize_runs=200,
                                                 evm_version="cancun").items() if k.endswith(":TaxProbe")][0]["bin-runtime"]
T = json.load(open(J("s03_tokens.json"))); AMT = 10 ** 22
items = []
for t in T:
    slot = "0x" + keccak(bytes.fromhex(word(P)) + bytes.fromhex(word(0))).hex()
    ov = {P: {"code": code}, t["token"]: {"stateDiff": {slot: "0x" + word(10 ** 24)}}}
    for dest in (t["pool"], OTHER):
        d = keccak(text="run(address,address,uint256)")[:4] + encode(["address", "address", "uint256"], [t["token"], dest, AMT])
        items.append([{"to": P, "data": "0x" + d.hex(), "gas": hex(2_000_000)}, "latest", ov])
res = rpc.batch("eth_call", items, n=20)
c = collections.Counter(); bad = []
for i, r in enumerate(res):
    t = T[i // 2]
    if r is None: c[(t["size"], "error")] += 1; bad.append((t["token"], "call failed")); continue
    left, arrived, ok = decode(["uint256", "uint256", "bool"], bytes.fromhex(r[2:]))
    k = "exact" if left == arrived == AMT and ok else f"left {left} arrived {arrived} ok {ok}"
    c[(t["size"], "to pool" if i % 2 == 0 else "to a wallet", k)] += 1
    if k != "exact": bad.append((t["token"], k))
for k, v in sorted(c.items(), key=str): print(k, v)
print("not exact:", bad[:10])
print(rpc.STATS)
