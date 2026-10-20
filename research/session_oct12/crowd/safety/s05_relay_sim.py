"""FlipRelayV3 as the engine would use it, simulated by eth_call on the head's state (nothing sent): the relay's runtime from
contracts/FlipRelayV3.json (owner filled in) at a test address with an ETH balance, and GasProbe.sol (this directory, research only) at the
owner's address measuring each call's gas inside the EVM. On every v3crowd pool still live (its pool holds tokens): buy then sell at 0.002 and
0.004 ETH (minOut 0 here: the fills are reported), the round trip against two fees. Then the failure paths of a v3crowd trade:
a buy with no pool at the address (NoPool: a launch that reverted), the presigned sell after it (NothingToSell), a sell of tokens on a pulled
pool under the engine's 500,000-gas limit, a buy whose deadline has passed (TooLate), a buy whose minOut is above the fill (TooLittleOut).
Transaction gas = the EVM's + 21,000 + calldata (4/16 a byte) (+ the L1 part, 70-1,300 gas on our own receipts: s05a). Writes s05_relay_sim.out."""
from common import *
import rpc, re, solcx
S = json.load(open(J("s00_probe.json"))); ETH = S["eth_usd"]
art = json.load(open(os.path.join(HERE, "..", "..", "..", "..", "contracts", "FlipRelayV3.json")))
HARN = "0xa3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3"; RELAY_AT = "0xf3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3"
code = bytearray(bytes.fromhex(art["deployedBytecode"][2:]))
for refs in art["immutableReferences"].values():
    for r in refs: code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(HARN[2:])
RELAY_CODE = "0x" + code.hex()
out = solcx.compile_files([J("GasProbe.sol")], output_values=["bin-runtime", "abi"], solc_version="0.8.26", optimize=True, optimize_runs=200, evm_version="cancun")
PROBE = "0x" + [v for k, v in out.items() if k.endswith(":GasProbe")][0]["bin-runtime"]
from eth_abi import encode, decode
sel = lambda s: keccak(text=s)[:4]
def buy_data(tok, fee, amt, mo, dl): return sel("buy(address,uint24,uint256,uint256,uint256)") + encode(["address", "uint24", "uint256", "uint256", "uint256"], [tok, fee, amt, mo, dl])
def sell_data(tok, fee, mo, dl): return sel("sell(address,uint24,uint256,uint256)") + encode(["address", "uint24", "uint256", "uint256"], [tok, fee, mo, dl])
ERR = {keccak(text=e)[:4].hex(): e.split("(")[0] for e in ("NotOwner()", "NotPool(address)", "Busy()", "TooLate(uint256,uint256)", "NoPool(address)", "Insufficient(uint256,uint256)",
       "NothingToSell(address)", "TooLittleOut(uint256,uint256)", "Overpay(uint256,uint256)", "TransferFailed(address)")}
def why(ret): return ERR.get(ret[:4].hex(), ret[:4].hex() or "(no data: out of gas or a plain revert)") if ret else "(no data: out of gas or a plain revert)"
def calldata_gas(b): return sum(16 if x else 4 for x in b)
head = rpc.call("eth_getBlockByNumber", ["latest", False]); hn = int(head["number"], 16); hts = int(head["timestamp"], 16); bf = int(head["baseFeePerGas"], 16)
TAG = hex(hn)
print(f"head {hn} {utc(hts)}; base fee {bf / 1e9:.4f} gwei; ETH ${ETH:,.2f}; relay runtime {len(code)} bytes (owner {HARN})")
def ov(bal, extra=None):
    o = {HARN: {"code": PROBE}, RELAY_AT: {"code": RELAY_CODE, "balance": hex(bal)}}
    if extra: o.update(extra)
    return o
def roundtrip(tok, fee, amt, mo=0, dl=None, extra=None, cap=479000):
    dl = dl or hts + 600
    data = sel("roundtrip(address,bytes,bytes,uint256)") + encode(["address", "bytes", "bytes", "uint256"], [RELAY_AT, buy_data(tok, fee, amt, mo, dl), sell_data(tok, fee, 0, dl), cap])
    r = rpc.call("eth_call", [{"from": "0x" + "c0" * 20, "to": HARN, "data": "0x" + data.hex(), "gas": hex(30_000_000)}, TAG, ov(int(0.02e18), extra)])
    return decode(["bool", "uint256", "bytes", "bool", "uint256", "bytes", "uint256", "uint256"], bytes.fromhex(r[2:]))
