#!/usr/bin/env python3
"""bnb_wallet.py: the BNB line's own wallet on the box (src/bnb_live.py; not the flip engine's wallet, whose key stays in
/etc/flip/engine.env, which this script never opens). The key never leaves the box and is never printed.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py                   # create the wallet: a new key in /etc/flip/bnb.key
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py withdraw 0xDEST    # all its BNB to 0xDEST, an account of yours
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py sweep 0xTOKEN      # a token left in it sold back to BNB

create: a new key goes to /etc/flip/bnb.key (or the path given), created mode 600 (os.open with O_EXCL: an existing file is never
replaced); prints only the address, which is what you send the BNB to, and the BNB_WALLET= line for /etc/flip/bnb.env.
withdraw: signs on the box a plain transfer of the wallet's whole balance less its gas (21,000 at the network's price, at least 0.1 gwei)
on chain 56 to 0xDEST, once you have typed 0xDEST a second time, and prints the transaction's hash. It refuses while flip-bnb runs live
(the engine keeps its own nonce) or holds open positions (their sale needs the gas), and a destination that is a contract, the wallet
itself or the zero address. An exchange's BNB Smart Chain (BEP20) deposit address is an account.
sweep: the wallet's whole balance of a token sold through the PancakeSwap V2 router to the wallet itself
(swapExactTokensForETHSupportingFeeOnTransferTokens, minOut the BNB expected on the pair's reserves x 0.9, or x (1 - SLIP) with a
third argument such as 0.3), after an approve of the router when the allowance is short; the sale is simulated by eth_call first, and
sent only on a typed yes. It refuses while flip-bnb runs live and for a token the positions file still holds (the engine sells it).
The RPC: BNB_RPC_URL from the environment, else /etc/flip/bnb.env, else https://bsc-rpc.publicnode.com (only its host is printed).

A copy of the key that prints nothing (on the same box: it guards against a deleted file, not a lost box):
    sudo install -m 600 /etc/flip/bnb.key /root/bnb.key.bak
Never `cat` the key: a terminal's output gets pasted into chats and tickets."""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.environ.get("BNB_KEY_FILE") or "/etc/flip/bnb.key"
ENV_FILE = os.environ.get("BNB_ENV_FILE") or "/etc/flip/bnb.env"
CHAIN_ID = 56
ROUTER = "0x10ed43c718714eb63d5aa57b78b54704e256024e"; WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"; FACTORY = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"
MIN_WEI, MAX_WEI = 10 ** 8, 5 * 10 ** 9                                                 # the gas price: 0.1 gwei at least, 5 gwei at most
MAX_UINT = 2 ** 256 - 1
w = lambda x: "%064x" % x
a = lambda s: "%064x" % int(s, 16)
ask = input                                                                              # (the tests answer for the owner)
sleep = time.sleep


def setting(k, d=None):
    """a setting as the engine sees it: the environment, else the env file's last line for it, else the default"""
    if os.environ.get(k):
        return os.environ[k].split(" #", 1)[0].strip()
    v = None
    try:
        for line in open(ENV_FILE):
            if line.startswith(k + "="):
                v = line.split("=", 1)[1].split(" #", 1)[0].strip() or None
    except OSError:
        pass
    return v if v is not None else d


def rpc_url():
    return setting("BNB_RPC_URL", "https://bsc-rpc.publicnode.com")


def host(url):
    try:
        return urllib.parse.urlparse(url).hostname or "?"
    except ValueError:
        return "?"


def rpc(method, params):
    """one JSON-RPC call to the RPC (an error names its host only: the URL may hold a provider's key)"""
    url = rpc_url()
    req = urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=15))
    except Exception as e:
        raise RuntimeError(f"{method} at {host(url)}: {type(e).__name__}") from None
    if "result" not in d:
        raise RuntimeError(f"{method} at {host(url)}: {str(d.get('error'))[:200]}")
    return d["result"]


def word(data, i=0):
    d = data[2:] if data.startswith("0x") else data
    return int(d[64 * i:64 * i + 64], 16)


def amount_out(x, r_in, r_out):
    if x <= 0 or r_in <= 0 or r_out <= 0:
        return 0
    return x * 9975 * r_out // (r_in * 10000 + x * 9975)


