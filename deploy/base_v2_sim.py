#!/usr/bin/env python3
"""base_v2_sim.py: the exit test for a Uniswap-V2 pair on Base, nothing sent. An eth_call with a state override puts contracts/V2RoundTrip.sol's
runtime code at one address with ETH; it buys the token through the V2 router with the stake, approves, sells everything back, and returns
the tokens bought, the ETH the sell returned and the constant-product quote for that sell. A token that blocks sells reverts the call (then
a buy-only probe says whether the buy alone works); a sell tax shows as ETH back under the quote.

    python3 deploy/base_v2_sim.py                       # the newest fresh-wallet pair with >= 1 ETH minted in the last 3,000 blocks
    python3 deploy/base_v2_sim.py <pair> [eth] [--block N] [--rpc URL]
    python3 deploy/base_v2_sim.py --all N [eth]           # every such pair created in the last N blocks

A pulled pair is empty at the head: simulate it at a block between its Mint and its Burn (--block). Reads go to the nodereal public
gateway by default (archive state, single requests); mainnet.base.org and base.gateway.tenderly.co also take state overrides."""
import os, sys, json, time, urllib.request, urllib.error
from eth_utils import keccak
import solcx
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RPC = "https://open-platform.nodereal.io/64a9df0874fb4a93b9d0a3849de012d3/base"
ROUTER = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"; FACTORY = "0x8909dc15e40173ff4699343b6eb8132c65e18ec6"; WETH = "0x4200000000000000000000000000000000000006"
HARNESS_AT = "0x" + "a2" * 20; CALLER = "0x" + "c0" * 20
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
T_PC = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex(); T_MINT = "0x" + keccak(text="Mint(address,uint256,uint256)").hex(); T_BURN = "0x" + keccak(text="Burn(address,uint256,uint256,address)").hex()
W = lambda d, i: int(d[2+64*i:2+64*(i+1)], 16); word = lambda x: ("%064x" % x) if isinstance(x, int) else x[2:].lower().zfill(64)


def rpc(url, m, p):
    for i in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60))
            if "result" in r: return r["result"]
            return {"error": r.get("error")}
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(4); continue
            return {"error": "HTTP %d %s" % (e.code, e.read()[:120])}
        except Exception as e:
            time.sleep(2); last = repr(e)
    return {"error": last}


def harness_runtime():
    src = open(os.path.join(ROOT, "contracts", "V2RoundTrip.sol")).read()
    if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]: solcx.install_solc("0.8.26")
    res = solcx.compile_standard({"language": "Solidity", "sources": {"V2RoundTrip.sol": {"content": src}}, "settings": {"optimizer": {"enabled": True, "runs": 200}, "evmVersion": "cancun",
                                  "outputSelection": {"*": {"V2RoundTrip": ["evm.deployedBytecode.object", "evm.methodIdentifiers"]}}}}, solc_version="0.8.26")
    c = res["contracts"]["V2RoundTrip.sol"]["V2RoundTrip"]; return "0x" + c["evm"]["deployedBytecode"]["object"], c["evm"]["methodIdentifiers"]


def simulate(url, pair, stake_wei, block="latest", do_sell=True, code=None, sels=None):
    t0 = rpc(url, "eth_call", [{"to": pair, "data": "0x0dfe1681"}, block]); t1 = rpc(url, "eth_call", [{"to": pair, "data": "0xd21220a7"}, block])
    if isinstance(t0, dict) or isinstance(t1, dict): return {"error": "pair read failed: %s %s" % (t0, t1)}
    token0, token1 = "0x" + t0[-40:], "0x" + t1[-40:]; token = token1 if token0 == WETH else token0
    if WETH not in (token0, token1): return {"error": "not a WETH pair"}
    data = "0x" + sels["roundTrip(address,address,address,uint256,bool)"] + word(ROUTER) + word(WETH) + word(token) + word(stake_wei) + word(1 if do_sell else 0)
    r = rpc(url, "eth_call", [{"from": CALLER, "to": HARNESS_AT, "data": data, "gas": "0x7a1200"}, block, {HARNESS_AT: {"code": code, "balance": hex(stake_wei * 2)}}])
    if isinstance(r, dict): return {"error": r["error"], "token": token}
    return {"token": token, "tokens": W(r, 0), "eth_back": W(r, 1), "quote": W(r, 2)}


