#!/usr/bin/env python3
"""base_v2_ops.py: the Base V2 line's money, from the box: the wallet (BASE_V2_WALLET, its key in /etc/flip/base_v2.key) and its FlipRelayV2
(BASE_V2_RELAY), both in /etc/flip/base_v2.env (docs/BASE_V2.md section 1; RUNBOOK 4m).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py status               # the wallet, the relay, the lock, the roster, the positions, today's trades (no key read)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py deposit 0.003        # ETH from the wallet into the relay (the stakes)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py withdraw [0.002]     # relay ETH back to the wallet (no amount = all of it)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py sweep 0xTOKEN        # a token left in the relay back to the wallet
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py payout 0xADDR 0.01   # ETH from the wallet to an address of yours (asks for a typed yes)

status reads only (the key file is opened for the lock test alone and never read): the service and its mode, the wallet's ETH and nonce,
the relay's ETH (in stakes of BASE_V2_STAKE_ETH), its code against FlipRelayV2's for this wallet and its owner(), router() and weth(), the
key file's lock (a live engine holds it), the roster (its count and when it was built), the halt file, the open positions
(base_v2_positions.json) and today's trades (UTC) from the log (BASE_V2_LOG_PATH) against BASE_V2_DAILY_STOP_ETH. deposit, withdraw, sweep
and payout sign on the box: each refuses while flip-base-v2 is active (stop it first: same wallet, same nonce) or another process holds the
key file's lock (base_wallet.py's docstring), checks that the key is BASE_V2_WALLET, that the chain is 8453 and (but payout) that
BASE_V2_RELAY is a FlipRelayV2 of this wallet, then sends one type-2 transaction (gas = the estimate x 1.3, maxFeePerGas = 2 x the base fee
+ the priority fee) to every BASE_V2_SEND_URLS, waits for its receipt and prints the balances after. The wallet keeps GAS_RESERVE (0.001
ETH, a few hundred trades' gas) through a deposit or a payout. Profit leaves in two steps: withdraw (relay -> wallet), then payout (wallet
-> your own address); base_v2_wallet.py withdraw empties the wallet at the end."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import base_v2_wallet as BV
BW = BV.BW

GAS_RESERVE_WEI = 10 ** 15                                                               # what stays in the wallet for the engine's gas
ETH_USD = float(BV.setting("BASE_V2_ETH_USD", "2570") or 2570)
usd = lambda wei: "$%.2f" % (wei / 1e18 * ETH_USD)


def eth_arg(s, what="the amount"):
    try:
        v = int(round(float(s) * 1e18))
    except (TypeError, ValueError):
        sys.exit(f"{what} is in ETH, e.g. 0.003 (got {s!r})")
    if v <= 0 or v > 10 ** 20:
        sys.exit(f"{what} must be above 0 ETH (and under 100)")
    return v


def today_trades():
    """today's (UTC) trade_done lines from the log: (live count, live net wei, live $, dry count, dry mean return); None without a log"""
    log = BV.log_path(); day = time.strftime("%Y-%m-%d", time.gmtime())
    if not os.path.exists(log):
        return None
    live, dry = [], []
    for e in BV.read_log(log, evs=("trade_done",)):
        if time.strftime("%Y-%m-%d", time.gmtime(e.get("t") or 0)) == day:
            (live if e.get("live") and not e.get("dry") else dry).append(e)
    rets = [e["ret"] for e in dry if isinstance(e.get("ret"), (int, float))]
    return len(live), sum(int(e.get("net_wei") or 0) for e in live), sum(e.get("usd") or 0 for e in live), len(dry), (sum(rets) / len(rets) if rets else None)


def roster_state():
    """(count, built) from the roster file; (None, why) when it is not there or not understood"""
    p = BV.roster_file()
    try:
        d = json.load(open(p)); ws = d.get("wallets") if isinstance(d, dict) else None
        if not isinstance(ws, list):
            return None, "not a roster (no wallets list)"
        age = (time.time() - os.path.getmtime(p)) / 86400
        return len(ws), f"built {d.get('built')} ({age:.1f} days ago)"
    except FileNotFoundError:
        return None, "no file (base_v2_roster.py builds it)"
    except Exception as e:
        return None, f"not readable ({type(e).__name__})"


