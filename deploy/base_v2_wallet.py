#!/usr/bin/env python3
"""base_v2_wallet.py: the Base V2 line's wallet on the box (src/base_v2_engine.py, service flip-base-v2; docs/BASE_V2.md section 1):
deploy/base_wallet.py's own helpers pointed at the V2 line's files, /etc/flip/base_v2.key (BASE_V2_KEY_FILE) and /etc/flip/base_v2.env,
with every BASE_* setting read as BASE_V2_*. Nothing here opens the key except base_wallet.py's load_account and hold_key; it is never
printed. Not the Base line's wallet (/etc/flip/base.key), not the flip engine's, not the BNB line's: none of those files is ever opened.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_wallet.py address             # the key file's address (never the key) against BASE_V2_WALLET
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_wallet.py withdraw 0xDEST      # all its ETH on Base to 0xDEST, an account of yours

The wallet itself is made once with base_wallet.py (RUNBOOK 4m step 5):
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py create /etc/flip/base_v2.key /etc/flip/base_v2.env
which writes the key (mode 600, O_EXCL) and the line BASE_WALLET=<address> into /etc/flip/base_v2.env; deploy/base_v2_setup.sh turns that
line into BASE_V2_WALLET= (this module accepts both). withdraw is base_wallet.py's: a plain transfer of the wallet's whole balance less its
fees to 0xDEST once typed a second time; it refuses while flip-base-v2 runs live or any process holds the key file's lock, while
base_v2_positions.json holds an open position, and a destination with code, the wallet itself, the relay or the zero address.

THE LOCK, shared with the engine (base_wallet.py's docstring): an exclusive fcntl.flock on the key file itself, BASE_V2_KEY_FILE. A live
flip-base-v2 takes it at its start and holds it while it runs; withdraw here, base_v2_ops.py's deposit/withdraw/sweep/payout and
base_v2_relay_deploy.py's deployment take it the same way, stop when another process holds it, and hold it until they exit.

The module is the shared helper of base_v2_ops.py, base_v2_relay_deploy.py, base_v2_roster.py and base_v2_results.py (the settings, the
reads, the lock, type-2 sends, the relay's expected runtime from contracts/FlipRelayV2.json); its imports are the standard library only
(base_v2_results.py runs under the system python)."""
import fcntl, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import base_wallet as BW

ENV_FILE = os.environ.get("BASE_V2_ENV_FILE") or "/etc/flip/base_v2.env"
SERVICE = "flip-base-v2"
LOG_DEFAULT = "/var/log/flip/base_v2.jsonl"
ROSTER_DEFAULT = "/etc/flip/base_v2_roster.json"
FACTORY_DEFAULT = "0x8909dc15e40173ff4699343b6eb8132c65e18ec6"                           # Uniswap V2 on Base (BASE_V2_FACTORY)
ROUTER_DEFAULT = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"                            # its router02 (BASE_V2_ROUTER)
WETH_DEFAULT = "0x4200000000000000000000000000000000000006"                              # (BASE_V2_WETH)
PROBE_DEFAULT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"                             # the line's probe (BASE_V2_PROBE)
SEL = {"buy": "1622dbe4", "sell": "6a272462", "withdraw": "2e1a7d4d", "sweep": "01681a62", "owner": "8da5cb5b", "router": "f887ea40", "weth": "3fc8cef3"}
_setting = BW.setting                                                                     # the original: the environment, else the env file's last line


def setting(k, d=None):
    """a V2 setting: BASE_X is read as BASE_V2_X (BASE_V2_X itself as it is), from the environment, else /etc/flip/base_v2.env; the line
    BASE_WALLET= that base_wallet.py create wrote there stands for BASE_V2_WALLET until the setup translates it"""
    k2 = k if k.startswith("BASE_V2_") or not k.startswith("BASE_") else "BASE_V2_" + k[len("BASE_"):]
    v = _setting(k2)
    if v is None and k2 == "BASE_V2_WALLET":
        v = _setting("BASE_WALLET")
    return v if v is not None else d


BW.ENV_FILE = ENV_FILE; BW.setting = setting; BW.SERVICE = SERVICE
KEY_FILE = BW.KEY_FILE = setting("BASE_V2_KEY_FILE") or "/etc/flip/base_v2.key"


def log_path():
    return setting("BASE_V2_LOG_PATH", LOG_DEFAULT)


def positions_file():
    return os.path.join(os.path.dirname(log_path()), "base_v2_positions.json")


def halt_file():
    return setting("BASE_V2_HALT_FILE") or os.path.join(os.path.dirname(os.path.abspath(log_path())), "HALTED.base_v2")


def roster_file():
    return setting("BASE_V2_ROSTER_FILE", ROSTER_DEFAULT)


router = lambda: (setting("BASE_V2_ROUTER") or ROUTER_DEFAULT).lower()
weth = lambda: (setting("BASE_V2_WETH") or WETH_DEFAULT).lower()
factory = lambda: (setting("BASE_V2_FACTORY") or FACTORY_DEFAULT).lower()
probes = lambda: [x.strip().lower() for x in (setting("BASE_V2_PROBE", PROBE_DEFAULT) or "").split(",") if x.strip()]
BW.positions_file = positions_file


