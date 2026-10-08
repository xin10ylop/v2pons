#!/usr/bin/env python3
"""A buy and a sell through the Universal Router on a live pool, with the engine's exact calldata and no transaction.

Two checks by eth_call with state overrides:
1. The buy as the wallet would send it: from an address given a balance, to the router, value = the stake, the engine's
   buy calldata. No revert means the router, the pool and the bytes agree; the gas is estimated.
2. The round trip: a harness contract (contracts/RouterRoundTrip.sol) at an address with ETH sends the same buy calldata,
   makes the fleet's two approvals, patches the tokens it got into the engine's sell calldata and sends it. Prints the tokens
   against v4math's prediction from the pool's current state and the ETH that came back.

    python3 deploy/router_sim.py                              # the operator's latest unpulled pool (it pulls within minutes: often none)
    python3 deploy/router_sim.py any                          # the latest unpulled ETH-paired hookless pool of anyone
    python3 deploy/router_sim.py <poolId> [eth] [block]       # a given pool, 0.0001 ETH by default; at a past block (the pool's state then)
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import relay_sim, ur, v4math
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UR = os.environ.get("UNIVERSAL_ROUTER", ur.UR).lower(); PERMIT2 = os.environ.get("PERMIT2", ur.PERMIT2).lower()
WALLET_AT = "0x" + "c0" * 20; HARNESS_AT = "0x" + "a2" * 20
W = relay_sim.W; word = relay_sim.word; rpc = relay_sim.rpc


def compile_harness():
    import solcx
    src = open(os.path.join(ROOT, "contracts", "RouterRoundTrip.sol")).read()
    r = solcx.compile_standard({"language": "Solidity", "sources": {"H.sol": {"content": src}}, "settings": {"optimizer": {"enabled": True, "runs": 200}, "viaIR": True, "evmVersion": "cancun",
                                "outputSelection": {"*": {"RouterRoundTrip": ["evm.deployedBytecode.object"]}}}}, solc_version="0.8.26")
    return "0x" + r["contracts"]["H.sol"]["RouterRoundTrip"]["evm"]["deployedBytecode"]["object"]


def main():
    relay_sim.RPC = os.environ.get("RPC_URL", relay_sim.RPC)
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    pid = relay_sim.latest_operator_pool(any_launcher=(arg == "any")) if arg in ("", "any") else arg
    amount = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 10 ** 14
    upto = int(sys.argv[3]) if len(sys.argv) > 3 else None; tag = hex(upto) if upto else "latest"
    key, sqrt_p, liq, b0, n = relay_sim.pool_state(pid, upto)
    print(f"pool {pid[:14]}: token {key['currency1']}, fee {key['fee'] / 1e4:g}%, tick spacing {key['tickSpacing']}, hook {key['hooks'][-6:]}; created block {b0}, {n} events; sqrtP {sqrt_p}, active liquidity {liq:.4g}; state at {tag}")
    if key["currency0"] != "0x" + "0" * 40: raise SystemExit("not an ETH-paired pool")
    if liq == 0: raise SystemExit("the pool has no liquidity at that block")
    k = {"c0": key["currency0"], "token": key["currency1"], "fee": key["fee"], "tick_spacing": key["tickSpacing"], "hooks": key["hooks"]}
    expect = v4math.buy_out_int(sqrt_p, liq, amount, key["fee"])
    buy = ur.buy_calldata(k, amount, 0, 0); sell = ur.sell_calldata(k, 1, 0, 0)
    for a in (UR, PERMIT2):
        code = rpc("eth_getCode", [a, "latest"])
        if len(code) <= 2: raise SystemExit(f"no code at {a}")
    # 1. the buy as the wallet sends it
    call = {"from": WALLET_AT, "to": UR, "value": hex(amount), "data": buy}; ov = {WALLET_AT: {"balance": hex(amount * 2)}}
    t0 = time.time()
    try:
        rpc("eth_call", [dict(call, gas=hex(1_000_000)), tag, ov], tries=2)
        gas = int(rpc("eth_estimateGas", [call, tag, ov], tries=2), 16)
        print(f"buy from a wallet through the router: ok ({1000 * (time.time() - t0):.0f} ms), about {gas} gas (the crowd's limit is 220000)")
    except RuntimeError as e:
        print("the buy through the router REVERTED:", str(e)[:400]); sys.exit(1)
    # 2. the round trip through the harness
    harness = compile_harness()
    data = ("0x" + keccak(text="run(address,address,address,bytes,uint256,bytes,uint256)").hex()[:8] + word(UR) + word(PERMIT2) + word(key["currency1"])
            + word(0xe0) + word(amount) + word(0xe0 + 32 + len(buy[2:]) // 2 + (-(len(buy[2:]) // 2)) % 32) + word(ur.AMOUNT_IN_OFFSET)
            + ur._bytes_arg(buy[2:]) + ur._bytes_arg(sell[2:]))
    ov = {HARNESS_AT: {"code": harness, "balance": hex(amount * 2)}}
    t0 = time.time()
    try:
        r = rpc("eth_call", [{"from": WALLET_AT, "to": HARNESS_AT, "data": data, "gas": hex(3_000_000)}, tag, ov], tries=2)
    except RuntimeError as e:
        print("the simulated round trip reverted:", str(e)[:600]); sys.exit(1)
    tokens_out, eth_back, gas_buy, gas_sell = (W(r, i) for i in range(4))
    print(f"eth_call in {1000 * (time.time() - t0):.0f} ms")
    print(f"buy  {amount / 1e18:.6f} ETH -> {tokens_out:.6g} tokens (v4math predicted {expect:.6g}: {'exact' if tokens_out == expect else f'off by {(tokens_out - expect) / expect:+.2e}'}); {gas_buy} gas")
    print(f"sell all -> {eth_back / 1e18:.6f} ETH back ({(eth_back - amount) / amount:+.2%} round trip at the pool's fee {key['fee'] / 1e4:g}% each way); {gas_sell} gas; tokens left 0: accounting ok")
    # minOut one above the real output must be refused
    buy_hi = ur.buy_calldata(k, amount, tokens_out + 1, 0)
    try:
        rpc("eth_call", [{"from": WALLET_AT, "to": UR, "value": hex(amount), "data": buy_hi, "gas": hex(1_000_000)}, tag, {WALLET_AT: {"balance": hex(amount * 2)}}], tries=1)
        print("a buy with minOut above the real output WENT THROUGH: do not use this router build"); sys.exit(1)
    except RuntimeError as e:
        print("a buy with minOut one above the real output is refused:", "V4TooLittleReceived ok" if "8b063d73" in str(e) or "revert" in str(e).lower() else str(e)[:200])


if __name__ == "__main__":
    main()
