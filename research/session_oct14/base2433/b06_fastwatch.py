"""Fast Base watch for the 2.433 operator (REPORT_BASE2433.md): polls Base every POLL seconds and EXITS on the first sign of a run, so the
session that started it in the background is woken at once. Read-only, public endpoint (publicnode serves fresh logs).

A sign is any of:
  - a Uniswap v4 Initialize at fee 5000 / tick spacing 100 (the operator's pool setup; 3 in the 24 h to Oct 14 10:10, all its own);
  - a launch transaction calling c3e0ff3d (260 B) on any contract (the operator's per-launch launcher);
  - the 31 buyer wallets' nonce sum, the collector 0x8f79d153's nonce, or the 3 Base launch wallets' nonces changing (read every WALLET_EVERY s);
  - the collector's balance dropping by more than 0.01 ETH.
State (the last block read, the last nonces) is kept in b06_state.json so a restart does not alert twice on the same event.
usage: python3 b06_fastwatch.py [max_minutes, default 115]   (exit 0 with "ALERT ..." lines, or "QUIET ..." when the time runs out)"""
import json, os, sys, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__)); STATE = os.path.join(HERE, "b06_state.json")
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
BUYERS = [a.lower() for a, n, b in json.load(open(SRC + "c16_rh_wallets_xchain.json"))["buyers_bsc"]]
COLLECT = "0x8f79d153630b327cc84487804f152972cce93cb4"
LAUNCH3 = ["0x4d40df2e5fb79b8b4cfc03ca9451a3462e813084", "0x505b452dc968ff72aade79fcd87fd31552d212e3", "0x72d0cac5017dd7e2bcf3cfbde9079eae796c163c"]
POLL = 12; WALLET_EVERY = 60
MAXMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 115
SELFTEST = os.environ.get("B06_SELFTEST") == "1"                                 # alert on any Initialize, keep no state (a test of the path)
if SELFTEST: STATE = os.path.join(HERE, "b06_selftest_state.json")


def wallets():
    addrs = BUYERS + [COLLECT] + LAUNCH3
    ns = xr.batch("base", "eth_getTransactionCount", [[a, "latest"] for a in addrs], n=20)
    bal = int(xr.batch("base", "eth_getBalance", [[COLLECT, "latest"]], n=1)[0], 16) / 1e18
    ns = [int(x, 16) for x in ns]
    return {"buyers31": sum(ns[:31]), "collect_nonce": ns[31], "collect_eth": bal, "launch3": sum(ns[32:])}


def main():
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16)
    last = max(st.get("last", head - 30), head - 500)                         # never reach back past publicnode's log window
    w0 = st.get("wallets") or wallets()
    t_end = time.time() + MAXMIN * 60; t_w = time.time()
    print(time.strftime("%H:%M:%S", time.gmtime()), f"watching Base from block {last + 1}; wallets {w0}", flush=True)
    alerts = []
    while time.time() < t_end and not alerts:
        try:
            head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16)
            if head > last:
                lo = last + 1
                for s in range(lo, head + 1, 400):
                    for l in xr.batch("base", "eth_getLogs", [[{"address": PM, "topics": [T_INIT], "fromBlock": hex(s), "toBlock": hex(min(s + 399, head))}]], n=1)[0] or []:
                        d = l["data"]; fee, ts = int(d[2:66], 16), int(d[66:130], 16)
                        tx = xr.batch("base", "eth_getTransactionByHash", [[l["transactionHash"]]], n=1)[0] or {}
                        sel = (tx.get("input") or "")[:10]; n = (len(tx.get("input") or "0x") - 2) // 2
                        if (fee, ts) == (5000, 100) or sel == "0xc3e0ff3d" or SELFTEST:
                            c0, c1 = "0x" + l["topics"][2][-40:], "0x" + l["topics"][3][-40:]
                            alerts.append(f"ALERT launch block {int(l['blockNumber'], 16)} fee {fee} ts {ts} from {tx.get('from')} to {tx.get('to')} "
                                          f"{sel} {n} B token {c1 if c0 == '0x' + '0' * 40 else c0} hook 0x{d[2 + 64 * 2 + 24: 2 + 64 * 3]} tx {l['transactionHash']}")
                last = head
            if time.time() - t_w >= WALLET_EVERY:
                t_w = time.time(); w = wallets()
                for k in ("buyers31", "collect_nonce", "launch3"):
                    if w[k] != w0[k]: alerts.append(f"ALERT wallets {k} {w0[k]} -> {w[k]} (collector {w0['collect_eth']:.4f} -> {w['collect_eth']:.4f} ETH)")
                if w0["collect_eth"] - w["collect_eth"] > 0.01 and not any("collect" in a for a in alerts):
                    alerts.append(f"ALERT wallets collector balance {w0['collect_eth']:.4f} -> {w['collect_eth']:.4f} ETH")
                w0 = w
        except Exception as e:                                                   # one failed poll never ends the watch
            print(time.strftime("%H:%M:%S", time.gmtime()), "poll error:", str(e)[:120], flush=True)
        json.dump({"last": last, "wallets": w0, "t": time.time()}, open(STATE, "w"))
        if not alerts: time.sleep(POLL)
    stamp = time.strftime("%m-%d %H:%M:%S UTC", time.gmtime())
    if alerts:
        print("\n".join(alerts)); print(f"{stamp}: {len(alerts)} alert(s); state at block {last}")
    else:
        print(f"QUIET {stamp}: nothing from the operator on Base up to block {last}; wallets {w0}")


if __name__ == "__main__":
    main()
