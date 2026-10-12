#!/usr/bin/env python3
"""relay_ops.py: the flip relay's money, from the box.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status              # wallet and relay balances, nonce, owner, today's trades
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.01        # ETH from the wallet into the relay (the stake)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw [0.005]    # relay ETH back to the wallet (no amount = all)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py sweep 0xTOKEN       # a token left in the relay back to the wallet
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py payout 0xADDR 0.1   # ETH from the wallet to an outside address (asks for a yes; --yes skips)
The V3 relay (RELAY_V3 in the env file, deploy/relay_v3_deploy.py; status shows it when it is set):
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.01     # ETH from the wallet into the V3 relay
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw_v3 [0.005] # V3 relay ETH back to the wallet (no amount = all)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py sweep_v3 0xTOKEN [N] # a token (or WETH) in the V3 relay back to the wallet: all of it,
                                                                                     # or N raw units (for a token whose transfers are capped)
The _v3 commands first check that RELAY_V3's code is FlipRelayV3's for this wallet, byte for byte, and that its owner() is the wallet.
Stop the engine before deposit/withdraw/sweep/payout and their _v3 forms (same wallet, same nonce). Profit leaves in two steps: withdraw
(relay -> wallet), then payout (wallet -> your own address); keep about 0.003 ETH in the wallet for gas."""
import json, os, subprocess, sys, time
from eth_account import Account
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay_sim
ENV = "/etc/flip/engine.env"; word = relay_sim.word; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"


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


GAS_RESERVE_WEI = int(0.003e18)                      # what stays in the wallet for the engine's gas (about a day at 300 trades)


def payout(acct, wallet, relay, args, yes, rpc, relay_v3=""):
    """plain ETH from the wallet to an outside address, after the checks: a valid address (a mixed-case one must pass its checksum), not our
    own wallet or relay, an amount above 0 that leaves the gas reserve, and a typed yes (or --yes)"""
    from eth_utils import is_address, is_checksum_address, to_checksum_address
    if len(args) != 2:
        sys.exit("usage: relay_ops.py payout 0xADDRESS ETH_AMOUNT [--yes]")
    to, amt_s = args
    if not is_address(to) or (to != to.lower() and to[2:] != to[2:].upper() and not is_checksum_address(to)):
        sys.exit(f"{to} is not a valid address (a mixed-case address must pass its checksum): check it character by character")
    to = to_checksum_address(to)
    if to.lower() in (wallet, relay, relay_v3):
        sys.exit("that is our own wallet or relay: use deposit/withdraw (deposit_v3/withdraw_v3) for those")
    try:
        amt = int(float(amt_s) * 1e18)
    except ValueError:
        sys.exit(f"{amt_s} is not an amount in ETH")
    if amt <= 0:
        sys.exit("the amount must be above 0")
    bal = int(rpc("eth_getBalance", [wallet, "latest"]), 16); gp = int(rpc("eth_gasPrice", []), 16); fee = 21000 * gp * 2
    if amt + fee + GAS_RESERVE_WEI > bal:
        sys.exit(f"the wallet holds {bal / 1e18:.6f} ETH; after {GAS_RESERVE_WEI / 1e18:g} ETH kept for gas at most {max(0, bal - fee - GAS_RESERVE_WEI) / 1e18:.6f} ETH can go out "
                 f"(withdraw from the relay first: relay_ops.py withdraw <eth>)")
    code = rpc("eth_getCode", [to, "latest"])
    kind = "a contract" if len(code) > 2 else "a plain address"
    print(f"send {amt / 1e18:.6f} ETH from the wallet {wallet} to {to} ({kind}) on Robinhood Chain (chain id 4663); {(bal - amt - fee) / 1e18:.6f} ETH stays")
    if not yes and input("type yes to send: ").strip().lower() != "yes":
        sys.exit("not sent")
    send(acct, to, amt, "0x", rpc)


