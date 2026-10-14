#!/usr/bin/env python3
"""base_wallet.py: the Base line's own wallet on the box (src/base_engine.py, service flip-base; docs/BASE.md section 1). Not the flip
engine's wallet (/etc/flip/engine.env) nor the BNB line's (/etc/flip/bnb.key): this script never opens either. The key never leaves the
box and is never printed.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py                        # create: a new key in /etc/flip/base.key, BASE_WALLET= in /etc/flip/base.env
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py create KEYFILE ENVFILE  # the same with other paths (a test in a scratch directory)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py address                # the key file's address (never the key) against BASE_WALLET
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py withdraw 0xDEST         # all its ETH on Base to 0xDEST, an account of yours

create: a new key goes to /etc/flip/base.key (BASE_KEY_FILE, or the path given), created mode 600 (os.open with O_EXCL: an existing file
is never replaced); the line BASE_WALLET=<address> replaces any BASE_WALLET= line of /etc/flip/base.env (or the path given; appended when
there is none; the file is written whole to a temporary file, mode 600, then renamed over it). Prints only the address.
withdraw: signs on the box a plain transfer (21,000 gas) of the wallet's whole balance less its gas and its L1 data fee, a type-2
transaction on chain 8453 (maxFeePerGas = 2 x the head's base fee + the priority fee), to 0xDEST once you have typed 0xDEST a second time,
sends it to every BASE_SEND_URLS endpoint, and prints the hash and the receipt. It refuses while flip-base runs live (BASE_DRY_RUN not 1)
or any process holds the key file's lock, while the positions file holds an open position (its sale needs the gas), and a destination
that is a contract (or an account with code: EIP-7702), the wallet itself or the zero address. An exchange's Base deposit address is an
account; check that the exchange credits Base (network "Base"), not Ethereum.

THE LOCK, shared with the engine: an exclusive fcntl.flock(LOCK_EX | LOCK_NB) on the key file itself, BASE_KEY_FILE (/etc/flip/base.key),
opened read-only. A live engine takes it at its start and holds it while it runs (it keeps the wallet's nonce in memory); withdraw here,
base_ops.py's deposit/withdraw/sweep/payout and base_relay_deploy.py's deployment take it the same way, stop when another process holds
it, and hold it until they exit, so no live engine starts meanwhile. (flip-base sees the key through a read-only bind mount of the same
file: the lock is on the file, so both sides see it.)

The RPC: BASE_RPC_URL from the environment, else /etc/flip/base.env, else https://mainnet.base.org, and BASE_READ_ALT_URL
(https://base-rpc.publicnode.com) when it fails or rate-limits; sends go to every BASE_SEND_URLS. Only hosts are ever printed.
A copy of the key that prints nothing (on the same box: it guards against a deleted file, not a lost box):
    sudo install -m 600 /etc/flip/base.key /root/base.key.bak
Never `cat` the key: a terminal's output gets pasted into chats and tickets.

The module is also the shared helper of base_ops.py, base_relay_deploy.py and base_results.py (settings, reads, the lock, type-2 sends);
its top-level imports are the standard library only (base_results.py runs under the system python)."""
import fcntl, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.environ.get("BASE_KEY_FILE") or "/etc/flip/base.key"
ENV_FILE = os.environ.get("BASE_ENV_FILE") or "/etc/flip/base.env"
SERVICE = "flip-base"
CHAIN_ID = 8453
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"                                       # Uniswap v4 PoolManager on Base (BASE_POOL_MANAGER)
GPO = "0x420000000000000000000000000000000000000f"                                       # OP Stack GasPriceOracle: the L1 data fee
EXPLORER = "https://basescan.org"
ZERO = "0x" + "0" * 40
PRIO_FLOOR_WEI = 10 ** 6                                                                 # 0.001 gwei: what the network asked on Oct 14
PRIO_MAX_WEI = 5 * 10 ** 7                                                               # 0.05 gwei (BASE_PRIO_GWEI's default)
MAX_FEE_WEI = 10 ** 9                                                                    # 1 gwei: over that (Base ran at 0.005-0.006) these scripts wait
UA = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
w = lambda x: "%064x" % (x % (1 << 256))
a = lambda s: "%064x" % int(s, 16)
ask = input                                                                              # (a test answers for the owner)
sleep = time.sleep
LOCK_FD = None                                                                           # the key file's lock, held from hold_key() to the exit


