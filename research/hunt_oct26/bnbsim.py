#!/usr/bin/env python3
"""bnbsim.py [STAKE]: can an outsider sell BNB's 4,050 B crowd tokens (team list, "Denied()")? Finds the line's live pools (PancakeSwap V2
pairs created in the last LOOK blocks whose token has 4,050 bytes of code and an isTeam(address) view), then eth_simulateV1 at the latest
block (BNB has no free archive state): a fresh wallet buys STAKE BNB through the PancakeSwap V2 router, approves, and sells it all at once,
again with the block clock moved 1, 5 and 30 minutes on. Nov 3 noon: no live pool (the line stopped on Nov 2 at about 15:00 UTC); kept for
its return. Note bnbhush.py: the token treats a zero gas price differently, so a default simulation may not show a real sell's fate.
Read-only."""
import sys, json, os, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H
URL = "https://bsc-dataseed.bnbchain.org"; R = "0x10ed43c718714eb63d5aa57b78b54704e256024e"; WN = "bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
FACT = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"; ME = "0x5e11e5e11e5e11e5e11e5e11e5e11e5e11e5e11e"
STAKE = int(float(sys.argv[1] if len(sys.argv) > 1 else "0.05") * 1e18); LOOK = int(os.environ.get("LOOK", "4000"))
w = lambda x: format(x, "064x"); ad = lambda a: "0" * 24 + a.lower().replace("0x", "")


def rpc(m, p):
    r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                 {"Content-Type": "application/json", "User-Agent": "curl/8"}), timeout=60).read())
    if "error" in r:
        raise RuntimeError(str(r["error"])[:300])
    return r["result"]


def sim(blocks):
    return rpc("eth_simulateV1", [{"blockStateCalls": blocks}, "latest"])


def main():
    head = int(rpc("eth_blockNumber", []), 16); ts = int(rpc("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)
    logs = H.logs("bnb", head - LOOK, head, [H.T_PC2], FACT)
    live = []
    for l in logs:
        t0, t1 = "0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]
        tok = t1 if t0[2:] == WN else t0
        code = rpc("eth_getCode", [tok, "latest"])
        if (len(code) - 2) // 2 == 4050 and "24851914" in code:
            live.append((int(l["blockNumber"], 16), tok, "0x" + l["data"][2 + 24:2 + 64]))
    print(f"head {head}: {len(live)} live pools of the 4,050 B line in the last {LOOK} blocks")
    for bn, tok, pair in live[-4:]:
        print(f"\n{pair} token {tok} created {head - bn} blocks ago")
        so = {ME: {"balance": hex(10 ** 20)}}
        buy = {"from": ME, "to": R, "value": hex(STAKE), "data": "0x7ff36ab5" + w(0) + w(0x80) + ad(ME) + w(2 ** 40) + w(2) + ad(WN) + ad(tok)}
        bal = {"from": ME, "to": tok, "data": "0x70a08231" + ad(ME)}
        r = sim([{"stateOverrides": so, "calls": [buy, bal]}])[0]["calls"]
        if r[0]["status"] != "0x1":
            print("  buy reverted:", (r[0].get("error") or {}).get("message")); continue
        q = int(r[1]["returnData"], 16); print(f"  buy {STAKE/1e18:g} BNB -> {q} tokens")
        appr = {"from": ME, "to": tok, "data": "0x095ea7b3" + ad(R) + w(2 ** 256 - 1)}
        sell = {"from": ME, "to": R, "data": "0x791ac947" + w(q) + w(0) + w(0xa0) + ad(ME) + w(2 ** 40) + w(2) + ad(tok) + ad(WN)}
        for gap in (0, 60, 300, 1800):
            blocks = [{"stateOverrides": so, "calls": [buy, appr] + ([sell] if gap == 0 else [])}]
            if gap:
                blocks.append({"blockOverrides": {"time": hex(ts + gap)}, "calls": [sell]})
            try:
                res = sim(blocks)
                sc = res[-1]["calls"][-1]
                print(f"  sell {'at once' if gap == 0 else str(gap) + ' s later'}: {'OK' if sc['status'] == '0x1' else 'REVERTED ' + str((sc.get('error') or {}).get('message'))[:120]}")
            except RuntimeError as e:
                print(f"  sell {gap} s later: error {e}")


if __name__ == "__main__":
    main()