def probe(data, bal=int(0.02e18), extra=None, cap=479000):
    pd = sel("probe(address,bytes,uint256)") + encode(["address", "bytes", "uint256"], [RELAY_AT, data, cap])
    r = rpc.call("eth_call", [{"from": "0x" + "c0" * 20, "to": HARN, "data": "0x" + pd.hex(), "gas": hex(30_000_000)}, TAG, ov(bal, extra)])
    return decode(["bool", "uint256", "bytes"], bytes.fromhex(r[2:]))
T = json.load(open(J("s03_tokens.json")))
# live pools now: the pool's token balance above 0 (refresh)
cand = [t for t in T if t["qs"] == 0][-40:]
bals = rpc.batch("eth_call", [[{"to": t["token"], "data": "0x70a08231" + word(t["pool"])}, TAG] for t in cand])
live = [t for t, b in zip(cand, bals) if b and int(b, 16) > 10 ** 24]
pulled = [t for t, b in zip(cand, bals) if b is not None and int(b, 16) < 10 ** 21]
print(f"of the last {len(cand)} WETH-token0 launches: live (pool holds > 1e6 tokens) {len(live)}, pulled {len(pulled)}")
for t in live:
    for amt in (int(0.002e18), int(0.004e18)):
        okb, gb, rb, oks, gs, rs, e1, e2 = roundtrip(t["token"], 100, amt)
        if not okb:
            print(f"  {t['pool']} {t['size']}B {amt / 1e18:.3f} ETH: buy reverted {why(rb)} gas {gb}"); continue
        got = decode(["uint256"], rb)[0]; back = decode(["uint256"], rs)[0] if oks else None
        txb = gb + 21000 + calldata_gas(buy_data(t["token"], 100, amt, got, hts + 3)); txs = gs + 21000 + calldata_gas(sell_data(t["token"], 100, 0, hts + 7200))
        print(f"  {t['pool']} ({t['size']} B, launch {utc(t['ts'])}) {amt / 1e18:.3f} ETH: buy {got / 1e18:,.0f} tokens, EVM gas {gb:,} (tx ~{txb:,}); "
              f"sell {'ok' if oks else 'REVERTED ' + why(rs)} {back / 1e18 if back else 0:.9f} ETH, EVM gas {gs:,} (tx ~{txs:,}); round trip {(back or 0) / amt - 1:+.4%} (two fees -0.0200%); "
              f"relay ETH after buy {e1 / 1e18:.6f}, after sell {e2 / 1e18:.6f}")
tk = (live or cand)[-1]["token"]
print("\nfailure paths (EVM gas inside the call; the transaction adds 21,000 + calldata):")
cases = [("buy, no pool at the CREATE2 address (a launch that reverted): fee 500 tier", buy_data(tk, 500, int(0.004e18), 1, hts + 600), None),
         ("the presigned sell after it: nothing to sell", sell_data(tk, 100, 0, hts + 7200), None),
         ("buy past its deadline (block time > fire time + 3 s)", buy_data(tk, 100, int(0.004e18), 1, hts - 1), None),
         ("buy whose minOut is above the fill (a buy ahead of ours > BUY_SLIP)", buy_data(tk, 100, int(0.004e18), 10 ** 40, hts + 600), None)]
if pulled:
    pt = pulled[-1]
    slot = "0x" + keccak(bytes.fromhex(word(RELAY_AT)) + bytes.fromhex(word(0))).hex()
    cases.append((f"sell of 1e23 tokens on a pulled pool {pt['pool'][:12]} under the 500,000 tx gas limit", sell_data(pt["token"], 100, 0, hts + 7200), {pt["token"]: {"stateDiff": {slot: "0x" + word(10 ** 23)}}}))
    cases.append((f"buy on that pulled pool under the 500,000 limit", buy_data(pt["token"], 100, int(0.004e18), 0, hts + 600), None))
for nm, d, extra in cases:
    ok, used, ret = probe(d, extra=extra)
    txg = used + 21000 + calldata_gas(d)
    print(f"  {nm}: {'ok' if ok else 'reverted ' + why(ret)}; EVM gas {used:,}; tx ~{txg:,} gas = {txg * bf / 1e18:.2e} ETH (${txg * bf / 1e18 * ETH:.4f}) at the base fee")
print(rpc.STATS)
