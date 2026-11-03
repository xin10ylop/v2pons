#!/usr/bin/env python3
"""bnbhush.py: can holders of BNB's 4,050 B crowd tokens move them now? The token keeps a team list (isTeam(address), setTeam) and two
Hush() reverts in its transfer path: one reached only when tx.gasprice and block.coinbase are both non-zero (a real transaction; a
default eth_call has both at 0), one on the team mapping. pose(true) sets a "veiled" flag and a horizon of now + 7 days. eth_simulateV1 at
the latest block of a 1-unit transfer from team wallets, the three outsiders who sold at 3-4.5x with zero-gas-price transactions, and
outsiders who never sold, each run as a default simulation (gas price 0) and as a real transaction would run (0.1 gwei, the block's real
coinbase). Read-only."""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
URL = "https://bsc-dataseed.bnbchain.org"
ad = lambda a: "0" * 24 + a.lower().replace("0x", "")
CASES = [  # (token, holder, what)
    ("0xccb9ecafc", "0x1c90da18", "outsider, sold 3.2x"), ("0x01f808213", "0x0f2f46da", "outsider, sold 3.6x"), ("0x03fd96270", "0xb27ad847", "outsider, sold 4.5x"),
    ("0x8778fbb", "0xf7093a4d", "outsider, 0.16 BNB, never sold"), ("0x0ab5a9e", "0xebd89f88", "outsider, 0.02 BNB, never sold"),
    ("0x267c279", "0x90ec45a1", "outsider, 0.014 BNB, never sold"), ("0xbb1a1f9", "0x93c22146", "outsider, 0.02 BNB, never sold"),
    ("0x8778fbb", "0xc0c84518", "team (crew)")]


def rpc(m, p):
    r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                 {"Content-Type": "application/json", "User-Agent": "curl/8"}), timeout=60).read())
    if "error" in r:
        raise RuntimeError(str(r["error"])[:300])
    return r["result"]


def main():
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/line_bnb_full.json")))
    blk = rpc("eth_getBlockByNumber", ["latest", False]); cb = blk["miner"]
    print(f"latest block {int(blk['number'], 16)}, time {int(blk['timestamp'], 16)}, coinbase {cb}")
    for pid, pre, what in CASES:
        p = next(q for q in d["pools"] if q["id"].startswith("v2:" + pid[:11]) or q["id"].startswith("v2:" + pid))
        holder = next(e[6] for e in p["ev"] if e[6].startswith(pre))
        tok = p["tok"]
        bal = int(rpc("eth_call", [{"to": tok, "data": "0x70a08231" + ad(holder)}, "latest"]), 16)
        team = int(rpc("eth_call", [{"to": tok, "data": "0x24851914" + ad(holder)}, "latest"]), 16)
        so = {holder: {"balance": hex(10 ** 18)}}
        call = {"from": holder, "to": tok, "data": "0xa9059cbb" + ad("0x000000000000000000000000000000000000dEaD") + format(1, "064x")}
        out = []
        for label, c, bo in (("simulated (gas price 0)", call, {}), ("as real (0.1 gwei, real coinbase)", dict(call, gasPrice=hex(10 ** 8), maxFeePerGas=None) , {"feeRecipient": cb})):
            c = {k: v for k, v in c.items() if v is not None}
            if "gasPrice" in c:
                c.pop("gasPrice"); c["maxFeePerGas"] = hex(10 ** 8); c["maxPriorityFeePerGas"] = hex(10 ** 8)
            blocks = [{"stateOverrides": so, "blockOverrides": dict(bo, baseFeePerGas="0x0") if bo else {}, "calls": [c]}]
            r = rpc("eth_simulateV1", [{"blockStateCalls": blocks, "validation": False}, "latest"])[0]["calls"][0]
            err = (r.get("error") or {}); data = err.get("data") or r.get("returnData", "")
            out.append(f"{label}: {'OK' if r['status'] == '0x1' else 'REVERT ' + str(data)[:10] + (' Hush()' if str(data).startswith('0x1887aac7') else '')}")
        print(f"{what:34s} {holder[:10]} team {team} holds {bal > 0} | " + " | ".join(out))


if __name__ == "__main__":
    main()