def status():
    wallet = (BV.setting("BASE_V2_WALLET") or "").lower(); relay = (BV.setting("BASE_V2_RELAY") or "").lower()
    stake = float(BV.setting("BASE_V2_STAKE_ETH", "0.02") or 0.02)
    mode = "live (BASE_V2_DRY_RUN=0)" if BW.live_setting() else "dry (BASE_V2_DRY_RUN=1)"
    print(f"flip-base-v2: {'active' if BW.service_active() else 'stopped'}, {mode} in {BV.ENV_FILE}; reads via {', '.join(BW.host(u) for u in BW.rpc_urls())}")
    if not wallet:
        print(f"wallet: BASE_V2_WALLET is not set in {BV.ENV_FILE} (base_wallet.py create {BV.KEY_FILE} {BV.ENV_FILE} makes it, base_v2_setup.sh names it; run this with sudo to read the file)"); return
    wb = BW.balance(wallet); n = int(BW.rpc("eth_getTransactionCount", [wallet, "latest"]), 16); np_ = int(BW.rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    print(f"wallet {wallet}: {wb / 1e18:.6f} ETH ({usd(wb)}), nonce {n}{'' if np_ == n else f' ({np_ - n} pending)'}   {BW.EXPLORER}/address/{wallet}")
    if not relay:
        print("relay: BASE_V2_RELAY is not set (base_v2_relay_deploy.py --write-env deploys it and writes the line)")
    else:
        rb = BW.balance(relay); oc, oo, orr, ow = BV.relay_check(relay, wallet)
        print(f"relay  {relay}: {rb / 1e18:.6f} ETH ({usd(rb)}) = {rb / 1e18 / stake:.1f} stakes of {stake:g} ETH; code "
              f"{'FlipRelayV2 for this wallet' if oc else 'NOT FlipRelayV2 for this wallet'}, owner() {'== wallet' if oo else '!= BASE_V2_WALLET: DO NOT USE'}, "
              f"router() {'== BASE_V2_ROUTER' if orr else 'WRONG'}, weth() {'== BASE_V2_WETH' if ow else 'WRONG'}")
    locked = BV.key_locked()
    print(f"key file {BV.KEY_FILE}: " + ("locked (a live engine, or a money script, holds it)" if locked else "not locked" if locked is False else "not openable (no file, or run this with sudo)"))
    n_r, why = roster_state()
    print(f"roster {BV.roster_file()}: " + (f"{n_r} wallets, {why}" if n_r is not None else why))
    halt = BV.halt_file()
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
        print(f"today: no log at {BV.log_path()}")
    else:
        nl, net, ul, nd, md = t
        print(f"today (UTC): {nl} live trade(s), {net / 1e18:+.6f} ETH (${ul:+.2f}) against the daily stop of -{float(BV.setting('BASE_V2_DAILY_STOP_ETH', '0.15') or 0.15):g} ETH; "
              f"{nd} dry trade(s){'' if md is None else ', mean %+.1f%%' % (100 * md)}")


def after(wallet, relay, before=None):
    """the balances after the transaction; a load-balanced node a block behind still shows the old ones, so they are read again for up to
    10 s until one of them has moved"""
    for i in range(6):
        wb = BW.balance(wallet); rb = BW.balance(relay) if relay else None
        if before is None or (wb, rb) != before or i == 5:
            break
        time.sleep(2)
    print(f"now: wallet {wb / 1e18:.6f} ETH" + (f", relay {rb / 1e18:.6f} ETH" if relay else "") + ("   (a node a block behind: the balances have not moved yet; base_v2_ops.py status in a moment)" if before is not None and (wb, rb) == before else ""))


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
        sys.exit(f"usage: base_v2_ops.py {usage}")
    BV.guard(any_mode=True)
    acct = BW.wallet_account(); wallet = acct.address.lower(); relay = (BV.setting("BASE_V2_RELAY") or "").lower()
    if cmd != "payout":
        if not relay:
            sys.exit(f"BASE_V2_RELAY is not set in {BV.ENV_FILE}: base_v2_relay_deploy.py --write-env first")
        checks = BV.relay_check(relay, wallet)
        if not all(checks):
            sys.exit(f"BASE_V2_RELAY {relay} is not a FlipRelayV2 of this wallet ({BV.relay_words(*checks)}): nothing sent; check {BV.ENV_FILE}")
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
            print("(an open position is in the positions file: its tokens stay in the relay and flip-base-v2 sells them at its next start; the ETH can go)")
        BW.transact(acct, relay, 0, "0x" + BV.SEL["withdraw"] + BW.w(amt), label=f"withdraw {(amt or rb) / 1e18:.6f} ETH from the relay to the wallet")
    elif cmd == "sweep":
        token = BW.address_arg(args[0], "the token")
        if not BW.has_code(token):
            sys.exit(f"{token} has no code on Base: not a token")
        if any(token in p.lower() for p in BW.open_positions()):
            sys.exit("the positions file holds this token as an open position: flip-base-v2 sells it at its next start (sudo systemctl start flip-base-v2)")
        bal = BW.word(BW.rpc("eth_call", [{"to": token, "data": "0x70a08231" + BW.a(relay)}, "latest"]))
        if bal == 0:
            sys.exit(f"the relay holds none of {token}: nothing to sweep")
        BW.transact(acct, relay, 0, "0x" + BV.SEL["sweep"] + BW.a(token), label=f"sweep {bal} raw units of {token} from the relay to the wallet")
        print("(the tokens are now in the wallet; a pulled pair's token is worth nothing, and nothing here sells it)")
    else:
        to, amt = BW.address_arg(args[0], "the destination"), eth_arg(args[1])
        if to in (wallet, relay, BW.ZERO):
            sys.exit("that is our own wallet or relay (or the zero address): deposit/withdraw move money between those")
        if amt + GAS_RESERVE_WEI > wb:
            sys.exit(f"the wallet holds {wb / 1e18:.6f} ETH; after {GAS_RESERVE_WEI / 1e18:g} ETH kept for gas at most {max(0, wb - GAS_RESERVE_WEI) / 1e18:.6f} "
                     f"can go out (withdraw from the relay first: base_v2_ops.py withdraw; or empty the wallet at the end: base_v2_wallet.py withdraw)")
        kind = "a contract (or an account with code)" if BW.has_code(to) else "a plain account"
        BW.transact(acct, to, amt, "0x", label=f"payout {amt / 1e18:g} ETH ({usd(amt)}) from the wallet {wallet} to {to} ({kind}) on Base (chain {BW.CHAIN_ID})",
                    confirm=lambda: BW.ask("type yes to send: ").strip().lower() == "yes")
    after(wallet, relay, (wb, rb0))


if __name__ == "__main__":
    main(sys.argv[1:])
