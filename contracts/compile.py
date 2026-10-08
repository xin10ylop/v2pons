#!/usr/bin/env python3
"""Compile contracts/FlipRelay.sol with solc 0.8.26 (py-solc-x) into contracts/FlipRelay.json: abi, creation bytecode, runtime
bytecode, the immutable references (so a deployment can be checked byte for byte with the owner and PoolManager filled in), the
function selectors and the source's sha256 (relay_deploy.py refuses an artifact that was not built from the source beside it).

    python3 contracts/compile.py
"""
import hashlib, json, os
import solcx
ROOT = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(ROOT, "FlipRelay.sol"); OUT = os.path.join(ROOT, "FlipRelay.json")
if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]:
    solcx.install_solc("0.8.26")
src = open(SRC).read()
res = solcx.compile_standard({
    "language": "Solidity", "sources": {"FlipRelay.sol": {"content": src}},
    "settings": {"optimizer": {"enabled": True, "runs": 1000}, "evmVersion": "cancun",
                 "outputSelection": {"*": {"FlipRelay": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object", "evm.deployedBytecode.immutableReferences", "evm.methodIdentifiers"]}}}},
    solc_version="0.8.26")
c = res["contracts"]["FlipRelay.sol"]["FlipRelay"]
art = {"contract": "FlipRelay", "solc": "0.8.26", "optimizer_runs": 1000, "evm": "cancun", "source_sha256": hashlib.sha256(src.encode()).hexdigest(),
       "abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"], "deployedBytecode": "0x" + c["evm"]["deployedBytecode"]["object"],
       "immutableReferences": c["evm"]["deployedBytecode"]["immutableReferences"], "selectors": c["evm"]["methodIdentifiers"]}
json.dump(art, open(OUT, "w"), indent=1)
print(f"wrote {OUT}: runtime {len(art['deployedBytecode']) // 2 - 1} bytes; selectors {art['selectors']}")