# ---------------------------------------------------------------- settings
def setting(k, d=None):
    """a setting as the engine sees it: the environment, else the env file's last line for it, else the default"""
    if os.environ.get(k):
        return os.environ[k].split(" #", 1)[0].strip()
    v = None
    try:
        for line in open(ENV_FILE):
            if line.startswith(k + "="):
                v = line.split("=", 1)[1].split(" #", 1)[0].strip().strip('"').strip("'") or None
    except OSError:
        pass
    return v if v is not None else d


def url_list(v):
    """a comma (or space) separated list of endpoints; '0' or '' is none"""
    return [u for u in re.split(r"[,\s]+", v or "") if u and u != "0"]


def rpc_urls():
    return url_list(setting("BASE_RPC_URL", "https://mainnet.base.org")) + url_list(setting("BASE_READ_ALT_URL", "https://base-rpc.publicnode.com"))


def send_urls():
    return url_list(setting("BASE_SEND_URLS", "https://mainnet-sequencer.base.org,https://mainnet.base.org"))


def host(url):
    try:
        return urllib.parse.urlparse(url).hostname or "?"
    except ValueError:
        return "?"


def env_path_ok(p):
    """never another line's file: the flip engine's (it holds that wallet's key) or the BNB line's"""
    return os.path.basename(p) not in ("engine.env", "bnb.env", "bnb.key")


# ---------------------------------------------------------------- reads
class RpcError(RuntimeError):
    """a JSON-RPC error answered by a node (a revert, a refused transaction): not retried elsewhere"""


def post(url, method, params, timeout=20):
    """one JSON-RPC call; a transport failure or a rate limit raises OSError-like RuntimeError naming the host only"""
    req = urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), UA)
    try:
        d = json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read()[:300].decode("utf-8", "replace")
        except Exception:
            pass
        if e.code not in (429, 403, 502, 503, 504) and '"error"' in body:
            try:
                err = json.loads(body).get("error") or {}
                raise RpcError(f"{method} at {host(url)}: {json.dumps(err)[:300]}")
            except ValueError:
                pass
        raise ConnectionError(f"{method} at {host(url)}: HTTP {e.code}") from None
    except RpcError:
        raise
    except Exception as e:
        raise ConnectionError(f"{method} at {host(url)}: {type(e).__name__}") from None
    if "result" not in d:
        err = d.get("error") or {}
        if isinstance(err, dict) and err.get("code") in (429, -32005, -32011, -32029):
            raise ConnectionError(f"{method} at {host(url)}: rate limited ({str(err.get('message'))[:80]})")
        raise RpcError(f"{method} at {host(url)}: {json.dumps(err)[:400]}")
    return d["result"]


def rpc(method, params, urls=None, timeout=20):
    """a read from BASE_RPC_URL, else BASE_READ_ALT_URL when the first cannot answer (down, rate-limited); a node's own error (a
    revert) is raised at once"""
    last = None
    for u in (urls or rpc_urls()):
        try:
            return post(u, method, params, timeout)
        except ConnectionError as e:
            last = e
    raise RuntimeError(str(last) if last else f"{method}: no endpoint")


def balance(addr):
    return int(rpc("eth_getBalance", [addr, "latest"]), 16)


def has_code(addr):
    return rpc("eth_getCode", [addr, "latest"]) not in ("0x", "0x0", "", None)


