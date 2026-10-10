#!/usr/bin/env python3
"""relay_ops.py: the flip relay's money, from the box.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status              # wallet and relay balances, nonce, owner, today's trades
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.01        # ETH from the wallet into the relay (the stake)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw [0.005]    # relay ETH back to the wallet (no amount = all)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py sweep 0xTOKEN       # a token left in the relay back to the wallet
Stop the engine before deposit/withdraw/sweep (same wallet, same nonce)."""
import json, os, subprocess, sys, time
from eth_account import Account
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay_sim
ENV = "/etc/flip/engine.env"; word = relay_sim.word


def env():
    d = {}
    for line in open(ENV):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); d[k.strip()] = v.split(" #", 1)[0].strip()
    return d


def send(acct, to, value, data, rpc):
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "pending"]), 16); gp = int(rpc("eth_gasPrice", []), 16)
    gas = int(rpc("eth_estimateGas", [{"from": acct.address, "to": to, "value": hex(value), "data": data}]), 16)
    from eth_utils import to_checksum_address
    tx = {"to": to_checksum_address(to), "value": value, "data": data, "gas": int(gas * 1.3), "gasPrice": gp * 2, "nonce": nonce, "chainId": 4663}
    h = rpc("eth_sendRawTransaction", ["0x" + bytes(acct.sign_transaction(tx).raw_transaction).hex()]); rec = None; t0 = time.time()
    while rec is None and time.time() - t0 < 60:
        time.sleep(1); rec = rpc("eth_getTransactionReceipt", [h])
    print(h, "ok" if rec and rec.get("status") == "0x1" else f"status {rec and rec.get('status')}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"; e = env(); relay_sim.RPC = e.get("RPC_URL") or relay_sim.RPC; rpc = relay_sim.rpc
    wallet = e.get("WALLET", "").lower(); relay = e.get("RELAY", "").lower()
    if cmd == "status":
        wb = int(rpc("eth_getBalance", [wallet, "latest"]), 16) if wallet else 0; nonce = int(rpc("eth_getTransactionCount", [wallet, "pending"]), 16) if wallet else 0
        print(f"wallet {wallet}: {wb / 1e18:.6f} ETH, nonce {nonce}")
        if relay:
            rb = int(rpc("eth_getBalance", [relay, "latest"]), 16); owner = rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"])
            print(f"relay {relay}: {rb / 1e18:.6f} ETH (stake {e.get('STAKE_ETH', '?')}), owner 0x{owner[-40:]} {'== wallet' if ('0x' + owner[-40:]).lower() == wallet else '!= WALLET'}")
        log = e.get("LOG_PATH", "/var/log/flip/engine.jsonl")
        if os.path.exists(log):
            day = time.strftime("%Y-%m-%d", time.gmtime()); done = []
            for l in open(log):
                try:
                    ev = json.loads(l)
                except Exception:
                    continue
                if ev.get("ev") == "trade_done" and not ev.get("dry") and time.strftime("%Y-%m-%d", time.gmtime(ev["t"])) == day: done.append(ev)
            print(f"today: {len(done)} live trades, {sum(ev.get('pnl_usd') or 0 for ev in done):+.2f} USD; service {'active' if subprocess.run(['systemctl', 'is-active', '--quiet', 'flip-engine']).returncode == 0 else 'stopped'}")
        return
    if subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"]).returncode == 0:
        sys.exit("stop the engine first: sudo systemctl stop flip-engine")
    acct = Account.from_key(e["PRIVATE_KEY"])
    if acct.address.lower() != wallet or not relay:
        sys.exit("WALLET/PRIVATE_KEY/RELAY not consistent in the env file")
    if cmd == "deposit":
        send(acct, relay, int(float(sys.argv[2]) * 1e18), "0x", rpc)
    elif cmd == "withdraw":
        amt = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 0
        send(acct, relay, 0, "0x2e1a7d4d" + word(amt), rpc)
    elif cmd == "sweep":
        send(acct, relay, 0, "0x01681a62" + word(sys.argv[2]), rpc)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
