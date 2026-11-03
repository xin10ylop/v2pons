#!/usr/bin/env python3
"""ethsim.py POOL_JSON [OFFSETS] [STAKE]: can an outsider sell the Ethereum 1852 B line's tokens? eth_simulateV1 (publicnode, archive) at
the pool's real state just after launch + OFFSET: a fresh wallet buys STAKE ETH through the Uniswap V2 router, approves, and sells it all
back (in the same simulated block, and again 1 and 200 simulated blocks later). Prints each step's success and the ETH back. Read-only."""
import sys, json, urllib.request
URL = "https://ethereum.publicnode.com"; R2 = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"; WETH = "c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
ME = "0x5e11e5e11e5e11e5e11e5e11e5e11e5e11e5e11e"
w = lambda x: format(x, "064x"); ad = lambda a: "0" * 24 + a.lower().replace("0x", "")


def rpc(m, p):
    r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                 {"Content-Type": "application/json", "User-Agent": "curl/8"}), timeout=60).read())
    if "error" in r:
        raise RuntimeError(str(r["error"])[:300])
    return r["result"]


def buy(tok, stake):
    path = w(2) + ad(WETH) + ad(tok)
    return {"from": ME, "to": R2, "value": hex(stake), "data": "0x7ff36ab5" + w(0) + w(0x80) + ad(ME) + w(2 ** 40) + path}


def sell(tok, amt):
    path = w(2) + ad(tok) + ad(WETH)
    return {"from": ME, "to": R2, "data": "0x791ac947" + w(amt) + w(0) + w(0xa0) + ad(ME) + w(2 ** 40) + path}


def run(pool, off, stake):
    tok = pool["tok"]; b = pool["bn"] + off
    so = {ME: {"balance": hex(10 ** 20)}}
    r1 = rpc("eth_simulateV1", [{"blockStateCalls": [{"stateOverrides": so, "calls": [buy(tok, stake), {"from": ME, "to": tok, "data": "0x70a08231" + ad(ME)}]}]}, hex(b)])
    c = r1[0]["calls"]
    if c[0]["status"] != "0x1":
        return f"+{off}: BUY reverted {c[0].get('error')}"
    bal = int(c[1]["returnData"], 16); got = int(c[0]["returnData"][2:][-64:], 16)
    out = [f"+{off}: buy {stake/1e18:g} ETH -> {bal} tokens (router said {got}, {'tax ' + format(1 - bal / got, '.1%') if got and bal != got else 'no buy tax'})"]
    for gap in (0, 1, 200):
        approve = {"from": ME, "to": tok, "data": "0x095ea7b3" + ad(R2) + w(2 ** 256 - 1)}
        eb = {"from": ME, "to": "0x" + "00" * 20, "data": "0x"}
        blocks = [{"stateOverrides": so, "calls": [buy(tok, stake), approve] + ([sell(tok, bal)] if gap == 0 else [])}]
        if gap:
            blocks.append({"blockOverrides": {"number": hex(b + 1 + gap)}, "calls": [sell(tok, bal)]})
        r = rpc("eth_simulateV1", [{"blockStateCalls": blocks, "traceTransfers": True}, hex(b)])
        sc = r[-1]["calls"][-1]
        eth_back = None
        for lg in sc.get("logs", []):          # traceTransfers: ETH transfers appear as logs from 0xeeee..
            if lg["address"].lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" and lg["topics"][2][-40:] == ME[2:]:
                eth_back = int(lg["data"], 16)
        out.append(f"    sell {'same block' if gap == 0 else str(gap) + ' blocks later'}: {'OK' if sc['status'] == '0x1' else 'REVERTED ' + str(sc.get('error'))[:160]}"
                   + (f", ETH back {eth_back/1e18:.6f} ({eth_back/stake - 1:+.1%})" if eth_back else ""))
    return "\n".join(out)


if __name__ == "__main__":
    d = json.load(open(sys.argv[1])); offs = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "3,50,150,400").split(",")]
    stake = int(float(sys.argv[3] if len(sys.argv) > 3 else "0.05") * 1e18)
    for pool in d["pools"][-3:]:
        print(pool["id"], pool["tok"], "burn +", pool.get("burn"))
        for o in offs:
            try:
                print(run(pool, o, stake))
            except Exception as e:
                print(f"+{o}: error {e}")