def live_running():
    """flip-bnb active with BNB_LIVE=1: the engine owns the wallet's nonce"""
    try:
        active = subprocess.run(["systemctl", "is-active", "--quiet", "flip-bnb"], stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        active = False
    return active and setting("BNB_LIVE", "0") == "1"


def open_positions():
    """the positions file's open positions (token -> state), {} when there is none"""
    path = setting("BNB_POSITIONS_FILE") or os.path.join(os.path.dirname(setting("BNB_LOG_PATH", "/var/log/flip/bnb.jsonl")), "bnb_positions.json")
    try:
        return {x.get("token"): x.get("state") for x in (json.load(open(path)).get("positions") or {}).values()}
    except FileNotFoundError:
        return {}


def load_account():
    """the key file (mode 600, owned by this user) as an account; its content is never printed"""
    from eth_account import Account
    try:
        st = os.stat(KEY_FILE)
    except OSError as e:
        sys.exit(f"{KEY_FILE} cannot be read ({e.strerror}): run this with sudo, or create the wallet first")
    if st.st_mode & 0o077 or st.st_uid != os.geteuid():
        sys.exit(f"{KEY_FILE} is open to other users or owned by another user: sudo chown root:root {KEY_FILE} && sudo chmod 600 {KEY_FILE}")
    try:
        with open(KEY_FILE) as f:
            return Account.from_key(f.read().strip())
    except Exception:
        sys.exit(f"{KEY_FILE} does not hold a usable key (its content is never printed)")


def gas_price():
    gp = max(int(rpc("eth_gasPrice", []), 16), MIN_WEI)
    if gp > MAX_WEI:
        sys.exit(f"the network asks {gp / 1e9:g} gwei, over {MAX_WEI / 1e9:g}: try again later")
    return gp


def sign_send(acct, tx):
    """signed on the box, sent; only the hash is printed"""
    from eth_utils import to_checksum_address
    tx = dict(tx, to=to_checksum_address(tx["to"]), chainId=CHAIN_ID)
    s = acct.sign_transaction(tx)
    raw = "0x" + bytes(getattr(s, "raw_transaction", None) or s.rawTransaction).hex(); h = "0x" + bytes(s.hash).hex()
    got = rpc("eth_sendRawTransaction", [raw])
    print(f"sent: {h}   https://bscscan.com/tx/{h}")
    if got and str(got).lower() != h:
        print(f"(the node answered another hash, {got}: look at the wallet on bscscan)")
    return h


def wait_mined(h, secs=90):
    """its status once mined (1 or 0), None when not seen within secs"""
    for _ in range(int(secs)):
        tx = rpc("eth_getTransactionByHash", [h])
        if tx and tx.get("blockNumber"):
            for r in rpc("eth_getBlockReceipts", [tx["blockNumber"]]) or []:
                if r.get("transactionHash", "").lower() == h.lower():
                    st = int(r.get("status") or "0x0", 16); print(f"mined in block {int(tx['blockNumber'], 16)}: {'ok' if st == 1 else 'REVERTED'}")
                    return st
        sleep(1)
    print(f"not mined within {secs} s: look at https://bscscan.com/tx/{h}")
    return None


def address_arg(s, what):
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", s or ""):
        sys.exit(f"{what} must be an address: 0x and 40 hex digits")
    return s.lower()


def create(p):
    from eth_account import Account
    if os.path.basename(p) == "engine.env":
        sys.exit("this script writes the BNB key file only, never the flip engine's env file")
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
    print(f"new BNB wallet: {acct.address}")
    print(f"add this line to /etc/flip/bnb.env: BNB_WALLET={acct.address.lower()}")
    print("send about $20 of BNB to it on BNB Smart Chain (BEP-20, chain id 56); RUNBOOK 4k has the rest")


def guard():
    if live_running():
        sys.exit("flip-bnb runs live and keeps the wallet's nonce: stop it first (RUNBOOK 4k step 6, then sudo systemctl stop flip-bnb)")
    if int(rpc("eth_chainId", []), 16) != CHAIN_ID:
        sys.exit(f"the RPC ({host(rpc_url())}) is not BNB Smart Chain (56)")


def withdraw(dest):
    dest = address_arg(dest, "the destination")
    acct = load_account(); me = acct.address.lower()
    if dest in (me, "0x" + "0" * 40):
        sys.exit("the destination is the wallet itself or the zero address")
    guard()
    pos = open_positions()
    if pos:
        sys.exit(f"{len(pos)} open live position(s) in the positions file ({', '.join(sorted(str(s) for s in pos.values()))}): their sale needs the gas; "
                 "let flip-bnb sell them first (or sweep each token after moving the file away)")
    if rpc("eth_getCode", [dest, "latest"]) not in ("0x", "0x0", ""):
        sys.exit(f"{dest} is a contract: a plain transfer of 21,000 gas may fail there; send to an account (an exchange deposit address is one)")
    bal = int(rpc("eth_getBalance", [me, "latest"]), 16); gp = gas_price(); fee = 21000 * gp; value = bal - fee
    if value <= 0:
        sys.exit(f"the wallet {me} holds {bal / 1e18:.8f} BNB, not more than the transfer's gas ({fee / 1e18:.8f})")
    nonce = int(rpc("eth_getTransactionCount", [me, "pending"]), 16)
    print(f"from {me} (the BNB line's wallet): {bal / 1e18:.8f} BNB\nto   {dest}: {value / 1e18:.8f} BNB on BNB Smart Chain (chain 56), "
          f"gas 21,000 at {gp / 1e9:g} gwei ({fee / 1e18:.8f} BNB), nonce {nonce}, via {host(rpc_url())}")
    if ask("type the destination address again to send: ").strip().lower() != dest:
        sys.exit("not the same address: nothing sent")
    h = sign_send(acct, {"nonce": nonce, "gasPrice": gp, "gas": 21000, "to": dest, "value": value, "data": "0x"})
    wait_mined(h)


def sweep(token, slip=0.1):
    token = address_arg(token, "the token")
    if not 0.001 <= slip <= 0.9:
        sys.exit("the slippage is 0.001..0.9 (0.1 by default)")
    if token == WBNB:
        sys.exit("WBNB is not swept here")
    acct = load_account(); me = acct.address.lower()
    guard()
    if token in open_positions():
        sys.exit("the positions file holds this token as an open position: the engine sells it (start flip-bnb live), or move the file away first")
    bal = word(rpc("eth_call", [{"to": token, "data": "0x70a08231" + a(me)}, "latest"]))
    if bal <= 0:
        print(f"the wallet holds none of {token}: nothing to sell"); return
    pair = "0x" + "%040x" % word(rpc("eth_call", [{"to": FACTORY, "data": "0xe6a43920" + a(token) + a(WBNB)}, "latest"]))
    if int(pair, 16) == 0:
        sys.exit(f"no PancakeSwap V2 pair of {token} with WBNB")
    t0 = "0x" + "%040x" % word(rpc("eth_call", [{"to": pair, "data": "0x0dfe1681"}, "latest"]))
    r = rpc("eth_call", [{"to": pair, "data": "0x0902f1ac"}, "latest"]); r0, r1 = word(r, 0), word(r, 1)
    rt, rq = (r0, r1) if t0 == token else (r1, r0)
    expected = amount_out(bal, rt, rq); min_out = expected * (10 ** 6 - int(round(slip * 1e6))) // 10 ** 6
    if expected <= 0:
        sys.exit(f"the pair {pair} returns nothing for these tokens (its WBNB: {rq / 1e18:.8f})")
    allowed = word(rpc("eth_call", [{"to": token, "data": "0xdd62ed3e" + a(me) + a(ROUTER)}, "latest"]))
    print(f"the wallet {me} holds {bal} of {token}: about {expected / 1e18:.8f} BNB on the pair {pair} (its WBNB {rq / 1e18:.6f}); "
          f"minOut {min_out / 1e18:.8f} ({slip:.0%} under){'' if allowed >= bal else '; the router needs an approve first'}")
    if ask("type yes to sell them: ").strip() != "yes":
        sys.exit("nothing sent")
    gp = gas_price()
    if allowed < bal:
        h = sign_send(acct, {"nonce": int(rpc("eth_getTransactionCount", [me, "pending"]), 16), "gasPrice": gp, "gas": 80000, "to": token, "value": 0,
                             "data": "0x095ea7b3" + a(ROUTER) + w(MAX_UINT)})
        if wait_mined(h) != 1:
            sys.exit("the approve did not go through: nothing sold")
    data = "0x791ac947" + w(bal) + w(min_out) + w(160) + a(me) + w(int(time.time()) + 120) + w(2) + a(token) + a(WBNB)
    try:
        rpc("eth_call", [{"from": me, "to": ROUTER, "data": data}, "latest"])                    # the sale simulated first: a revert sends nothing
    except RuntimeError as e:
        sys.exit(f"the sale would revert ({e}): nothing sent; a larger slippage as a third argument (e.g. 0.3) may pass")
    h = sign_send(acct, {"nonce": int(rpc("eth_getTransactionCount", [me, "pending"]), 16), "gasPrice": gp, "gas": 300000, "to": ROUTER, "value": 0, "data": data})
    wait_mined(h)


def main(argv):
    if argv and argv[0] == "withdraw":
        if len(argv) != 2:
            sys.exit("usage: bnb_wallet.py withdraw 0xDEST")
        return withdraw(argv[1])
    if argv and argv[0] == "sweep":
        if len(argv) not in (2, 3):
            sys.exit("usage: bnb_wallet.py sweep 0xTOKEN [SLIP]")
        try:
            slip = float(argv[2]) if len(argv) == 3 else 0.1
        except ValueError:
            sys.exit("the slippage must be a number such as 0.1")
        return sweep(argv[1], slip)
    return create(argv[0] if argv else KEY_FILE)


if __name__ == "__main__":
    main(sys.argv[1:])
