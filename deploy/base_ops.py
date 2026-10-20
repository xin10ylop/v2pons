#!/usr/bin/env python3
"""base_ops.py: the Base line's money, from the box: the wallet (BASE_WALLET, its key in /etc/flip/base.key) and its FlipRelay (BASE_RELAY),
both in /etc/flip/base.env (docs/BASE.md section 1; RUNBOOK 4l).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py status               # balances, nonce, the relay's code/owner/pm, today's trades (no key read)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py deposit 0.004        # ETH from the wallet into the relay (the stakes)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py withdraw [0.002]     # relay ETH back to the wallet (no amount = all of it)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py sweep 0xTOKEN        # a token left in the relay back to the wallet
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py payout 0xADDR 0.01   # ETH from the wallet to an address of yours (asks for a typed yes)

status reads only (the key file is never opened): the service and its mode, the wallet's ETH and nonce, the relay's ETH (in stakes of
BASE_STAKE_ETH), its code against FlipRelay's for this wallet and its owner() and pm(), the halt file, the open positions, and today's
trades (UTC) from the log (BASE_LOG_PATH). deposit, withdraw, sweep and payout sign on the box: each refuses while flip-base is active
(stop it first: same wallet, same nonce) or another process holds the key file's lock (base_wallet.py's docstring), checks that the key is
BASE_WALLET, that the chain is 8453 and (but payout) that BASE_RELAY is a FlipRelay of this wallet, then sends one type-2 transaction
(gas = the estimate x 1.3, maxFeePerGas = 2 x the base fee + the priority fee) to every BASE_SEND_URLS, waits for its receipt and prints the
balances after. The wallet keeps GAS_RESERVE (0.001 ETH, a few hundred trades' gas) through a deposit or a payout. Profit leaves in two
steps: withdraw (relay -> wallet), then payout (wallet -> your own address); base_wallet.py withdraw empties the wallet at the end."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import base_wallet as BW

GAS_RESERVE_WEI = 10 ** 15                                                               # what stays in the wallet for the engine's gas
ETH_USD = float(BW.setting("BASE_ETH_USD", "2570") or 2570)
usd = lambda wei: "$%.2f" % (wei / 1e18 * ETH_USD)


def eth_arg(s, what="the amount"):
    try:
        v = int(round(float(s) * 1e18))
    except (TypeError, ValueError):
        sys.exit(f"{what} is in ETH, e.g. 0.004 (got {s!r})")
    if v <= 0 or v > 10 ** 20:
        sys.exit(f"{what} must be above 0 ETH (and under 100)")
    return v


def relay_check(relay, wallet):
    """(code is FlipRelay's for this wallet, owner() is the wallet, pm() is the PoolManager)"""
    import base_relay_sim                                                                # sets relay_sim.PM to Base's PoolManager
    import relay_sim
    code = BW.rpc("eth_getCode", [relay, "latest"])
    if not code or len(code) <= 2:
        return False, False, False
    owner = BW.rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"]); pm = BW.rpc("eth_call", [{"to": relay, "data": "0x8970cdff"}, "latest"])
    return (code.lower() == relay_sim.relay_runtime(wallet).lower(), ("0x" + owner[-40:]).lower() == wallet,
            ("0x" + pm[-40:]).lower() == base_relay_sim.PM)


def today_trades():
    """today's (UTC) trade_done lines from the log: (live count, live $, dry count, dry mean return)"""
    log = BW.setting("BASE_LOG_PATH", "/var/log/flip/base.jsonl"); day = time.strftime("%Y-%m-%d", time.gmtime())
    live, dry = [], []
    try:
        for line in open(log):
            if '"trade_done"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("ev") != "trade_done" or time.strftime("%Y-%m-%d", time.gmtime(e.get("t") or 0)) != day:
                continue
            (live if e.get("live") and not e.get("dry") else dry).append(e)
    except OSError:
        return None
    rets = [e["ret"] for e in dry if isinstance(e.get("ret"), (int, float))]
    return len(live), sum(e.get("usd") or 0 for e in live), len(dry), (sum(rets) / len(rets) if rets else None)


def status():
    wallet = (BW.setting("BASE_WALLET") or "").lower(); relay = (BW.setting("BASE_RELAY") or "").lower()
    stake = float(BW.setting("BASE_STAKE_ETH", "0.002") or 0.002)
    mode = "live (BASE_DRY_RUN=0)" if BW.live_setting() else "dry (BASE_DRY_RUN=1)"
    print(f"flip-base: {'active' if BW.service_active() else 'stopped'}, {mode} in {BW.ENV_FILE}; reads via {', '.join(BW.host(u) for u in BW.rpc_urls())}")
    if not wallet:
        print(f"wallet: BASE_WALLET is not set in {BW.ENV_FILE} (base_wallet.py makes it; run this with sudo to read the file)"); return
    wb = BW.balance(wallet); n = int(BW.rpc("eth_getTransactionCount", [wallet, "latest"]), 16); np_ = int(BW.rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    print(f"wallet {wallet}: {wb / 1e18:.6f} ETH ({usd(wb)}), nonce {n}{'' if np_ == n else f' ({np_ - n} pending)'}   {BW.EXPLORER}/address/{wallet}")
    if not relay:
        print(f"relay: BASE_RELAY is not set (base_relay_deploy.py --write-env deploys it and writes the line)")
    else:
        rb = BW.balance(relay); oc, oo, op = relay_check(relay, wallet)
        print(f"relay  {relay}: {rb / 1e18:.6f} ETH ({usd(rb)}) = {rb / 1e18 / stake:.1f} stakes of {stake:g} ETH; code "
              f"{'FlipRelay for this wallet' if oc else 'NOT FlipRelay for this wallet'}, owner() {'== wallet' if oo else '!= BASE_WALLET: DO NOT USE'}, "
              f"pm() {'== PoolManager' if op else 'WRONG'}")
    halt = BW.setting("BASE_HALT_FILE") or os.path.join(os.path.dirname(BW.setting("BASE_LOG_PATH", "/var/log/flip/base.jsonl")), "HALTED.base")
    if os.path.exists(halt):
        try:
            why = open(halt).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        print(f"HALTED: {why}  ({halt})")
    try:
        pos = BW.open_positions()
    except SystemExit as e:
        pos = [str(e)]
    print(f"open positions: {len(pos)}" + (f" ({'; '.join(p[:120] for p in pos)})" if pos else ""))
    t = today_trades()
    if t is None:
        print(f"today: no log at {BW.setting('BASE_LOG_PATH', '/var/log/flip/base.jsonl')}")
    else:
        nl, ul, nd, md = t
        print(f"today (UTC): {nl} live trade(s), ${ul:+.2f} against the daily stop of -${float(BW.setting('BASE_DAILY_STOP_USD', '10') or 10):g}; "
              f"{nd} dry trade(s){'' if md is None else ', mean %+.1f%%' % (100 * md)}")


def after(wallet, relay, before=None):
    """the balances after the transaction; a load-balanced node a block behind still shows the old ones, so they are read again for up to
    10 s until one of them has moved (the first Base deposit printed 'relay 0.000000' from such a node)"""
    for i in range(6):
        wb = BW.balance(wallet); rb = BW.balance(relay) if relay else None
        if before is None or (wb, rb) != before or i == 5:
            break
        time.sleep(2)
    print(f"now: wallet {wb / 1e18:.6f} ETH" + (f", relay {rb / 1e18:.6f} ETH" if relay else "") + ("   (a node a block behind: the balances have not moved yet; base_ops.py status in a moment)" if before is not None and (wb, rb) == before else ""))


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        return status()
    if cmd not in ("deposit", "withdraw", "sweep", "payout"):
        sys.exit(__doc__.split("\n\n")[1])
    try:
        return act(cmd, argv[1:])
    finally:
        BW.release_key()


def act(cmd, args):
    usage = {"deposit": "deposit ETH", "withdraw": "withdraw [ETH]", "sweep": "sweep 0xTOKEN", "payout": "payout 0xADDRESS ETH"}[cmd]
    if len(args) != {"deposit": 1, "withdraw": len(args[:1]), "sweep": 1, "payout": 2}[cmd]:
        sys.exit(f"usage: base_ops.py {usage}")
    BW.guard(any_mode=True)
    acct = BW.wallet_account(); wallet = acct.address.lower(); relay = (BW.setting("BASE_RELAY") or "").lower()
    if cmd != "payout":
        if not relay:
            sys.exit(f"BASE_RELAY is not set in {BW.ENV_FILE}: base_relay_deploy.py --write-env first")
        oc, oo, op = relay_check(relay, wallet)
        if not (oc and oo and op):
            sys.exit(f"BASE_RELAY {relay} is not a FlipRelay of this wallet (code {'ok' if oc else 'differs'}, owner {'ok' if oo else 'not the wallet'}, "
                     f"pm {'ok' if op else 'wrong'}): nothing sent; check {BW.ENV_FILE}")
    wb = BW.balance(wallet); rb0 = BW.balance(relay) if relay else None
    if cmd == "deposit":
        amt = eth_arg(args[0])
        if amt + GAS_RESERVE_WEI > wb:
            sys.exit(f"the wallet holds {wb / 1e18:.6f} ETH; with {GAS_RESERVE_WEI / 1e18:g} ETH kept for gas at most {max(0, wb - GAS_RESERVE_WEI) / 1e18:.6f} can go in")
        BW.transact(acct, relay, amt, "0x", label=f"deposit {amt / 1e18:g} ETH ({usd(amt)}) from the wallet into the relay {relay}")
    elif cmd == "withdraw":
        rb = BW.balance(relay); amt = eth_arg(args[0]) if args else 0
        if rb == 0:
            sys.exit(f"the relay {relay} holds no ETH: nothing to withdraw")
        if amt > rb:
            sys.exit(f"the relay holds {rb / 1e18:.6f} ETH, less than {amt / 1e18:g}")
        if BW.open_positions():
            print("(an open position is in the positions file: its tokens stay in the relay and flip-base sells them at its next start; the ETH can go)")
        BW.transact(acct, relay, 0, "0x2e1a7d4d" + BW.w(amt), label=f"withdraw {(amt or rb) / 1e18:.6f} ETH from the relay to the wallet")
    elif cmd == "sweep":
        token = BW.address_arg(args[0], "the token")
        if not BW.has_code(token):
            sys.exit(f"{token} has no code on Base: not a token")
        if any(token in p.lower() for p in BW.open_positions()):
            sys.exit("the positions file holds this token as an open position: flip-base sells it at its next start (sudo systemctl start flip-base)")
        bal = BW.word(BW.rpc("eth_call", [{"to": token, "data": "0x70a08231" + BW.a(relay)}, "latest"]))
        if bal == 0:
            sys.exit(f"the relay holds none of {token}: nothing to sweep")
        BW.transact(acct, relay, 0, "0x01681a62" + BW.a(token), label=f"sweep {bal} raw units of {token} from the relay to the wallet")
        print("(the tokens are now in the wallet; a pulled pool's token is worth nothing, and nothing here sells it)")
    else:
        to, amt = BW.address_arg(args[0], "the destination"), eth_arg(args[1])
        if to in (wallet, relay, BW.ZERO):
            sys.exit("that is our own wallet or relay (or the zero address): deposit/withdraw move money between those")
        if amt + GAS_RESERVE_WEI > wb:
            sys.exit(f"the wallet holds {wb / 1e18:.6f} ETH; after {GAS_RESERVE_WEI / 1e18:g} ETH kept for gas at most {max(0, wb - GAS_RESERVE_WEI) / 1e18:.6f} "
                     f"can go out (withdraw from the relay first: base_ops.py withdraw; or empty the wallet at the end: base_wallet.py withdraw)")
        kind = "a contract (or an account with code)" if BW.has_code(to) else "a plain account"
        BW.transact(acct, to, amt, "0x", label=f"payout {amt / 1e18:g} ETH ({usd(amt)}) from the wallet {wallet} to {to} ({kind}) on Base (chain {BW.CHAIN_ID})",
                    confirm=lambda: BW.ask("type yes to send: ").strip().lower() == "yes")
    after(wallet, relay, (wb, rb0))


if __name__ == "__main__":
    main(sys.argv[1:])
