#!/usr/bin/env python3
"""Run a buy and a sell through the FlipRelay on a live pool without sending anything: eth_call with state overrides puts the
relay's runtime code (owner and PoolManager filled in) at one address with a balance, and a harness contract at another as its
owner; the harness buys, reads the balance, sells, and checks the accounting. Prints the tokens the buy got against v4math's
prediction from the pool's current state, and the ETH the sell got back.

    python3 deploy/relay_sim.py                       # the operator's latest unpulled pool
    python3 deploy/relay_sim.py <poolId>              # a given v4 pool (ETH-paired, no hook)
    python3 deploy/relay_sim.py <poolId> 0.001        # with 0.001 ETH instead of 0.0001
"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import v4math
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RPC = os.environ.get("RPC_URL", "https://rpc.mainnet.chain.robinhood.com"); H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; LAUNCHER = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
RELAY_AT = "0x" + "f1" * 20; HARNESS_AT = "0x" + "a1" * 20
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); A = lambda d, i: "0x" + d[2 + 64*i + 24: 2 + 64*(i+1)]
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x[2:].lower().zfill(64)


def rpc(m, p, tries=6):
    last = None
    for i in range(tries):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60))
            if "result" in d: return d["result"]
            last = d["error"]
            if last.get("code") != 429: raise RuntimeError(json.dumps(last))
        except RuntimeError: raise
        except Exception as e: last = str(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"{m}: {last}")


def compile_harness():
    import solcx
    if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]:
        print("installing solc 0.8.26 (once, about 10 MB)"); solcx.install_solc("0.8.26")
    src = open(os.path.join(ROOT, "contracts", "RoundTripHarness.sol")).read()
    r = solcx.compile_standard({"language": "Solidity", "sources": {"H.sol": {"content": src}}, "settings": {"optimizer": {"enabled": True, "runs": 200}, "evmVersion": "cancun",
                                "outputSelection": {"*": {"RoundTripHarness": ["evm.deployedBytecode.object"]}}}}, solc_version="0.8.26")
    return "0x" + r["contracts"]["H.sol"]["RoundTripHarness"]["evm"]["deployedBytecode"]["object"]


def relay_runtime(owner):
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelay.json"))); code = bytearray.fromhex(art["deployedBytecode"][2:])
    fill = {"pm": PM, "owner": owner}
    for name_id, refs in art["immutableReferences"].items():
        pass
    # solc keys immutable references by AST id; match them through the ABI order of declaration: pm first, owner second
    ids = sorted(art["immutableReferences"], key=int)
    assert len(ids) == 2, art["immutableReferences"]
    for ast_id, val in zip(ids, (PM, owner)):
        for r in art["immutableReferences"][ast_id]:
            code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
    return "0x" + code.hex()


def pool_state(pid):
    """the pool's key and current (sqrtP, active liquidity) from its Initialize, ModifyLiquidity and last Swap logs"""
    head = int(rpc("eth_blockNumber", []), 16)
    init = None
    for a in range(head, head - 2_000_000, -200_000):
        ls = rpc("eth_getLogs", [{"fromBlock": hex(max(1, a - 199_999)), "toBlock": hex(a), "address": PM, "topics": [T_INIT, pid]}])
        if ls: init = ls[0]; break
    if not init: raise SystemExit("pool not found in the last 2M blocks")
    d = init["data"]; b0 = int(init["blockNumber"], 16)
    key = {"currency0": "0x" + init["topics"][2][-40:], "currency1": "0x" + init["topics"][3][-40:], "fee": W(d, 0), "tickSpacing": sgn(W(d, 1)), "hooks": A(d, 2)}
    sqrt_p, tick0 = W(d, 3), sgn(W(d, 4))
    ls = rpc("eth_getLogs", [{"fromBlock": hex(b0), "toBlock": "latest", "address": PM, "topics": [[T_SWAP, T_ML], pid]}])
    adds = []; last_swap = None
    for l in ls:
        if l["topics"][0] == T_ML: adds.append((sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))))
        else: last_swap = l
    liq = sum(x[2] for x in adds if x[0] < tick0 <= x[1])
    if last_swap: sqrt_p, liq = W(last_swap["data"], 2), W(last_swap["data"], 3)
    return key, sqrt_p, liq, b0, len(ls)