def v3_ops(cmd, acct, wallet, relay_v3, rpc):
    """deposit_v3 <eth>, withdraw_v3 [eth], sweep_v3 <token> [raw amount] on the V3 relay, after checking that RELAY_V3's code is the
    artifact's runtime for this wallet byte for byte (contracts/FlipRelayV3.json with the owner filled in) and that its owner() is the wallet"""
    import relay_v3_sim
    if acct.address.lower() != wallet or not relay_v3:
        sys.exit("WALLET/PRIVATE_KEY/RELAY_V3 not consistent in the env file")
    if rpc("eth_getCode", [relay_v3, "latest"]).lower() != relay_v3_sim.relay_v3_runtime(wallet).lower():
        sys.exit(f"the code at RELAY_V3 {relay_v3} is not FlipRelayV3's for this wallet (contracts/FlipRelayV3.json, owner = WALLET): "
                 f"check the env file and the repository's version")
    owner = rpc("eth_call", [{"to": relay_v3, "data": "0x8da5cb5b"}, "latest"])
    if ("0x" + owner[-40:]).lower() != wallet:
        sys.exit(f"RELAY_V3 {relay_v3} is not a relay owned by the wallet: check the env file")
    if cmd == "deposit_v3":
        if len(sys.argv) < 3:
            sys.exit("usage: relay_ops.py deposit_v3 ETH_AMOUNT")
        send(acct, relay_v3, int(float(sys.argv[2]) * 1e18), "0x", rpc)
    elif cmd == "withdraw_v3":
        amt = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 0
        send(acct, relay_v3, 0, "0x2e1a7d4d" + word(amt), rpc)
    else:
        if len(sys.argv) < 3 or (len(sys.argv) > 3 and not sys.argv[3].isdigit()):
            sys.exit("usage: relay_ops.py sweep_v3 0xTOKEN [RAW_AMOUNT]   (a whole number of the token's smallest units; none = all)")
        send(acct, relay_v3, 0, "0x6ea056a9" + word(sys.argv[2]) + word(int(sys.argv[3]) if len(sys.argv) > 3 else 0), rpc)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"; e = env(); relay_sim.RPC = e.get("RPC_URL") or relay_sim.RPC; rpc = relay_sim.rpc
    wallet = e.get("WALLET", "").lower(); relay = e.get("RELAY", "").lower()
    if cmd == "status":
        wb = int(rpc("eth_getBalance", [wallet, "latest"]), 16) if wallet else 0; nonce = int(rpc("eth_getTransactionCount", [wallet, "pending"]), 16) if wallet else 0
        print(f"wallet {wallet}: {wb / 1e18:.6f} ETH, nonce {nonce}")
        if relay:
            rb = int(rpc("eth_getBalance", [relay, "latest"]), 16); owner = rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"])
            print(f"relay {relay}: {rb / 1e18:.6f} ETH (stake {e.get('STAKE_ETH', '?')}), owner 0x{owner[-40:]} {'== wallet' if ('0x' + owner[-40:]).lower() == wallet else '!= WALLET'}")
        relay_v3 = e.get("RELAY_V3", "").lower()
        if relay_v3:
            rb = int(rpc("eth_getBalance", [relay_v3, "latest"]), 16); owner = rpc("eth_call", [{"to": relay_v3, "data": "0x8da5cb5b"}, "latest"])
            weth = int(rpc("eth_call", [{"to": WETH, "data": "0x70a08231" + word(relay_v3)}, "latest"]), 16)
            print(f"V3 relay {relay_v3}: {rb / 1e18:.6f} ETH{f', {weth / 1e18:.6f} WETH' if weth else ''}, owner 0x{owner[-40:]} "
                  f"{'== wallet' if ('0x' + owner[-40:]).lower() == wallet else '!= WALLET'}")
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
    if cmd in ("deposit_v3", "withdraw_v3", "sweep_v3"):
        v3_ops(cmd, acct, wallet, e.get("RELAY_V3", "").lower(), rpc); return
    if acct.address.lower() != wallet or not relay:
        sys.exit("WALLET/PRIVATE_KEY/RELAY not consistent in the env file")
    if cmd == "deposit":
        send(acct, relay, int(float(sys.argv[2]) * 1e18), "0x", rpc)
    elif cmd == "withdraw":
        amt = int(float(sys.argv[2]) * 1e18) if len(sys.argv) > 2 else 0
        send(acct, relay, 0, "0x2e1a7d4d" + word(amt), rpc)
    elif cmd == "sweep":
        send(acct, relay, 0, "0x01681a62" + word(sys.argv[2]), rpc)
    elif cmd == "payout":
        payout(acct, wallet, relay, [x for x in sys.argv[2:] if not x.startswith("--")], "--yes" in sys.argv, rpc, e.get("RELAY_V3", "").lower())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