def hold_key():
    """the lock a live flip-base-v2 holds on the key file while it runs: refused while another process holds it; held from here to the exit
    (base_wallet.hold_key with the V2 line's words; the file is opened read-only for the lock and never read here)"""
    if BW.LOCK_FD is not None:
        return
    try:
        fd = os.open(KEY_FILE, os.O_RDONLY)
    except OSError as e:
        sys.exit(f"{KEY_FILE} cannot be opened ({e.strerror}): run this with sudo, or create the wallet first (base_wallet.py create {KEY_FILE} {ENV_FILE})")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        sys.exit(f"a live V2 engine holds {KEY_FILE} (flip-base-v2 live, or a manual run) and keeps the wallet's nonce: stop it first")
    BW.LOCK_FD = fd


def guard(any_mode=False):
    """before anything is signed: flip-base-v2 stopped (any_mode) or at least not live, the key's lock ours, chain 8453"""
    if any_mode and BW.service_active():
        sys.exit(f"{SERVICE} is running: sudo systemctl stop {SERVICE} first (same wallet, same nonce), and start it again after")
    if BW.live_running():
        sys.exit(f"{SERVICE} runs live and keeps the wallet's nonce: stop it first (RUNBOOK 4m step 12: sudo systemctl stop {SERVICE})")
    hold_key()
    BW.check_chain()


BW.hold_key = hold_key; BW.guard = guard


def key_locked():
    """whether some process (a live engine, a money script) holds the key file's lock: the file is opened for the lock test only and never
    read; None when it cannot be opened (no file, or not root)"""
    try:
        fd = os.open(KEY_FILE, os.O_RDONLY)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(fd, fcntl.LOCK_UN); return False
    except BlockingIOError:
        return True
    finally:
        os.close(fd)


# ---------------------------------------------------------------- the relay (contracts/FlipRelayV2.json)
def artifact():
    return json.load(open(os.path.join(ROOT, "contracts", "FlipRelayV2.json")))


def relay_runtime(owner, router_=None, weth_=None):
    """FlipRelayV2's runtime as the chain holds it after a deployment by `owner` with constructor (router, weth): the artifact's deployedBytecode
    with its three immutables filled in (solc keys them by AST id, which follows the declaration order: owner, router, weth)"""
    art = artifact(); code = bytearray.fromhex(art["deployedBytecode"][2:]); ids = sorted(art["immutableReferences"], key=int)
    assert len(ids) == 3, art["immutableReferences"]
    for ast_id, val in zip(ids, (owner, router_ or router(), weth_ or weth())):
        for r in art["immutableReferences"][ast_id]:
            code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
    return "0x" + code.hex()


def relay_check(relay, wallet, expected=None):
    """(the code is FlipRelayV2's for this wallet, owner() == wallet, router() == BASE_V2_ROUTER, weth() == BASE_V2_WETH), read from the chain"""
    code = BW.rpc("eth_getCode", [relay, "latest"])
    if not code or len(code) <= 2:
        return False, False, False, False
    got = {k: ("0x" + (BW.rpc("eth_call", [{"to": relay, "data": "0x" + SEL[k]}, "latest"]) or "")[-40:]).lower() for k in ("owner", "router", "weth")}
    return code.lower() == (expected or relay_runtime(wallet)).lower(), got["owner"] == wallet.lower(), got["router"] == router(), got["weth"] == weth()


def relay_words(oc, oo, orr, ow):
    return (f"code {'ok' if oc else 'differs'}, owner {'ok' if oo else 'not the wallet'}, router {'ok' if orr else 'wrong'}, weth {'ok' if ow else 'wrong'}")


# ---------------------------------------------------------------- the log
def read_log(path=None, hours=None, evs=None):
    """the log's lines (and its rotated copies' when hours is given), oldest first, parsed; a line of another event than `evs` is skipped"""
    import glob, gzip, time
    path = path or log_path(); t_lo = (time.time() - hours * 3600) if hours else None
    files = (sorted(glob.glob(path + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) if hours else []) + [path]
    out, seen = [], set()
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                if evs and not any(('"%s"' % ev) in line for ev in evs):
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(e, dict) or "ev" not in e or (evs and e["ev"] not in evs):
                    continue
                k = (e.get("t"), e["ev"], e.get("pair"), e.get("dry"), e.get("what"))
                if (t_lo is None or (e.get("t") or 0) >= t_lo) and k not in seen:          # a rotated copy of the same line counts once
                    seen.add(k); out.append(e)
        except (OSError, EOFError):
            pass
    return sorted(out, key=lambda e: e.get("t") or 0)


# ---------------------------------------------------------------- the commands
def show_address():
    acct = BW.load_account(); want = (setting("BASE_V2_WALLET") or "").lower()
    print(f"the key file {KEY_FILE} is the wallet {acct.address}; BASE_V2_WALLET in {ENV_FILE}: "
          + (("the same" if want == acct.address.lower() else f"{want}: DIFFERENT, fix the env file") if want else "not set"))


def main(argv):
    try:
        if argv and argv[0] == "withdraw" and len(argv) == 2:
            return BW.withdraw(argv[1])
        if argv == ["address"]:
            return show_address()
        sys.exit(__doc__.split("\n\n")[1])
    finally:
        BW.release_key()


if __name__ == "__main__":
    main(sys.argv[1:])