def verdict(url, pair, stake_wei, block, code, sels):
    full = simulate(url, pair, stake_wei, block, True, code, sels)
    if "error" not in full:
        eb, q = full["eth_back"], full["quote"]; ratio = eb / q if q else 0
        kind = "SELLABLE" if q and ratio >= 0.97 else ("TAXED %.0f%%" % (100 * (1 - ratio)) if q else "SOLD NOTHING")
        return kind, "buy %.6f ETH -> %d tokens; sell -> %.6f ETH (quote %.6f, %.1f%% of the stake back)" % (stake_wei / 1e18, full["tokens"], eb / 1e18, q / 1e18, 100 * eb / stake_wei), full
    buy = simulate(url, pair, stake_wei, block, False, code, sels)
    if "error" in buy: return "UNREADABLE", "buy and sell both failed: %s" % str(buy["error"])[:200], buy
    return "HONEYPOT", "the buy works (%d tokens) but the sell REVERTS: %s" % (buy["tokens"], str(full["error"])[:160]), full


def recent_pairs(url, back, min_eth):
    head = int(rpc(url, "eth_blockNumber", []), 16); out = []
    for a in range(head - back, head + 1, 5000):
        for pos in (1, 2):
            w32 = "0x" + word(WETH)
            ls = rpc(url, "eth_getLogs", [{"address": FACTORY, "topics": [T_PC, w32, None] if pos == 1 else [T_PC, None, w32], "fromBlock": hex(a), "toBlock": hex(min(a + 4999, head))}])
            for l in (ls if isinstance(ls, list) else []):
                pair = "0x" + l["data"][2:66][-40:]; bn = int(l["blockNumber"], 16)
                ms = rpc(url, "eth_getLogs", [{"address": pair, "topics": [T_MINT], "fromBlock": hex(bn), "toBlock": hex(bn + 5)}])
                if not ms: continue
                m = ms[0]; eth = (W(m["data"], 0) if pos == 1 else W(m["data"], 1)) / 1e18
                if eth < min_eth: continue
                tx = rpc(url, "eth_getTransactionByHash", [l["transactionHash"]]); bs = rpc(url, "eth_getLogs", [{"address": pair, "topics": [T_BURN], "fromBlock": hex(bn), "toBlock": hex(head)}])
                out.append({"pair": pair, "bn": bn, "eth": eth, "creator": tx["from"], "nonce": int(tx["nonce"], 16), "burn": int(bs[0]["blockNumber"], 16) if bs else None})
    return sorted(out, key=lambda p: p["bn"])


def main(argv):
    url = RPC; stake = 0.01; block = "latest"; pairs = None; back = None
    if "--rpc" in argv: url = argv[argv.index("--rpc") + 1]
    if "--block" in argv: block = hex(int(argv[argv.index("--block") + 1]))
    if "--all" in argv: back = int(argv[argv.index("--all") + 1])
    pos = [a for a in argv[1:] if not a.startswith("--") and a not in (url, str(back)) and not (argv.index(a) > 0 and argv[argv.index(a) - 1] in ("--block", "--rpc", "--all"))]
    if pos and pos[0].startswith("0x"): pairs = [{"pair": pos[0]}]; pos = pos[1:]
    if pos: stake = float(pos[0])
    code, sels = harness_runtime()
    if pairs is None:
        found = recent_pairs(url, back or 3000, 1.0)
        if not found: sys.exit("no fresh-wallet pair with >= 1 ETH in the window")
        pairs = found if back else [found[-1]]
    for p in pairs:
        blk = block
        if block == "latest" and p.get("burn"): blk = hex(p["bn"] + 30)   # pulled already: simulate 30 blocks after the mint
        kind, text, raw = verdict(url, p["pair"], int(stake * 1e18), blk, code, sels)
        print("%s  pair %s%s  at %s: %s" % (kind.ljust(12), p["pair"], "  (%.2f ETH, creator nonce %s, %s)" % (p["eth"], p.get("nonce"), "pulled at +%d" % (p["burn"] - p["bn"]) if p.get("burn") else "open") if "eth" in p else "", blk, text))


if __name__ == "__main__":
    main(sys.argv)