def check_chain():
    for u in rpc_urls():
        try:
            cid = int(post(u, "eth_chainId", []), 16)
        except Exception as e:
            print(f"(eth_chainId not read at {host(u)}: {e})")
            continue
        if cid != CHAIN_ID:
            sys.exit(f"the endpoint {host(u)} is chain {cid}, not Base ({CHAIN_ID}): fix BASE_RPC_URL / BASE_READ_ALT_URL in {ENV_FILE}")


def word(data, i=0):
    d = data[2:] if data.startswith("0x") else data
    return int(d[64 * i:64 * i + 64], 16)


# ---------------------------------------------------------------- the service, the positions, the key
def service_active():
    """systemctl's word on flip-base (False where there is no systemctl)"""
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", SERVICE], stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def live_setting():
    """BASE_DRY_RUN as the engine would read it: anything but 1 counts as live here (the safe side for a refusal)"""
    return (setting("BASE_DRY_RUN", "1") or "1").strip().lower() not in ("1", "true", "yes")


def live_running():
    return service_active() and live_setting()


def positions_file():
    return os.path.join(os.path.dirname(setting("BASE_LOG_PATH", "/var/log/flip/base.jsonl")), "base_positions.json")


def open_positions():
    """the open positions in base_positions.json (beside the log), as a list of their JSON texts; [] when there is none. The file's
    shape is the engine's: {"positions": {...} or [...]}, a list, or a dict of positions (dict values); an empty one means none"""
    try:
        d = json.load(open(positions_file()))
    except FileNotFoundError:
        return []
    except Exception as e:
        sys.exit(f"{positions_file()} cannot be read ({type(e).__name__}): look at it before moving any money")
    if isinstance(d, dict) and "positions" in d:
        d = d["positions"]
    if isinstance(d, dict):
        return [json.dumps(v) for v in d.values() if isinstance(v, (dict, list)) and v]
    if isinstance(d, list):
        return [json.dumps(v) for v in d if v]
    return []


def load_account(key_file=None):
    """the key file (mode 600, owned by this user) as an account; its content is never printed"""
    from eth_account import Account
    p = key_file or KEY_FILE
    try:
        st = os.stat(p)
    except OSError as e:
        sys.exit(f"{p} cannot be read ({e.strerror}): run this with sudo, or create the wallet first (base_wallet.py)")
    if st.st_mode & 0o077 or st.st_uid != os.geteuid():
        sys.exit(f"{p} is open to other users or owned by another user: sudo chown root:root {p} && sudo chmod 600 {p}")
    try:
        with open(p) as f:
            return Account.from_key(f.read().strip())
    except Exception:
        sys.exit(f"{p} does not hold a usable key (its content is never printed)")


def wallet_account():
    """the key file's account, which must be BASE_WALLET"""
    acct = load_account(); want = (setting("BASE_WALLET") or "").lower()
    if not want:
        sys.exit(f"BASE_WALLET is not set in {ENV_FILE}: base_wallet.py writes it when it creates the wallet")
    if acct.address.lower() != want:
        sys.exit(f"the key in {KEY_FILE} is for {acct.address}, BASE_WALLET says {want}: fix {ENV_FILE}")
    return acct


