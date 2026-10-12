#!/usr/bin/env python3
"""Compile contracts/BnbRoundTrip.sol with solc 0.8.26 (py-solc-x) into contracts/BnbRoundTrip.json: abi, runtime bytecode, the
function selectors and the source's sha256. The BNB engine's live path (src/bnb_live.py) places the runtime bytecode by eth_call state
override for its pre-buy round-trip check; it refuses an artifact that was not built from the source beside it. Never deployed.

    python3 contracts/compile_bnb.py
"""
import hashlib, json, os
import solcx
ROOT = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(ROOT, "BnbRoundTrip.sol"); OUT = os.path.join(ROOT, "BnbRoundTrip.json")
if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]:
    solcx.install_solc("0.8.26")
src = open(SRC).read()
res = solcx.compile_standard({
    "language": "Solidity", "sources": {"BnbRoundTrip.sol": {"content": src}},
    "settings": {"optimizer": {"enabled": True, "runs": 200}, "evmVersion": "cancun",
                 "outputSelection": {"*": {"BnbRoundTrip": ["abi", "evm.deployedBytecode.object", "evm.methodIdentifiers"]}}}},
    solc_version="0.8.26")
c = res["contracts"]["BnbRoundTrip.sol"]["BnbRoundTrip"]
art = {"contract": "BnbRoundTrip", "solc": "0.8.26", "optimizer_runs": 200, "evm": "cancun", "source_sha256": hashlib.sha256(src.encode()).hexdigest(),
       "abi": c["abi"], "deployedBytecode": "0x" + c["evm"]["deployedBytecode"]["object"], "selectors": c["evm"]["methodIdentifiers"]}
json.dump(art, open(OUT, "w"), indent=1)
print(f"wrote {OUT}: runtime {len(art['deployedBytecode']) // 2 - 1} bytes; selectors {art['selectors']}")
