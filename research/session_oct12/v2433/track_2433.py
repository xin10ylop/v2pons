"""Track the 2.433 operator's wallets after the Oct 12 shutdown (REPORT_2433STOP.md), read-only on the public RPC.

The set: the hub 0x6c3bd8f6 (the prepared next launch wallet that collected the line's money at 02:12 and bridged 9.3 ETH to Ethereum
at 13:08), the line's 31 buyer wallets and the retired launch wallets that swept into it (read from wallets/w05_hub_inflows.out).
Each run reads every wallet's nonce and balance, compares them with the last run (track_state.json beside this file) and prints what
moved. Any outgoing transaction (a nonce change) or a balance over 0.005 ETH is a sign the operator is coming back. The node keeps no
historical state, so the script reports that something moved, not what it was: a full-block scan around the time finds the transaction.

Usage: python3 research/session_oct12/v2433/track_2433.py        (prints the changes; writes the new state)
       python3 research/session_oct12/v2433/track_2433.py --dry  (prints, writes nothing)"""
import json, os, re, sys, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "track_state.json")
HUB = "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"
BOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
LIVE_ETH = 0.005                                                                     # a balance above this is money parked to be used


def wallets():
    """the hub, then every wallet that swept into it at 02:12-02:13 (the 31 buyers have nonces in the tens of thousands)"""
    out = {HUB: "hub (prepared launch wallet, bridged 9.3 ETH out)"}
    for line in open(os.path.join(HERE, "wallets", "w05_hub_inflows.out")):
        m = re.search(r"to (0x[0-9a-f]{40}) -> " + HUB + r" [0-9.e-]+ nonce (\d+)", line)
        if m and m.group(1) not in out:
            out[m.group(1)] = "buyer" if int(m.group(2)) > 1000 else "launch wallet"
    return out


def main():
    dry = "--dry" in sys.argv
    ws = wallets(); addrs = list(ws)
    for _ in range(5):                                                               # a load-balanced node may not have its own head yet
        b = rpc("eth_getBlockByNumber", ["latest", False])
        if b:
            break
        time.sleep(1)
    head, t_head = int(b["number"], 16), int(b["timestamp"], 16)
    res = batch([("eth_getTransactionCount", [a, "latest"]) for a in addrs] + [("eth_getBalance", [a, "latest"]) for a in addrs]
                + [("eth_getTransactionCount", [BOT_ROUTER, "latest"])])
    now = {a: {"nonce": int(res[i], 16), "eth": int(res[len(addrs) + i], 16) / 1e18} for i, a in enumerate(addrs)}
    router_nonce = int(res[-1], 16)
    old = json.load(open(STATE)) if os.path.exists(STATE) else None
    print("2.433 operator wallets at block %d (%s UTC): %d wallets (%d buyers, %d launch wallets, the hub)" % (
        head, time.strftime("%m-%d %H:%M", time.gmtime(t_head)), len(addrs), sum(v == "buyer" for v in ws.values()), sum(v == "launch wallet" for v in ws.values())))
    h = now[HUB]; print("  hub %s: nonce %d, %.6f ETH" % (HUB, h["nonce"], h["eth"]))
    print("  all wallets together: %.6f ETH; bot router nonce %d" % (sum(v["eth"] for v in now.values()), router_nonce))
    moved = []
    for a in addrs:
        o = (old or {}).get("wallets", {}).get(a)
        n = now[a]
        if o and (n["nonce"] != o["nonce"] or abs(n["eth"] - o["eth"]) > 1e-6):
            moved.append("  MOVED %s (%s): nonce %d -> %d, %.6f -> %.6f ETH" % (a, ws[a], o["nonce"], n["nonce"], o["eth"], n["eth"]))
        elif n["eth"] > LIVE_ETH:
            moved.append("  FUNDED %s (%s): %.6f ETH at nonce %d" % (a, ws[a], n["eth"], n["nonce"]))
    if old is None:
        print("  first run: state saved, nothing to compare")
    elif moved:
        print("  SINCE THE LAST RUN (%s UTC):" % time.strftime("%m-%d %H:%M", time.gmtime(old["t_head"])))
        print("\n".join(moved))
    else:
        print("  nothing moved since %s UTC (block %d)" % (time.strftime("%m-%d %H:%M", time.gmtime(old["t_head"])), old["head"]))
    if not dry:
        json.dump({"head": head, "t_head": t_head, "router_nonce": router_nonce, "wallets": now}, open(STATE, "w"), indent=0, sort_keys=True)


if __name__ == "__main__":
    main()
