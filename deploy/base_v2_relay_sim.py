#!/usr/bin/env python3
"""base_v2_relay_sim.py: FlipRelayV2's buy and sell on a live Base V2 pair with nothing sent: an eth_call with state overrides puts the relay's
runtime code (owner = the harness, router and WETH filled into the immutables) at one address with ETH, and contracts/V2RelayHarness.sol at
another; the harness buys with the stake and sells everything back. Prints the tokens bought, the ETH back and the share of the stake it is.

    python3 deploy/base_v2_relay_sim.py <pair> [eth] [--block N] [--rpc URL]   # a given pair (defaults: 0.01 ETH, the head)
    python3 deploy/base_v2_relay_sim.py                                        # the newest fresh-wallet pair (base_v2_sim.py's pick)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import solcx
import base_v2_sim as S
RELAY_AT = "0x" + "f2" * 20; HARNESS_AT = "0x" + "a3" * 20


def compiled(name):
    src = open(os.path.join(ROOT, "contracts", name + ".sol")).read()
    res = solcx.compile_standard({"language": "Solidity", "sources": {name + ".sol": {"content": src}}, "settings": {"optimizer": {"enabled": True, "runs": 1000}, "evmVersion": "cancun",
                                  "outputSelection": {"*": {name: ["evm.deployedBytecode.object", "evm.deployedBytecode.immutableReferences", "evm.methodIdentifiers"]}}}}, solc_version="0.8.26")
    return res["contracts"][name + ".sol"][name]


def relay_runtime(owner, router, weth):
    """FlipRelayV2's runtime with its three immutables filled in, as the chain would hold it after a deployment by `owner`"""
    c = compiled("FlipRelayV2"); code = bytearray(bytes.fromhex(c["evm"]["deployedBytecode"]["object"]))
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelayV2.json")))
    assert art["deployedBytecode"] == "0x" + c["evm"]["deployedBytecode"]["object"], "contracts/FlipRelayV2.json was not built from FlipRelayV2.sol"
    # the immutables' order in the source: owner, router, weth; solc numbers them by AST id, which follows declaration order
    refs = c["evm"]["deployedBytecode"]["immutableReferences"]; ids = sorted(refs, key=int); vals = [owner, router, weth]
    for i, k in enumerate(ids):
        for r in refs[k]: code[r["start"]:r["start"] + r["length"]] = bytes.fromhex(S.word(vals[i]))
    return "0x" + code.hex(), c["evm"]["methodIdentifiers"]


def main(argv):
    url = S.RPC; stake = 0.01; block = "latest"; pair = None
    if "--rpc" in argv: url = argv[argv.index("--rpc") + 1]
    if "--block" in argv: block = hex(int(argv[argv.index("--block") + 1]))
    pos = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] not in ("--rpc", "--block")]
    if pos and pos[0].startswith("0x"): pair = pos[0]; pos = pos[1:]
    if pos: stake = float(pos[0])
    if pair is None:
        found = S.recent_pairs(url, 3000, 1.0); pair = found[-1]["pair"]; print("newest fresh-wallet pair:", found[-1])
    t0 = S.rpc(url, "eth_call", [{"to": pair, "data": "0x0dfe1681"}, block]); t1 = S.rpc(url, "eth_call", [{"to": pair, "data": "0xd21220a7"}, block])
    token = "0x" + (t1 if "0x" + t0[-40:] == S.WETH else t0)[-40:]
    relay_code, relay_sels = relay_runtime(HARNESS_AT, S.ROUTER, S.WETH); h = compiled("V2RelayHarness"); harness_code = "0x" + h["evm"]["deployedBytecode"]["object"]
    stake_wei = int(stake * 1e18); data = "0x" + h["evm"]["methodIdentifiers"]["run(address,address,uint256,uint256)"] + S.word(RELAY_AT) + S.word(token) + S.word(stake_wei) + S.word(0)
    ov = {RELAY_AT: {"code": relay_code, "balance": hex(stake_wei)}, HARNESS_AT: {"code": harness_code}}
    r = S.rpc(url, "eth_call", [{"from": S.CALLER, "to": HARNESS_AT, "data": data, "gas": "0x7a1200"}, block, ov])
    if isinstance(r, dict): sys.exit("the relay round trip REVERTED: %s" % str(r["error"])[:300])
    tokens, eth_out = S.W(r, 0), S.W(r, 1)
    print("FlipRelayV2 on pair %s at %s: buy %.6f ETH -> %d tokens; sell -> %.6f ETH (%.1f%% of the stake); relay selectors %s" % (pair, block, stake, tokens, eth_out / 1e18, 100 * eth_out / stake_wei, {k: v for k, v in relay_sels.items() if k.startswith(("buy", "sell"))}))
    # the owner check: the same call from a relay whose owner is someone else must revert NotOwner
    other_code, _ = relay_runtime(S.CALLER, S.ROUTER, S.WETH); ov2 = dict(ov, **{RELAY_AT: {"code": other_code, "balance": hex(stake_wei)}})
    r2 = S.rpc(url, "eth_call", [{"from": S.CALLER, "to": HARNESS_AT, "data": data, "gas": "0x7a1200"}, block, ov2])
    print("owner check:", "refused (NotOwner)" if isinstance(r2, dict) and "30cd7471" in str(r2["error"]) else ("REVERTED differently: %s" % str(r2)[:120] if isinstance(r2, dict) else "NOT REFUSED: the relay let a non-owner trade"))


if __name__ == "__main__":
    main(sys.argv)
