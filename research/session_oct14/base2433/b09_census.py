"""Census of the 2.433 operator's Base launches since 09:30 UTC Oct 14: every PoolManager Initialize from block 52,590,400 to the head
with fee 5000 / tick spacing 100, plus any Initialize (any fee/ts) whose token has the operator's code hash 63ad5291cdef. Per pool: block,
time, launch tx, from, to (launcher), selector, calldata size, launcher and token code hash prefixes, hook and its v4 permission flags
(the low 14 address bits), sqrtPriceX96 and tick at init. Writes b09_census.json for b10-b12. Read-only (Tenderly's public Base gateway
for logs, publicnode for the head)."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.25
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
FLAGS = ["beforeInitialize", "afterInitialize", "beforeAddLiquidity", "afterAddLiquidity", "beforeRemoveLiquidity", "afterRemoveLiquidity",
         "beforeSwap", "afterSwap", "beforeDonate", "afterDonate", "beforeSwapReturnDelta", "afterSwapReturnDelta",
         "afterAddLiquidityReturnDelta", "afterRemoveLiquidityReturnDelta"]          # bit 13 .. bit 0
START = 52590400; OP_HASH = "63ad5291cdef"; Z = "0x" + "0" * 40
sg = lambda x, b=256: x - (1 << b) if x >> (b - 1) else x


def flags(addr):
    low = int(addr, 16) & 0x3FFF
    return [FLAGS[13 - b] for b in range(13, -1, -1) if low >> b & 1]


def chash(code): return keccak(bytes.fromhex(code[2:])).hex()[:12] if code and len(code) > 2 else "-"


def main():
    head, hts = xr.head("base")
    ini = []
    for s in range(START, head + 1, 500):
        ini += xr.batch("base_t", "eth_getLogs", [[{"address": PM, "topics": [T_INIT], "fromBlock": hex(s), "toBlock": hex(min(s + 499, head))}]], n=1)[0] or []
    print(f"Base head {head} at {time.strftime('%H:%M:%S', time.gmtime(hts))} UTC (run {time.strftime('%H:%M:%S', time.gmtime())} UTC); "
          f"v4 Initialize logs in {START}..{head}: {len(ini)}")
    toks = sorted({("0x" + l["topics"][3][-40:]) if l["topics"][2][-40:] == "0" * 40 else "0x" + l["topics"][2][-40:] for l in ini})
    codes = dict(zip(toks, xr.batch("base", "eth_getCode", [[t, "latest"] for t in toks], n=20)))
    th = {t: chash(c) for t, c in codes.items()}
    sel = [l for l in ini if (xr.W(l["data"], 0) == 5000 and sg(xr.W(l["data"], 1)) == 100)
           or th.get(("0x" + l["topics"][3][-40:]) if l["topics"][2][-40:] == "0" * 40 else "0x" + l["topics"][2][-40:]) == OP_HASH]
    print(f"tokens checked for code hash {OP_HASH}: {len(toks)}; with it: {sum(1 for v in th.values() if v == OP_HASH)}; "
          f"fee 5000/ts 100: {sum(1 for l in ini if xr.W(l['data'], 0) == 5000 and sg(xr.W(l['data'], 1)) == 100)}; selected: {len(sel)}")
    rows = []
    for l in sel:
        b = int(l["blockNumber"], 16); d = l["data"]
        t = xr.call("base_t", "eth_getTransactionByHash", [l["transactionHash"]])
        B = xr.call("base_t", "eth_getBlockByNumber", [hex(b), False])
        c0, c1 = "0x" + l["topics"][2][-40:], "0x" + l["topics"][3][-40:]
        tok = c1 if c0 == Z else c0
        hook = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
        lc = xr.call("base_t", "eth_getCode", [t["to"], hex(b)]) if t.get("to") else "0x"
        hc = xr.call("base_t", "eth_getCode", [hook, hex(b)])
        r = dict(block=b, ts=int(B["timestamp"], 16), tx=l["transactionHash"], frm=t["from"].lower(), to=(t.get("to") or "").lower(),
                 sel=t["input"][:10], nbytes=(len(t["input"]) - 2) // 2, value=int(t["value"], 16), launcher_hash=chash(lc),
                 launcher_size=(len(lc) - 2) // 2, pool=l["topics"][1], c0=c0, c1=c1, token=tok, token_hash=th.get(tok, "-"),
                 fee=xr.W(d, 0), ts_=sg(xr.W(d, 1)), hook=hook, hook_hash=chash(hc), hook_size=(len(hc) - 2) // 2,
                 flags=flags(hook), sqrtP=xr.W(d, 3), tick=sg(xr.W(d, 4)), tx_index=int(l["transactionIndex"], 16))
        rows.append(r)
    rows.sort(key=lambda r: r["block"])
    print("\n| # | time UTC | block | launch tx | from | to (launcher) | sel | B | launcher hash | token | token hash | fee/ts | hook | hook flags | sqrtPriceX96 | tick |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        print(f"| {i} | {time.strftime('%H:%M:%S', time.gmtime(r['ts']))} | {r['block']} | {r['tx']} | {r['frm']} | {r['to']} | {r['sel']} | {r['nbytes']} | "
              f"{r['launcher_hash']} ({r['launcher_size']} B) | {r['token']} | {r['token_hash']} | {r['fee']}/{r['ts_']} | {r['hook']} | "
              f"0x{int(r['hook'], 16) & 0x3FFF:04x} {'+'.join(r['flags']) or 'none'} | {r['sqrtP']} | {r['tick']} |")
    print("\nnotes per pool: pool id, currency0, value of the launch tx, hook code size/hash, tx index")
    for r in rows:
        print(f"  {r['block']}: pool {r['pool']} c0 {r['c0']} value {r['value']} hook code {r['hook_size']} B {r['hook_hash']} idx {r['tx_index']}")
    json.dump(dict(head=head, head_ts=hts, rows=rows), open("/home/user/v2pons/research/session_oct14/base2433/b09_census.json", "w"), indent=1)
    print(f"\nrequests: {xr.STATS}")


if __name__ == "__main__":
    main()
