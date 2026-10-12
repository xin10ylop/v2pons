#!/usr/bin/env python3
"""Compile contracts/<Name>.sol with solc 0.8.26 (py-solc-x) into contracts/<Name>.json: abi, creation bytecode, runtime bytecode, the
immutable references (so a deployment can be checked byte for byte with the immutables filled in), the function selectors and the
source's sha256 (the deploy scripts refuse an artifact that was not built from the source beside it). Name defaults to FlipRelay.

    python3 contracts/compile.py                  # FlipRelay (the v4 relay)
    python3 contracts/compile.py FlipRelayV3      # the V3 relay
"""
import hashlib, json, os, sys
import solcx
NAME = sys.argv[1] if len(sys.argv) > 1 else "FlipRelay"
if NAME not in ("FlipRelay", "FlipRelayV3"):
    sys.exit(f"unknown contract {NAME}: FlipRelay or FlipRelayV3")
ROOT = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(ROOT, NAME + ".sol"); OUT = os.path.join(ROOT, NAME + ".json")
if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]:
    solcx.install_solc("0.8.26")
src = open(SRC).read()
res = solcx.compile_standard({
    "language": "Solidity", "sources": {NAME + ".sol": {"content": src}},
    "settings": {"optimizer": {"enabled": True, "runs": 1000}, "evmVersion": "cancun",
                 "outputSelection": {"*": {NAME: ["abi", "evm.bytecode.object", "evm.deployedBytecode.object", "evm.deployedBytecode.immutableReferences", "evm.methodIdentifiers"]}}}},
    solc_version="0.8.26")
c = res["contracts"][NAME + ".sol"][NAME]
art = {"contract": NAME, "solc": "0.8.26", "optimizer_runs": 1000, "evm": "cancun", "source_sha256": hashlib.sha256(src.encode()).hexdigest(),
       "abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"], "deployedBytecode": "0x" + c["evm"]["deployedBytecode"]["object"],
       "immutableReferences": c["evm"]["deployedBytecode"]["immutableReferences"], "selectors": c["evm"]["methodIdentifiers"]}
json.dump(art, open(OUT, "w"), indent=1)
print(f"wrote {OUT}: runtime {len(art['deployedBytecode']) // 2 - 1} bytes; selectors {art['selectors']}")