def latest_operator_pool():
    head = int(rpc("eth_blockNumber", []), 16)
    ls = rpc("eth_getLogs", [{"fromBlock": hex(head - 400_000), "toBlock": "latest", "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}])
    for l in reversed(ls):
        d = l["data"]
        if A(d, 2) != "0x" + "0" * 40 or sgn(W(d, 1)) != 200: continue
        t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
        if (t.get("to") or "").lower() != LAUNCHER: continue
        pid = l["topics"][1]
        rem = rpc("eth_getLogs", [{"fromBlock": l["blockNumber"], "toBlock": "latest", "address": PM, "topics": [T_ML, pid]}])
        if any(sgn(W(r["data"], 2)) < 0 for r in rem): continue
        return pid
    raise SystemExit("no unpulled operator pool in the last 400k blocks")


def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else latest_operator_pool()
    amount = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 10 ** 14
    key, sqrt_p, liq, b0, n = pool_state(pid)
    print(f"pool {pid[:14]}: token {key['currency1']}, fee {key['fee'] / 1e4:g}%, tick spacing {key['tickSpacing']}, hook {key['hooks'][-6:]}; created block {b0}, {n} events; sqrtP {sqrt_p}, active liquidity {liq:.4g}")
    if key["currency0"] != "0x" + "0" * 40: raise SystemExit("not an ETH-paired pool")
    expect = v4math.buy_out_int(sqrt_p, liq, amount, key["fee"])
    harness = compile_harness(); relay = relay_runtime(HARNESS_AT)
    data = ("0x" + keccak(text="run(address,(address,address,uint24,int24,address),uint256,uint256)").hex()[:8] + word(RELAY_AT) + word(key["currency0"]) + word(key["currency1"])
            + word(key["fee"]) + word(key["tickSpacing"]) + word(key["hooks"]) + word(amount) + word(0))
    ov = {RELAY_AT: {"code": relay, "balance": hex(amount * 2)}, HARNESS_AT: {"code": harness}}
    t0 = time.time()
    try:
        r = rpc("eth_call", [{"from": "0x" + "c0" * 20, "to": HARNESS_AT, "data": data, "gas": hex(3_000_000)}, "latest", ov], tries=2)
    except RuntimeError as e:
        print("the simulated round trip reverted:", str(e)[:400]); sys.exit(1)
    tokens_out, held, eth_back, eth_after = (W(r, i) for i in range(4))
    print(f"eth_call in {1000 * (time.time() - t0):.0f} ms")
    print(f"buy  {amount / 1e18:.6f} ETH -> {tokens_out:.6g} tokens (v4math predicted {expect:.6g}: {'exact' if tokens_out == expect else f'off by {(tokens_out - expect) / expect:+.2e}'}); the relay holds {held:.6g}")
    print(f"sell all -> {eth_back / 1e18:.6f} ETH back ({(eth_back - amount) / amount:+.2%} round trip at the pool's fee {key['fee'] / 1e4:g}% each way); relay ETH after {eth_after / 1e18:.6f}, tokens left 0: accounting ok")
    try:
        rpc("eth_call", [{"from": "0x" + "c0" * 20, "to": HARNESS_AT, "data": data[:-64] + word(tokens_out + 1), "gas": hex(3_000_000)}, "latest", ov], tries=1)
        print("a buy with minOut above the real output WENT THROUGH: the relay does not enforce minOut; do not use it"); sys.exit(1)
    except RuntimeError as e:
        print("a buy with minOut one above the real output is refused:", "TooLittleOut ok" if "e20a4c5d" in str(e) else ("reverted, but not with TooLittleOut: " + str(e)[:200]))
    gas = rpc("eth_estimateGas", [{"from": "0x" + "c0" * 20, "to": HARNESS_AT, "data": data}, "latest", ov]) if False else None


if __name__ == "__main__":
    main()
