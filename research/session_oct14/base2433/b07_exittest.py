"""The exit test for the 2.433 operator's Base pools (REPORT_BASE2433.md): can an outsider who buys sell again through the per-launch
afterSwap hook? No transaction: an eth_call with state overrides at a past block puts our FlipRelay's runtime code (PoolManager = Base's,
owner = a harness) at one address with ETH, and contracts/RoundTripHarness.sol at another as its owner; the harness buys through the
pool, reads the balance, sells everything back and checks the accounting (deploy/relay_sim.py's method, on Base).

Then a sell held across blocks: with the buy's tokens written into the relay's balance slot at a later block (the slot found by probing
the token's balanceOf under overrides), a sell alone from the relay. That covers a hook that refuses a sell in a later block than the buy.

Tenderly's public Base gateway serves eth_call at old blocks with state overrides.
usage: python3 b07_exittest.py [launch_block, default 52590807] [amount ETH, default 0.002]"""
import json, os, sys, time, urllib.request, ssl
ROOT = "/home/user/v2pons"
sys.path.insert(0, os.path.join(ROOT, "deploy")); sys.path.insert(0, os.path.join(ROOT, "src"))
from eth_utils import keccak
import relay_sim as RS
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
RPC = "https://base.gateway.tenderly.co"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
RELAY_AT = "0x" + "f1" * 20; HARNESS_AT = "0x" + "a1" * 20; CALLER = "0x" + "c0" * 20
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16); A = lambda d, i: "0x" + d[2 + 64 * i + 24: 2 + 64 * (i + 1)]
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = RS.word


def rpc(m, p):
    for i in range(5):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60, context=CTX))
            return d
        except Exception as e:
            err = str(e); time.sleep(1 + i)
    return {"error": {"message": err}}


def why(e):
    d = (e.get("data") or "") if isinstance(e, dict) else ""
    if isinstance(d, dict): d = d.get("data", "")
    msg = (e.get("message", "") if isinstance(e, dict) else str(e))[:160]
    if isinstance(d, str) and d.startswith("0x08c379a0") and len(d) >= 138:
        n = int(d[74:138], 16); return f"revert '{bytes.fromhex(d[138:138 + 2 * n]).decode('utf-8', 'replace')}'"
    return f"{msg} {d[:74] if isinstance(d, str) else ''}"


def main():
    L = int(sys.argv[1]) if len(sys.argv) > 1 else 52590807
    amount = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 2 * 10 ** 15
    init = rpc("eth_getLogs", [{"fromBlock": hex(L), "toBlock": hex(L), "address": PM, "topics": [T_INIT]}])["result"]
    init = [l for l in init if int(l["data"][2:66], 16) == 5000 and int(l["data"][66:130], 16) == 100][0]
    d = init["data"]; pid = init["topics"][1]
    key = {"currency0": "0x" + init["topics"][2][-40:], "currency1": "0x" + init["topics"][3][-40:], "fee": W(d, 0), "tickSpacing": sgn(W(d, 1)), "hooks": A(d, 2)}
    ev = rpc("eth_getLogs", [{"fromBlock": hex(L), "toBlock": hex(L + 60), "address": PM, "topics": [[T_SWAP, T_ML], pid]}])["result"]
    marks = [(int(e["blockNumber"], 16) - L, "swap" if e["topics"][0] == T_SWAP else ("add" if sgn(W(e["data"], 2)) > 0 else "PULL")) for e in ev]
    print(f"launch {L}: pool {pid[:18]} token {key['currency1']} fee {key['fee']} ts {key['tickSpacing']} hook {key['hooks']}")
    print(f"events to +60: {marks}")
    os.environ["RPC_URL"] = RPC; RS.PM = PM
    harness = RS.compile_harness(); relay = RS.relay_runtime(HARNESS_AT)
    run = ("0x" + keccak(text="run(address,(address,address,uint24,int24,address),uint256,uint256)").hex()[:8] + word(RELAY_AT) + word(key["currency0"]) + word(key["currency1"])
           + word(key["fee"]) + word(key["tickSpacing"] % (1 << 256)) + word(key["hooks"]) + word(amount) + word(0))
    ov = {RELAY_AT: {"code": relay, "balance": hex(amount * 2)}, HARNESS_AT: {"code": harness}}
    pull = min([o for o, k in marks if k == "PULL"] or [60])
    print(f"\nround trip in one call (buy then sell), {amount / 1e18:g} ETH, by an outside relay:")
    held_at = {}
    for off in [o for o in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20, 24, 28, 29) if o < pull]:
        r = rpc("eth_call", [{"from": CALLER, "to": HARNESS_AT, "data": run, "gas": hex(5_000_000)}, hex(L + off), ov])
        if "result" in r:
            tok, held, back, after = (W(r["result"], i) for i in range(4))
            held_at[off] = tok
            print(f"  at +{off:>2}: buy -> {tok:.6g} tokens, sell -> {back / 1e18:.6f} ETH ({(back - amount) / amount:+.2%})")
        else:
            print(f"  at +{off:>2}: REVERTED {why(r['error'])}")
    # the sell alone at a later block, with the tokens written into the relay's balance
    tokens = held_at.get(4) or held_at.get(5) or next(iter(held_at.values()), 0)
    if not tokens: print("no buy went through: no hold test"); return
    slot = None
    for s in range(0, 12):
        sl = "0x" + keccak(bytes.fromhex(word(RELAY_AT) + word(s))).hex()
        r = rpc("eth_call", [{"to": key["currency1"], "data": "0x70a08231" + word(RELAY_AT)}, hex(L + 5), {key["currency1"]: {"stateDiff": {sl: "0x" + word(tokens)}}}])
        if "result" in r and int(r["result"], 16) == tokens: slot = sl; print(f"\nthe token's balance mapping is at slot {s}"); break
    if not slot: print("balance slot not found in 0-11: no hold test"); return
    sell = "0x" + keccak(text="sell((address,address,uint24,int24,address),uint256,uint256)").hex()[:8] + word(key["currency0"]) + word(key["currency1"]) + word(key["fee"]) + word(key["tickSpacing"] % (1 << 256)) + word(key["hooks"]) + word(0) + word(0)
    print(f"a sell alone, the relay holding {tokens:.6g} tokens (an outsider's buy at +4), at later blocks:")
    for off in [o for o in (6, 8, 9, 10, 12, 14, 16, 20, 24, 28, 29) if o < pull]:
        ov2 = {RELAY_AT: {"code": relay, "balance": "0x0"}, key["currency1"]: {"stateDiff": {slot: "0x" + word(tokens)}}}
        r = rpc("eth_call", [{"from": HARNESS_AT, "to": RELAY_AT, "data": sell, "gas": hex(5_000_000)}, hex(L + off), ov2])
        print(f"  at +{off:>2}: " + (f"sell -> {W(r['result'], 0) / 1e18:.6f} ETH ({(W(r['result'], 0) - amount) / amount:+.2%} on the {amount / 1e18:g} ETH in)" if "result" in r else f"REVERTED {why(r['error'])}"))


if __name__ == "__main__":
    main()