def hold_key():
    """the lock a live engine holds on the key file while it runs: refused while another process holds it; held from here to the exit"""
    global LOCK_FD
    if LOCK_FD is not None:
        return
    fd = os.open(KEY_FILE, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        sys.exit(f"a live Base engine holds {KEY_FILE} (flip-base live, or a manual run) and keeps the wallet's nonce: stop it first")
    LOCK_FD = fd


def release_key():
    global LOCK_FD
    if LOCK_FD is not None:
        os.close(LOCK_FD); LOCK_FD = None


def guard(any_mode=False):
    """before anything is signed: flip-base stopped (any_mode) or at least not live, the key's lock ours, chain 8453"""
    if any_mode and service_active():
        sys.exit(f"flip-base is running: sudo systemctl stop {SERVICE} first (same wallet, same nonce), and start it again after")
    if live_running():
        sys.exit(f"flip-base runs live and keeps the wallet's nonce: stop it first (RUNBOOK 4l step 9: sudo systemctl stop {SERVICE})")
    hold_key()
    check_chain()


# ---------------------------------------------------------------- type-2 transactions
def fees():
    """(base fee of the head, priority fee, maxFeePerGas = 2 x base + priority); stops above MAX_FEE_WEI"""
    blk = rpc("eth_getBlockByNumber", ["latest", False]); base = int(blk["baseFeePerGas"], 16)
    try:
        prio = int(rpc("eth_maxPriorityFeePerGas", []), 16)
    except Exception:
        prio = PRIO_FLOOR_WEI
    prio = min(max(prio, PRIO_FLOOR_WEI), PRIO_MAX_WEI); mx = 2 * base + prio
    if mx > MAX_FEE_WEI:
        sys.exit(f"Base asks a base fee of {base / 1e9:g} gwei, over {MAX_FEE_WEI / 1e9:g} gwei with the margin: try again later")
    return base, prio, mx


def l1_fee_bound(size):
    """the L1 data fee's upper bound for a transaction of `size` bytes (GasPriceOracle.getL1FeeUpperBound, Fjord and later)"""
    try:
        return int(rpc("eth_call", [{"to": GPO, "data": "0xf1c7a58b" + w(size)}, "latest"]), 16)
    except Exception:
        return 10 ** 13                                                                  # 0.00001 ETH: far above what Base charged on Oct 14


def sign(acct, tx):
    """a type-2 transaction on chain 8453, signed on the box: (raw hex, hash)"""
    from eth_utils import to_checksum_address
    tx = dict(tx, type=2, chainId=CHAIN_ID)
    if tx.get("to"):
        tx["to"] = to_checksum_address(tx["to"])
    s = acct.sign_transaction(tx)
    return "0x" + bytes(getattr(s, "raw_transaction", None) or s.rawTransaction).hex(), "0x" + bytes(s.hash).hex()


def send_raw(raw, h):
    """to every BASE_SEND_URLS endpoint; the first that takes it (or already knows it) counts; only the hash is printed"""
    ok, errs = [], []
    for u in send_urls():
        try:
            got = post(u, "eth_sendRawTransaction", [raw])
            ok.append(host(u))
            if got and str(got).lower() != h.lower():
                print(f"({host(u)} answered another hash, {got}: look at the wallet on {EXPLORER})")
        except Exception as e:
            m = str(e)
            (ok if re.search(r"already known|known transaction|AlreadyKnown", m, re.I) else errs).append(host(u) if "known" in m.lower() else m[:200])
    if not ok:
        sys.exit("no endpoint took the transaction: " + " | ".join(errs))
    print(f"sent: {h}   {EXPLORER}/tx/{h}   (taken by {', '.join(ok)}{'; refused by: ' + ' | '.join(errs) if errs else ''})")
    return h


def wait_receipt(h, secs=90):
    """the receipt once mined (status printed with its gas and L1 fee), None when not seen within secs"""
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            r = rpc("eth_getTransactionReceipt", [h])
        except RuntimeError:
            r = None
        if r and r.get("blockNumber"):
            st = int(r.get("status") or "0x0", 16); gas = int(r["gasUsed"], 16) * int(r.get("effectiveGasPrice") or "0x0", 16)
            l1 = int(r.get("l1Fee") or "0x0", 16)
            print(f"mined in block {int(r['blockNumber'], 16)}: {'ok' if st == 1 else 'REVERTED'}; gas {int(r['gasUsed'], 16):,} = "
                  f"{gas / 1e18:.9f} ETH + L1 fee {l1 / 1e18:.9f} ETH")
            return r
        sleep(1)
    print(f"not mined within {secs} s: look at {EXPLORER}/tx/{h} before trying again")
    return None


def transact(acct, to, value, data, gas=None, label="", confirm=None):
    """estimate, check the balance (value + gas at maxFee + twice the L1 bound), optionally confirm, sign, send, wait: the receipt"""
    me = acct.address.lower()
    base, prio, mx = fees()
    if gas is None:
        q = {"from": me, "value": hex(value), "data": data}
        if to:
            q["to"] = to
        gas = int(int(rpc("eth_estimateGas", [q]), 16) * 1.3) + 5000
    nonce = int(rpc("eth_getTransactionCount", [me, "pending"]), 16)
    tx = {"nonce": nonce, "maxFeePerGas": mx, "maxPriorityFeePerGas": prio, "gas": gas, "value": value, "data": data}
    if to:
        tx["to"] = to
    raw, h = sign(acct, tx); l1 = l1_fee_bound(len(raw) // 2)
    bal = balance(me); need = value + gas * mx + 2 * l1
    print(f"{label}: nonce {nonce}, gas limit {gas:,} at most {mx / 1e9:.4f} gwei (base {base / 1e9:.4f} + priority {prio / 1e9:.4f}), "
          f"L1 fee at most {l1 / 1e18:.9f} ETH: at most {(gas * mx + l1) / 1e18:.8f} ETH of fees; the wallet holds {bal / 1e18:.6f} ETH")
    if bal < need:
        sys.exit(f"the wallet holds {bal / 1e18:.8f} ETH, under the {need / 1e18:.8f} this needs: nothing sent")
    if confirm and not confirm():
        sys.exit("nothing sent")
    send_raw(raw, h)
    return wait_receipt(h)


def address_arg(s, what):
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", s or ""):
        sys.exit(f"{what} must be an address: 0x and 40 hex digits")
    if s[2:] not in (s[2:].lower(), s[2:].upper()):
        from eth_utils import is_checksum_address
        if not is_checksum_address(s):
            sys.exit(f"{s} is mixed-case but fails its checksum: a character is wrong; copy it again")
    return s.lower()


# ---------------------------------------------------------------- the env file
def set_env(path, key, value):
    """KEY=value replacing every KEY= line of the env file (appended when there is none), written whole to a mode-600 temporary file and
    renamed over it; a missing file is created mode 600. Returns the value it replaced (None when there was none)"""
    if not env_path_ok(path):
        sys.exit(f"{path}: this script writes the Base line's env file only")
    try:
        lines = open(path).read().splitlines()
    except FileNotFoundError:
        lines = ["# the Base engine's settings (src/base_engine.py, docs/BASE.md section 5); no key belongs in this file"]
    old = [l.split("=", 1)[1].strip() for l in lines if l.startswith(key + "=")]
    out, done = [], False
    for l in lines:
        if l.startswith(key + "="):
            if not done:
                out.append(f"{key}={value}"); done = True
            continue
        out.append(l)
    if not done:
        out.append(f"{key}={value}")
    tmp = path + ".tmp"
    if os.path.lexists(tmp):
        os.unlink(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600); os.write(fd, ("\n".join(out) + "\n").encode()); os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    return old[-1] if old else None


# ---------------------------------------------------------------- the commands
def create(p, env):
    from eth_account import Account
    if os.path.basename(p) in ("engine.env", "bnb.env", "bnb.key", "base.env"):
        sys.exit(f"{p}: the key goes to its own file (BASE_KEY_FILE, /etc/flip/base.key), never an env file or another line's key")
    if not env_path_ok(env):
        sys.exit(f"{env}: the address goes to the Base line's env file only (/etc/flip/base.env)")
    if os.path.lexists(p):
        sys.exit(f"{p} exists: not replacing it (move it away yourself if it really is unused, after backing it up)")
    acct = Account.create()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, ("0x" + bytes(acct.key).hex() + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    st = os.stat(p)
    k = open(p).read().strip()
    assert re.fullmatch(r"0x[0-9a-f]{64}", k) and st.st_mode & 0o777 == 0o600, "the key file was not written as expected"
    assert Account.from_key(k).address == acct.address, "the written key does not match the address"
    del k
    addr = acct.address.lower()
    old = set_env(env, "BASE_WALLET", addr)
    print(f"new Base wallet: {acct.address}")
    print(f"written: {p} (mode 600, the key: never displayed) and BASE_WALLET={addr} in {env}")
    if old and old.lower() != addr:
        print(f"it replaced BASE_WALLET={old}: that wallet's key is not at {p}; if it still holds ETH, its own key file is the only way to it")
        relay = setting("BASE_RELAY") if os.path.abspath(env) == os.path.abspath(ENV_FILE) else None
        if relay:
            print(f"BASE_RELAY={relay} belongs to the old wallet: deploy a new relay (RUNBOOK 4l step 4) before any live start")
    print("send about 0.012 ETH to it on Base (chain id 8453; an exchange's withdrawal on the network \"Base\"); RUNBOOK 4l has the rest")


def show_address():
    acct = load_account(); want = (setting("BASE_WALLET") or "").lower()
    print(f"the key file {KEY_FILE} is the wallet {acct.address}; BASE_WALLET in {ENV_FILE}: "
          + (("the same" if want == acct.address.lower() else f"{want}: DIFFERENT, fix the env file") if want else "not set"))


def withdraw(dest):
    dest = address_arg(dest, "the destination")
    acct = load_account(); me = acct.address.lower()
    if dest in (me, ZERO):
        sys.exit("the destination is the wallet itself or the zero address")
    relay = (setting("BASE_RELAY") or "").lower()
    if relay and dest == relay:
        sys.exit("the destination is our own relay: that is base_ops.py deposit")
    guard()
    pos = open_positions()
    if pos:
        sys.exit(f"{len(pos)} open position(s) in {positions_file()}: their sale needs the wallet's gas; let flip-base sell them first")
    if has_code(dest):
        sys.exit(f"{dest} has code (a contract, or an account with an EIP-7702 delegation): a plain transfer of 21,000 gas may fail there; "
                 "send to a plain account (an exchange's Base deposit address is one)")
    bal = balance(me); base, prio, mx = fees(); l1 = l1_fee_bound(120); fee = 21000 * mx + 2 * l1; value = bal - fee
    if value <= 0:
        sys.exit(f"the wallet {me} holds {bal / 1e18:.9f} ETH, not more than the transfer's fees ({fee / 1e18:.9f})")
    nonce = int(rpc("eth_getTransactionCount", [me, "pending"]), 16)
    print(f"from {me} (the Base line's wallet): {bal / 1e18:.9f} ETH\nto   {dest}: {value / 1e18:.9f} ETH on Base (chain {CHAIN_ID}), "
          f"gas 21,000 at most {mx / 1e9:.4f} gwei + an L1 fee of at most {l1 / 1e18:.9f}: at most {fee / 1e18:.9f} ETH kept for the fees "
          f"(what they do not use stays in the wallet), nonce {nonce}, via {', '.join(host(u) for u in send_urls())}")
    if ask("type the destination address again to send: ").strip().lower() != dest:
        sys.exit("not the same address: nothing sent")
    raw, h = sign(acct, {"nonce": nonce, "maxFeePerGas": mx, "maxPriorityFeePerGas": prio, "gas": 21000, "to": dest, "value": value, "data": "0x"})
    send_raw(raw, h)
    wait_receipt(h)


def main(argv):
    try:
        return run(argv)
    finally:
        release_key()


def run(argv):
    if argv and argv[0] == "withdraw":
        if len(argv) != 2:
            sys.exit("usage: base_wallet.py withdraw 0xDEST")
        return withdraw(argv[1])
    if argv and argv[0] == "address":
        return show_address()
    if argv and argv[0] == "create":
        argv = argv[1:]
    if len(argv) > 2 or any(x.startswith("-") for x in argv):
        sys.exit(__doc__.split("\n\n")[1])
    return create(argv[0] if argv else KEY_FILE, argv[1] if len(argv) > 1 else ENV_FILE)


if __name__ == "__main__":
    main(sys.argv[1:])
