#!/usr/bin/env python3
"""bnb_live: the LIVE path of the BNB line, loaded by src/bnb_engine.py only when BNB_LIVE=1. With BNB_LIVE=0 (the default) this file is
never imported and the engine signs and sends nothing. research/session_oct12/bnb/REPORT_BNB.md section 5: a $5 probe of the rule (buy at
L+50, sell at L+260) on every BNB_PROBE_EVERY-th launch of a traded size, the others left dry as the control, and the gate as halts.

From the wallet straight through the PancakeSwap V2 router (no contract of ours on chain):
  - at the launch (about 50 blocks before the buy) the pool is armed when its size is one BNB_LIVE_POOL_BNB lists (1, 10, 25), its slot
    is live, the line is not halted, the day is not stopped and fewer than BNB_MAX_OPEN positions are open; then the pre-buy check: the
    token's runtime code must be one of the line's templates (BNB_TOKEN_CODEHASHES), and an eth_call of contracts/BnbRoundTrip.sol,
    placed by state override at a fresh address, buys the stake through the router and sells it all back (the wallet's own calls) on the
    pool as it is; the pool is refused when a leg fails, when the sale returns under BNB_CHECK_MIN (99%) of the stake, or when a leg would
    need more gas than its limit;
  - at L+BNB_BUY_AT seen: swapExactETHForTokensSupportingFeeOnTransferTokens(minOut, [WBNB, token], wallet, now + BNB_DEADLINE_S), the
    value the engine's stake (BNB_STAKE_USD at the USDT/WBNB price), minOut the engine's tokens for it on the reserves it tracks (the
    PancakeSwap formula) x the buy leg's measured factor x (1 - BNB_SLIP), raised to the same bound on the pool's reserves read just
    before the send; not sent when it would land more than BNB_BUY_LATE blocks after L+BNB_BUY_AT by the chain's head (read once more just
    before the send, else the newest head known aged at BLOCK_S a block); one not mined by then is cancelled (no copy of it goes out);
  - after the buy's receipt: approve(router, max) at the next nonce (once a token);
  - at L+BNB_SELL_AT seen, at once on a dump seen first, when the pool stops being watched, or when the chain's head is BNB_SELL_LATE
    blocks past L+BNB_SELL_AT while the reader lags: swapExactTokensForETHSupportingFeeOnTransferTokens(the wallet's whole balance of the
    token, the BNB expected on the tracked reserves x the sell leg's factor x (1 - BNB_SLIP), [token, WBNB], wallet, deadline); a reverted
    sell is sent again on the reserves then with the slippage doubled, up to BNB_SELL_TRIES sells;
  - settled from the receipts: BNB in (the WBNB the router paid the pair), the tokens (the token's Transfers to the wallet, or its balance),
    BNB out (the WBNB the pair paid the router), the gas of every transaction, the P&L in BNB, $ and % beside the dry price of the same
    trade: a trade_done line with live: true (the positions file saved first: a hard kill never settles a trade twice).
One worker thread signs and sends everything: the nonce comes from the RPC (pending) once, is kept in memory and is read again after any
nonce error. Gas: a fixed limit per call (BNB_GAS_BUY/APPROVE/SELL; twice it after an out-of-gas revert), the price eth_gasPrice kept
between BNB_MIN_GWEI and BNB_MAX_GWEI. Every send goes to every send endpoint at once; with no receipt a copy goes again each
BNB_REBROADCAST_S, and one a pool holds unmined (either read endpoint's) is replaced at its nonce after BNB_REPLACE_S (1/8 dearer, 3
times, then once at BNB_MAX_GWEI; a buy past its deadline by a 0-value transfer to the wallet). A buy dropped as never mined while a
later nonce of ours is out has its nonce filled the same way. Reads BNB_RPC_URL cannot answer are asked once at BNB_READ_ALT_URL. What a
transaction with no receipt did is decided by one rule, written at Live.outcome(): from a receipt at either read endpoint in a block
final there, or from the state of an endpoint whose count shows its nonce mined; a 'nonce too low' or a refused replacement only stops
the signing at that nonce and asks both endpoints at once; anything else is held (alarms; nothing dropped, sent again or settled), and a
transaction is dropped as never mined only when every endpoint answers that its nonce is free, no pool holds it, no node said 'nonce
too low' at it and its deadline is past (a backend that lags still answers, stale, and may hold a mined transaction as pending). The worker reads the head itself when the
reader gives none for 3 s, and extrapolates it when no source shows a new block for 10 s.
The gate halts the line (HALTED.bnb beside the log; the owner's own HALTED.bnb holds without a restart): a dump before +997 on any pool of
the line (the skipped sizes aside), no crowd buy in +60..+260 on a traded pool whose logs were all read, any reverted buy, approve or
sell, a negative median over the first 10 live trades, then over any 10 in a row, and 3 live trades in a row under -50%. A halt stops
new buys and still sells what is open. BNB_DAILY_STOP_USD of losses stops new buys for the rest of the UTC day.
Open positions and the pools they need are written to bnb_positions.json beside the log on every change and taken back at the start
(sold at once when past their sell block; a position whose last transaction has no receipt waits for it); one live engine at a time
holds bnb_positions.json.lock and the key file's lock (deploy/bnb_wallet.py takes the same).

The key is read from BNB_KEY_FILE (mode 600, owned by this process's user, made by deploy/bnb_wallet.py) and is never printed, logged or
written anywhere.
"""
import os, re, json, time, threading, queue, statistics, datetime, traceback, hashlib, fcntl, urllib.request, urllib.parse, urllib.error

SEL_BUY = "b6f9de95"                     # swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)
SEL_SELL = "791ac947"                    # swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
SEL_APPROVE = "095ea7b3"                 # approve(address,uint256)
SEL_BALANCE = "70a08231"                 # balanceOf(address)
SEL_ALLOWANCE = "dd62ed3e"               # allowance(address,address)
SEL_RESERVES = "0902f1ac"                # getReserves()
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"     # Transfer(address,address,uint256)
MAX_UINT = 2 ** 256 - 1
HARNESS = "0x00000000000000000000000000000000b0b0b0b0"                              # where the check's code is placed (an empty account)
USDT = "0x55d398326f99059ff775485246999027b3197955"                                  # the start's self-test of the check: a round trip of USDT
ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts", "BnbRoundTrip.json")
OPEN = ("buying", "buy_sent", "bought", "approve_sent", "approved", "sell_sent", "stuck")   # a position holding (or buying) tokens: never dropped
TOKEN_CODEHASHES = "0x18449a1624d9c5270bd1526d891e72a37319e8a08eb3fe687b5ad707e1c487bc,"  \
                   "0x5faca89801207abc52605eeb2ba37eec664b0e6668d96513bcb11f616d441356"     # keccak of the launcher's two token templates (1,365 and 2,995 bytes), Oct 12
FAST = {"tries": 1, "timeout": 3, "alt": False}                                      # a read on the buy's own path: one try, 3 s, no second endpoint
BLOCK_S = 0.45                                                                       # BNB Chain's block time (Oct 12): a head extrapolated while blind
HEAD_BLIND_S = 10                                                                    # no head from any source this long: extrapolated
HEAD_NOW_S = 1.5                                                                     # the head read just before a buy's send: one try, this long at most
ZERO_READS = 6                                                                       # a token balance of 0 at the sale read this many times, 1 s apart, before it counts
ALT_EVERY_S = 5                                                                      # a pending decision asks BNB_READ_ALT_URL at most this often
w = lambda x: "%064x" % x
a = lambda s: "%064x" % int(s, 16)


def own_file(path):
    """a file of this line in the shared log directory: HALTED.bnb or a name that starts with "bnb" (so never one of flip-engine's: its
    HALTED, HALTED.front*, HALTED.follow or its log)"""
    b = os.path.basename(path)
    return b == "HALTED.bnb" or b.startswith("bnb")


def buy_data(min_out, token, wallet, deadline, wbnb):
    return "0x" + SEL_BUY + w(min_out) + w(128) + a(wallet) + w(deadline) + w(2) + a(wbnb) + a(token)


def sell_data(amount, min_out, token, wallet, deadline, wbnb):
    return "0x" + SEL_SELL + w(amount) + w(min_out) + w(160) + a(wallet) + w(deadline) + w(2) + a(token) + a(wbnb)


def approve_data(spender):
    return "0x" + SEL_APPROVE + a(spender) + w(MAX_UINT)


PPM = 10 ** 6


def bound(expected, factor_ppm, slip_ppm):
    """a minimum output: the expected amount x the token's measured factor x (1 - the slippage), in integers"""
    return expected * factor_ppm // PPM * (PPM - slip_ppm) // PPM


def reply_kind(err):
    """an endpoint's error for a transaction sent: "in" (this very transaction is already there), "nonce" (the nonce is taken or out
    of order: read it again), "rejected" (the transaction itself was refused: nothing went in) or "unknown" (the endpoint's own trouble:
    a rate limit, a method it does not serve; another endpoint may take it)"""
    m = str(err).lower()
    if "already known" in m or "known transaction" in m or "already imported" in m or "already exists" in m:
        return "in"
    if "nonce" in m or "replacement transaction underpriced" in m:
        return "nonce"
    if any(x in m for x in ("insufficient funds", "underpriced", "intrinsic gas", "gas limit", "invalid sender", "exceeds", "fee cap",
                            "oversized", "negative value", "chain id", "chainid", "rlp", "transaction type", "invalid transaction")):
        return "rejected"
    return "unknown"


def addr(t):
    return "0x" + t[-40:].lower()


def transfers(rcpt, token, frm=None, to=None):
    """the sum of a token's Transfer logs in a receipt (from and to filtered)"""
    s = 0
    for lg in rcpt.get("logs") or []:
        t = lg.get("topics") or []
        if len(t) == 3 and t[0] == T_TRANSFER and lg.get("address", "").lower() == token and (frm is None or addr(t[1]) == frm) \
                and (to is None or addr(t[2]) == to):
            s += int(lg["data"], 16)
    return s


class Live:
    def __init__(self, E):
        self.E = E; s, env = E._setting, E.env
        self.wallet = env("BNB_WALLET", "").lower()
        if not re.fullmatch(r"0x[0-9a-f]{40}", self.wallet):
            raise SystemExit("BNB_LIVE=1 needs BNB_WALLET=0x... (the address deploy/bnb_wallet.py printed)")
        self.key_file = env("BNB_KEY_FILE", "/etc/flip/bnb.key")
        self.send_urls = list(dict.fromkeys(u for u in (env("BNB_SEND_URL", E.RPC_URL), env("BNB_SEND_ALT_URL", "https://bsc-dataseed.bnbchain.org")) if u != "0"))
        ra = env("BNB_READ_ALT_URL", env("BNB_SEND_ALT_URL", "https://bsc-dataseed.bnbchain.org"))
        self.read_alt = ra if ra not in ("0", E.RPC_URL) else None                      # a read BNB_RPC_URL failed is asked here once
        for u in self.send_urls + ([self.read_alt] if self.read_alt else []):
            x = urllib.parse.urlparse(u)
            if x.scheme != "https" or not x.hostname:
                raise SystemExit(f"BNB_SEND_URL / BNB_SEND_ALT_URL / BNB_READ_ALT_URL must be https URLs (host {E.host(u)})")
        if E.STAKE_USD > 10:                                                            # the probe is $5 (REPORT_BNB section 5): 15 is the dry run's
            raise SystemExit(f"BNB_STAKE_USD {E.STAKE_USD:g} is over $10: the live line is the $5 probe; set BNB_STAKE_USD=5 in /etc/flip/bnb.env")
        self.SLIP = s("BNB_SLIP", "0.05", 0.001, 0.15); self.SLIP_PPM = int(round(self.SLIP * 1e6))     # integer arithmetic for every bound
        self.PROBE_EVERY = s("BNB_PROBE_EVERY", "2", 1, 1000, True)
        self.MAX_OPEN = s("BNB_MAX_OPEN", "2", 1, 4, True)
        self.DAILY_STOP = s("BNB_DAILY_STOP_USD", "10", 0.1, 50)
        self.GAS = {"buy": s("BNB_GAS_BUY", "200000", 21000, 3_000_000, True), "approve": s("BNB_GAS_APPROVE", "80000", 21000, 3_000_000, True),
                    "sell": s("BNB_GAS_SELL", "180000", 21000, 3_000_000, True)}
        self.MIN_GWEI = s("BNB_MIN_GWEI", "0.1", 0.01, 5); self.MAX_GWEI = s("BNB_MAX_GWEI", "1", self.MIN_GWEI, 5)
        self.DEADLINE_S = s("BNB_DEADLINE_S", "60", 5, 3600, True)
        self.CHECK_MIN = s("BNB_CHECK_MIN", "0.99", 0.8, 1.0)                           # a clean round trip of this line returns 0.99501
        self.MAX_STAKE = int(s("BNB_MAX_STAKE_BNB", "0.015", 0.0001, 0.1) * 1e18)
        self.SELL_TRIES = s("BNB_SELL_TRIES", "3", 1, 10, True)
        self.RECEIPT_WAIT_S = s("BNB_RECEIPT_WAIT_S", "20", 5, 3600)
        self.BUY_LATE = s("BNB_BUY_LATE", "7", 0, 1000, True)                         # blocks past L+BUY_AT (by the head) after which a buy is not sent
        self.SELL_LATE = s("BNB_SELL_LATE", "20", 1, 1000, True)                      # blocks past L+SELL_AT (by the head) at which a lagging reader's position is sold
        if E.LAG_BLOCKS >= self.BUY_LATE:                                               # the reader sees L+BUY_AT LAG_BLOCKS behind the head: every buy would be late
            raise SystemExit(f"BNB_LAG_BLOCKS {E.LAG_BLOCKS} must stay below BNB_BUY_LATE {self.BUY_LATE}: every live buy would count as late")
        self.REBROADCAST_S = s("BNB_REBROADCAST_S", "5", 1, 600)                       # a transaction with no receipt is sent again to every endpoint this often
        self.REPLACE_S = s("BNB_REPLACE_S", "8", 2, 3600)                              # an approve or sell pending this long is signed anew at its nonce, its gas price raised
        self.LIVE_SIZES = E._sizes("BNB_LIVE_POOL_BNB", "1,10,25")                    # REPORT_BNB section 5: 1, 10 and 25 first, 2.5 later
        self.CODEHASHES = {h.strip().lower() for h in env("BNB_TOKEN_CODEHASHES", TOKEN_CODEHASHES).split(",") if h.strip()}
        if not self.CODEHASHES or not all(re.fullmatch(r"0x[0-9a-f]{64}", h) for h in self.CODEHASHES):
            raise SystemExit("BNB_TOKEN_CODEHASHES must be a comma list of 0x + 64 hex digits (the keccak of a token's runtime code)")
        logdir = os.path.dirname(os.path.abspath(E.LOG_PATH))
        self.HALT_FILE = env("BNB_HALT_FILE", os.path.join(logdir, "HALTED.bnb")); self.POS_FILE = env("BNB_POSITIONS_FILE", os.path.join(logdir, "bnb_positions.json"))
        for name, path in (("BNB_HALT_FILE", self.HALT_FILE), ("BNB_POSITIONS_FILE", self.POS_FILE), ("BNB_LOG_PATH", E.LOG_PATH)):
            if not own_file(path) or (name != "BNB_HALT_FILE" and os.path.basename(path) == "HALTED.bnb"):
                raise SystemExit(f"{name} {path}: live, the line's files must be named HALTED.bnb (the halt) or start with 'bnb' (never flip-engine's files)")
        if len({os.path.abspath(p) for p in (self.HALT_FILE, self.POS_FILE, E.LOG_PATH)}) < 3:
            raise SystemExit("BNB_HALT_FILE, BNB_POSITIONS_FILE and BNB_LOG_PATH must be three different files")
        art = json.load(open(ART)); self.CODE = art["deployedBytecode"]; self.SEL_RUN = art["selectors"]["run(address,address,address,uint256)"]
        with open(os.path.join(os.path.dirname(ART), "BnbRoundTrip.sol"), "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != art.get("source_sha256"):
                raise SystemExit(f"{ART} was not built from the BnbRoundTrip.sol beside it (sha256 differs): python3 contracts/compile_bnb.py")
        self.load_key()
        self.lock = threading.RLock(); self.q = queue.Queue(); self.stop = False
        self.pos, self.snaps, self.roles, self.hashes, self.traded = {}, {}, {}, set(), set()
        self.gate_rets, self.recent, self.approved, self.eligible = [], [], set(), 0
        self.day, self.pnl_today, self.stop_logged = self.today(), 0.0, False
        self.halted = None; self.off = None; self.nonce = None; self.balance = None; self.balance_at = 0.0; self.balance_ok_at = -1e9; self.saved_at = 0.0
        self.mined_nonces, self.new_codes = {}, set()                                   # nonce -> our transaction mined with it; code hashes alarmed once
        self.unlogged = []; self.last_reply = (None, None)                              # trade_done lines saved, not yet in the log; the last send's answer
        self.POLL_S = 0.4                                                                # a transaction's receipt asked at most this often
        self.REBROADCAST_BEFORE_S = 10; self.EXPIRED_AFTER_S = 15                       # a copy is sent again only this long before its deadline; dropped this long after
        self.MAX_REPLACE = 3                                                             # replacements of one pending transaction at most
        self.dirty = False; self.snapped_at = 0.0; self.thread = None
        self.halt_written = True; self.halt_seen_at = 0.0                              # the halt file written (else tried again at each save); last looked at
        self.head_val, self.head_ok_at, self.head_polled_at = None, time.monotonic(), 0.0   # the newest head known and when a source last answered
        self.HEAD_POLL_S, self.HEAD_BLIND_S = 3.0, HEAD_BLIND_S                        # the worker asks the head itself after this long without one; extrapolates after this
        self.fin, self.fin_at = None, -1e9                                               # the chain's finalized block, read at most every POLL_S
        self.off_at, self.SELFTEST_RETRY_S = 0.0, 300                                   # a failed self-test is run again this often
        self.lock_fds = []
        try:                                                                            # one live engine at a time: one positions file, and one user of the key (its nonce)
            for path, flags in ((self.POS_FILE + ".lock", os.O_RDWR | os.O_CREAT), (self.key_file, os.O_RDONLY)):
                fd = os.open(path, flags, 0o600); self.lock_fds.append(fd)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise SystemExit(f"another live BNB engine holds {path} (the service and a manual run at once, or bnb_wallet.py running?): stop it first") from None
        except OSError as e:
            self.close()
            raise SystemExit(f"{self.POS_FILE}.lock or the key file cannot be opened ({e.strerror})") from None
        except SystemExit:
            self.close(); raise

    def close(self):
        """the worker stops and the instance locks are let go (a process's exit does the same)"""
        self.stop = True
        for fd in getattr(self, "lock_fds", []):
            os.close(fd)
        self.lock_fds = []

    def shutdown(self, wait_s=8):
        """SIGTERM (a restart, a deploy, the owner's stop): nothing new is sent, the worker finishes the step it is in (a transaction being
        sent is recorded before its send and its state saved after it), the positions file is written, then the process exits"""
        self.stop = True
        t = self.thread
        if t is not None and t is not threading.current_thread():
            t.join(wait_s)
        if self.lock.acquire(timeout=2):                                                # (a worker stuck past the wait must not hold the exit)
            try:
                self.save()
            finally:
                self.lock.release()

    # ------------------------------------------------------------ the key: read once, checked against BNB_WALLET, never shown
    def load_key(self):
        try:
            st = os.stat(self.key_file)
        except OSError as e:
            raise SystemExit(f"BNB_KEY_FILE {self.key_file} cannot be read ({e.strerror}): deploy/bnb_wallet.py creates it") from None
        if st.st_mode & 0o077:
            raise SystemExit(f"{self.key_file} is open to other users (mode {oct(st.st_mode & 0o777)}): sudo chmod 600 {self.key_file}")
        if st.st_uid != os.geteuid():
            raise SystemExit(f"{self.key_file} is owned by uid {st.st_uid}, not by this process's user (uid {os.geteuid()}): sudo chown root:root {self.key_file}")
        try:
            from eth_account import Account
            from eth_utils import to_checksum_address
            with open(self.key_file) as f:
                acct = Account.from_key(f.read().strip())
        except Exception:
            raise SystemExit(f"{self.key_file} does not hold a usable key (its content is never printed), or eth_account is missing") from None
        if acct.address.lower() != self.wallet:
            raise SystemExit(f"the key in {self.key_file} is for {acct.address.lower()}, BNB_WALLET is {self.wallet}")
        from eth_utils import keccak
        self.acct = acct; self.checksum = to_checksum_address; self.keccak = keccak

    def sign(self, tx):
        s = self.acct.sign_transaction(tx)
        raw = getattr(s, "raw_transaction", None) or s.rawTransaction
        return "0x" + bytes(raw).hex(), "0x" + bytes(s.hash).hex()

    # ------------------------------------------------------------ small things
    def log(self, ev):
        self.E.log(ev)

    def alarm(self, what, **kw):
        self.E.alarm(what, **kw)

    def scrub(self, x, n=200):
        t = self.E.scrub(x, 10 ** 6)
        for u in self.send_urls + ([self.read_alt] if getattr(self, "read_alt", None) else []):
            t = t.replace(u, self.E.host(u))
            try:
                p = urllib.parse.urlparse(u)
            except ValueError:
                continue
            for part, mark in ((p.query, "<query>"), (p.path if len(p.path) > 1 else "", "/<path>"), (p.netloc.rpartition("@")[0], "<user>")):
                if part:
                    t = t.replace(part, mark)
        return t[:n]

    @staticmethod
    def today():
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    def wake(self):
        self.q.put(1)

    def roll_day(self):
        d = self.today()
        if d != self.day:
            self.day, self.pnl_today, self.stop_logged = d, 0.0, False

    def open_count(self, exclude=None):
        return sum(1 for k, x in self.pos.items() if k != exclude)

    def blocked(self, exclude=None):
        """why no new buy may start now, or None"""
        self.roll_day()
        if self.off:
            return "live is off for this run: " + self.off
        if not self.halted and time.monotonic() - self.halt_seen_at >= 1:                # the owner's stop (echo ... > HALTED.bnb) holds without a restart
            self.halt_seen_at = time.monotonic()
            if os.path.exists(self.HALT_FILE):
                try:
                    with open(self.HALT_FILE) as f:
                        why = f.read().strip()[:300] or "halted"
                except OSError:
                    why = "halted"
                self.halted = why
                self.alarm(f"the BNB line halted by its halt file: {why}; open positions are still sold; remove {self.HALT_FILE} and restart flip-bnb to resume",
                           halt_file=self.HALT_FILE)
                self.mark()
        if self.halted:
            return "halted: " + self.halted
        if self.pnl_today <= -self.DAILY_STOP:
            return f"the daily stop (${self.pnl_today:+.2f} today, BNB_DAILY_STOP_USD {self.DAILY_STOP:g})"
        n = self.open_count(exclude)
        if n >= self.MAX_OPEN:
            return f"{n} live position(s) open (BNB_MAX_OPEN {self.MAX_OPEN})"
        return None

    def halt(self, reason):
        """the gate: no new buy until HALTED.bnb is removed and the service restarted; what is open is still sold"""
        with self.lock:
            first = self.halted is None
            self.halted = self.halted or reason
            for k in [k for k, x in self.pos.items() if x["state"] in ("armed", "checked", "buy_due")]:
                self.drop(k, "held", "the line halted before the buy")
        if first:
            self.write_halt()
        self.alarm(f"the BNB line halted: {reason}; open positions are still sold; remove {self.HALT_FILE} and restart flip-bnb to resume" if first
                   else f"the BNB line (already halted) would halt again: {reason}", halt_file=self.HALT_FILE)
        self.mark()

    def write_halt(self):
        """the halt file; one that cannot be written is tried again at every save, and the positions file says so (a restart keeps the halt)"""
        try:
            with open(self.HALT_FILE, "w") as f:
                f.write(self.halted + "\n")
            self.halt_written = True
        except Exception as e:
            first = self.halt_written; self.halt_written = False
            if first:
                self.alarm(f"the halt file {self.HALT_FILE} could not be written ({self.scrub(e, 80)}): tried again at every save; the positions file keeps the halt")

    def drop(self, pair, role, why):
        """a position that never bought: the pool stays dry (its role says why)"""
        x = self.pos.pop(pair, None)
        self.roles[pair] = role
        self.log({"ev": "live_skip", "pair": pair, "L": x["L"] if x else None, "role": role, "why": why})

    # ------------------------------------------------------------ chain reads (the engine's RPC: tried again, never the key)
    def rpc(self, method, params, tries=3, timeout=10, alt=True):
        """the engine's RPC; a read it could not answer is asked once at BNB_READ_ALT_URL (the sale's reads, the receipts and the nonce
        must not depend on one public node). Not for the buy's own fast reads (alt False: they have their own fallbacks)"""
        try:
            return self.E.rpc(method, params, tries=tries, timeout=timeout)
        except Exception as e:
            if not (alt and self.read_alt):
                raise
            try:
                return self.alt_rpc(method, params, timeout)
            except Exception as e2:
                raise RuntimeError(f"{self.scrub(e, 120)}; at {self.E.host(self.read_alt)}: {self.scrub(e2, 120)}") from None

    def alt_rpc(self, method, params, timeout):
        """one JSON-RPC call to BNB_READ_ALT_URL (an error names its host only)"""
        req = urllib.request.Request(self.read_alt, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                     {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method}: HTTP {e.code}") from None
        if not isinstance(d, dict) or "result" not in d:
            raise RuntimeError(f"{method}: {self.scrub(json.dumps((d or {}).get('error') if isinstance(d, dict) else d), 160)}")
        return d["result"]

    def gas_price(self, fast=False):
        """eth_gasPrice kept between BNB_MIN_GWEI and BNB_MAX_GWEI (fast, on the buy's path: one try of 3 s, else the floor)"""
        lo, hi = int(round(self.MIN_GWEI * 1e9)), int(round(self.MAX_GWEI * 1e9))
        try:
            gp = int(self.rpc("eth_gasPrice", [], **(FAST if fast else {})), 16)
        except Exception as e:
            self.alarm(f"eth_gasPrice not read ({self.scrub(e, 80)}): {self.MIN_GWEI:g} gwei", quiet_key="gasprice", every_s=300); gp = lo
        if gp > hi:
            self.alarm(f"the network asks {gp / 1e9:g} gwei, above BNB_MAX_GWEI {self.MAX_GWEI:g}: sent at the cap", quiet_key="gascap", every_s=300)
        return min(max(gp, lo), hi)

    def reserves(self, pair, side, fast=False):
        r = self.E.words(self.rpc("eth_call", [{"to": pair, "data": "0x" + SEL_RESERVES}, "latest"], **(FAST if fast else {})))
        return (r[0], r[1]) if side == 0 else (r[1], r[0])                           # (WBNB, token)

    def token_balance(self, token, both=False, alt=False):
        """the wallet's balance of the token (alt: BNB_READ_ALT_URL's alone); both: the larger of BNB_RPC_URL's and BNB_READ_ALT_URL's (a
        buy's tokens seen by either are there: a backend that lags shows the balance before the buy; raises when the second cannot answer)"""
        call = [{"to": token, "data": "0x" + SEL_BALANCE + a(self.wallet)}, "latest"]
        if alt:
            return self.E.words(self.alt_rpc("eth_call", call, 5))[0]
        bal = self.E.words(self.rpc("eth_call", call))[0]
        if both and self.read_alt:
            bal = max(bal, self.E.words(self.alt_rpc("eth_call", call, 5))[0])
        return bal

    def allowance(self, token, alt=False):
        call = [{"to": token, "data": "0x" + SEL_ALLOWANCE + a(self.wallet) + a(self.E.ROUTER)}, "latest"]
        return self.E.words(self.alt_rpc("eth_call", call, 5) if alt else self.rpc("eth_call", call))[0]

    def alt_receipt(self, group):
        """BNB_READ_ALT_URL's view of our transactions at one nonce, before anything is dropped or settled for want of a receipt on
        BNB_RPC_URL: (the one mined, its receipt) once its block is final there, "unfinal" when one is mined there in a block not final
        yet (or its receipt is not served yet), "pending" when it holds one unmined, else None; raises when it cannot answer"""
        for t in group[::-1]:
            tx = self.alt_rpc("eth_getTransactionByHash", [t["hash"]], 5)
            if not tx:
                continue
            if not tx.get("blockNumber"):
                return "pending"
            if int(tx["blockNumber"], 16) > int(self.alt_rpc("eth_getBlockByNumber", ["finalized", False], 5)["number"], 16):
                return "unfinal"
            r = None
            try:
                r = next((r_ for r_ in self.alt_rpc("eth_getBlockReceipts", [tx["blockNumber"]], 5) or [] if r_.get("transactionHash", "").lower() == t["hash"].lower()), None)
            except Exception:
                pass
            r = r or self.alt_rpc("eth_getTransactionReceipt", [t["hash"]], 5)
            return (t, r) if r else "unfinal"
        return None

    def read_balance(self, fast=False):
        self.balance = int(self.rpc("eth_getBalance", [self.wallet, "latest"], **(FAST if fast else {})), 16); self.balance_at = self.balance_ok_at = time.monotonic()
        return self.balance

    def receipt(self, h):
        """(receipt or None, whether the node knows the transaction): its block from eth_getTransactionByHash, then that block's receipts
        (publicnode serves eth_getBlockReceipts but refuses eth_getTransactionReceipt without a token), else eth_getTransactionReceipt"""
        tx = self.rpc("eth_getTransactionByHash", [h], tries=2)
        if not tx or not tx.get("blockNumber"):
            return None, bool(tx)
        try:
            for r in self.rpc("eth_getBlockReceipts", [tx["blockNumber"]], tries=2) or []:
                if r.get("transactionHash", "").lower() == h.lower():
                    return r, True
        except Exception:
            pass
        return self.rpc("eth_getTransactionReceipt", [h], tries=2), True

    # ------------------------------------------------------------ sending: one worker thread, one nonce sequence
    def post(self, url, raw):
        """eth_sendRawTransaction to one endpoint: ("ok"|"in"|"nonce"|"rejected"|"unknown", what it said)"""
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": [raw]}).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=4))
        except urllib.error.HTTPError as e:
            try:
                d = json.loads(e.read())                                             # a JSON-RPC error inside an HTTP error status
            except Exception:
                return "unknown", f"HTTP {e.code}"
        except Exception as e:
            return "unknown", self.scrub(e, 120)
        if not isinstance(d, dict):
            return "unknown", "not a JSON-RPC answer"
        if d.get("result"):
            return "ok", None
        err = d.get("error")
        msg = self.scrub((err or {}).get("message") if isinstance(err, dict) else err, 160)
        return reply_kind(msg), msg

    def post_all(self, raw):
        """the same signed transaction to every send endpoint at once (one transaction has one hash: a second copy is harmless, and an
        endpoint that takes it but does not pass it on is covered by the other): [(kind, message, host)], back at the first ok/in (the
        other posts finish on their own), else when every endpoint answered"""
        if len(self.send_urls) == 1:
            u = self.send_urls[0]; k, msg = self.post(u, raw)
            return [(k, msg, self.E.host(u))]
        q = queue.Queue()

        def one(u):
            try:
                k, msg = self.post(u, raw)
            except Exception as e:
                k, msg = "unknown", self.scrub(e, 120)
            q.put((k, msg, self.E.host(u)))
        for u in self.send_urls:
            threading.Thread(target=one, args=(u,), daemon=True).start()
        out = []
        for _ in self.send_urls:
            try:
                out.append(q.get(timeout=15))                                          # (post() gives up after 4 s)
            except queue.Empty:
                break
            if out[-1][0] in ("ok", "in"):
                break
        return out

    def broadcast(self, raw):
        """the transaction to every send endpoint (post_all): taken when one says ok or already known; a second round when no endpoint
        gave a definite answer. Otherwise the most telling answer: nonce, rejected, unknown"""
        got = []
        for _ in range(2):
            for g in self.post_all(raw):
                if g[0] in ("ok", "in"):
                    return g
                got.append(g)
            if any(k != "unknown" for k, _, _ in got):
                break
        return next((g for want in ("nonce", "rejected", "unknown") for g in got if g[0] == want), ("unknown", "no answer", "-"))

    def read_nonce(self):
        self.nonce = int(self.rpc("eth_getTransactionCount", [self.wallet, "pending"]), 16)
        self.log({"ev": "live_nonce", "nonce": self.nonce})
        return self.nonce

    def send_tx(self, x, kind, to, value, data, gas, gp, info, nonce=None):
        """sign with the sequencer's nonce and send; the record is written before the send (a restart finds it). Returns the record, or
        None when nothing went in (also when the nonce cannot be read, or the engine is stopping). A nonce error reads the nonce again and
        signs anew (at most 3 times), unless this very transaction is already known (a copy that went in). With nonce: a replacement of a
        pending transaction at that nonce, signed once; the sequence is not touched, and a refusal leaves the pending one as it was."""
        self.last_reply = (None, None)
        if self.stop:
            return None
        for attempt in range(3 if nonce is None else 1):
            if nonce is not None:
                n = nonce
            elif self.nonce is not None:
                n = self.nonce
            else:
                try:
                    n = self.read_nonce()
                except Exception as e:
                    self.alarm(f"the {kind} was not sent: the wallet's nonce was not read ({self.scrub(e, 80)})", quiet_key="nonce-read", every_s=60, pair=x["pair"])
                    return None
            raw, h = self.sign({"nonce": n, "gasPrice": gp, "gas": gas, "to": self.checksum(to), "value": value, "data": data, "chainId": self.E.CHAIN_ID})
            rec = {"kind": kind, "hash": h, "nonce": n, "gas": gas, "gas_price": gp, "value": value, "raw": raw, "sent_at": time.time(), "rebroadcast": 0, **info}
            with self.lock:
                x["txs"].append(rec); self.hashes.add(h)
            self.save()
            k, msg, via = self.broadcast(raw)
            if k == "nonce" and self.known(h):
                k = "in"
            self.last_reply = (k, msg)
            self.log({"ev": "live_send", "kind": kind, "pair": x["pair"], "L": x["L"], "hash": h, "nonce": n, "gas": gas, "gwei": gp / 1e9, "value_wei": value,
                      **info, "reply": k, "detail": msg, "via": via, "attempt": attempt + 1})
            if k in ("ok", "in", "unknown"):                                       # unknown: perhaps in; its receipt (or its absence) decides
                if nonce is None:
                    self.nonce = n + 1 if k != "unknown" else None
                return rec
            with self.lock:
                x["txs"].remove(rec); self.hashes.discard(h)
            self.save()
            if nonce is not None:                                                       # a replacement not taken: the pending one stays
                self.alarm(f"the {kind}'s replacement at nonce {n} was not taken ({k}: {msg})", quiet_key="replace-" + kind, every_s=60, pair=x["pair"])
                return None
            if k == "nonce":
                self.nonce = None; continue
            self.alarm(f"the {kind} was refused by the node ({msg}): nothing went in", quiet_key="refused-" + kind, every_s=60, pair=x["pair"])
            return None
        self.alarm(f"the {kind} was not sent: nonce errors 3 times", pair=x["pair"])
        return None

    def known(self, h):
        try:
            return bool(self.rpc("eth_getTransactionByHash", [h], tries=2))
        except Exception:
            return False

    # ------------------------------------------------------------ the engine's hooks (the reader's thread): quick, no network
    def on_launch(self, p):
        """a launch of a traded size: its slot (live or control) when its size is one BNB_LIVE_POOL_BNB lists (the slots alternate within
        those sizes), else it stays dry (role dry_size, out of the control); a live slot is armed and checked by the worker"""
        if p["skip"]:
            return
        with self.lock:
            if any(abs(p["size"] - s_) < 0.005 for s_ in self.LIVE_SIZES):
                self.eligible += 1; n = self.eligible
                role = "live" if (n - 1) % self.PROBE_EVERY == 0 else "control"
                why = self.blocked() if role == "live" else None
                role = "held" if why else role
            else:
                n, role, why = None, "dry_size", f"pool size {p['size']:g} BNB is not traded live (BNB_LIVE_POOL_BNB {','.join('%g' % x for x in self.LIVE_SIZES)})"
            self.roles[p["pair"]] = role
            if role == "live":
                self.pos[p["pair"]] = {"pair": p["pair"], "token": p["token"], "side": p["side"], "L": p["L"], "pool_bnb": p["size"], "state": "armed",
                                       "q_check": self.E.stake_wei(), "factor_ppm": PPM, "txs": [], "gas_wei": 0, "sell_tries": 0, "approve_tries": 0}
        self.log({"ev": "live_arm", "pair": p["pair"], "L": p["L"], "pool_bnb": p["size"], "role": role, "slot": n, "why": why})
        if role == "live":
            self.mark()

    def on_fire(self, p, B):
        """the engine's buy at L+BUY_AT: a checked live position is bought with the engine's stake, minOut from its own tokens"""
        with self.lock:
            x = self.pos.get(p["pair"])
            if x is None or x["state"] in OPEN:                                         # (OPEN: a resumed position whose pool copy predates its buy)
                return
            if x["state"] != "checked":
                self.drop(p["pair"], "unchecked", f"the pre-buy check had not finished ({x['state']})"); return
            why = self.blocked(exclude=p["pair"])
            if why:
                self.drop(p["pair"], "held", why); return
            if p["q"] <= 0 or p["tok"] <= 0:                                            # the engine found no tokens for the stake (no reserves)
                self.drop(p["pair"], "held", "no tokens for the stake at +%d" % self.E.BUY_AT); return
            x.update(state="buy_due", q=p["q"], exp_tokens=p["tok"], min_out=bound(p["tok"], x.get("f_buy", x["factor_ppm"]), self.SLIP_PPM), r_wbnb=p["rq"],
                     r_token=p["rt"], fire_block=B)
        self.mark()

    def on_sell(self, p, B, back):
        """the engine's sale at L+SELL_AT: the live position is sold; a traded pool with no crowd buy in +60..+260 halts the line, when
        its logs were all read (after a restart or a jump the crowd's buys in the blocks missed were never seen: an alarm, not a halt)"""
        q = p["q"]; dry = {"dry_ret": round((back - q - int(round(self.E.GAS_UNITS * self.E.GAS_GWEI * 1e9))) / q, 6), "dry_ret_gross": round((back - q) / q, 6), "dry_back_wei": back}
        self.sell_due(p, f"sell at +{self.E.SELL_AT}", dry, B)
        if p["pair"] in self.traded and p["crowd_gate"] == 0:
            why = f"no crowd buy in +{self.E.GATE_CROWD_FROM}..+{self.E.SELL_AT} on a traded pool ({p['pair']}, {p['size']:g} BNB)"
            if p["gaps"] or p["breaks"]:
                self.alarm(f"gate not judged (blocks or logs missed: gaps {p['gaps']}, breaks {p['breaks']}): {why}", pair=p["pair"])
            else:
                self.halt(why)

    def on_dump(self, p, off):
        """a dump: an open position is sold at once; before +997 on any pool of the line (traded, control or not traded live; the 15-BNB
        pools aside) it halts the line: the creator's schedule (+997 at the earliest, REPORT_BNB section 3) has changed"""
        self.sell_due(p, f"the dump at +{off}", {"dry_ret": -1.0, "dry_ret_gross": -1.0, "dry_back_wei": 0}, None)
        if not p["skip"] and off < self.E.GATE_DUMP_BEFORE:
            self.halt(f"a dump at +{off}, before +{self.E.GATE_DUMP_BEFORE}, on a {'traded' if p['pair'] in self.traded else 'watched'} pool of the line "
                      f"({p['pair']}, {p['size'] or 0:g} BNB, {self.roles.get(p['pair']) or 'no slot'})")

    def on_finish(self, p, why):
        """the pool is no longer watched: an open position with no sale due is sold at once; one that never bought is dropped"""
        with self.lock:
            x = self.pos.get(p["pair"])
            if x is not None and x["state"] in ("armed", "checked", "buy_due"):
                self.drop(p["pair"], "held", f"the pool was dropped before the buy ({why or 'watched to its end'})")
            self.snaps.pop(p["pair"], None); self.roles.pop(p["pair"], None); self.traded.discard(p["pair"])
        self.sell_due(p, f"the pool is no longer watched ({why or 'watched to its end'})", None, None)
        self.mark()

    def sell_due(self, p, why, dry, B):
        """a sale due (the first reason kept): for a position holding or buying tokens, and for one whose buy is due, which then is not sent"""
        with self.lock:
            x = self.pos.get(p["pair"])
            if x is None or (x["state"] not in OPEN and x["state"] != "buy_due") or x.get("sell_due"):
                return
            x["sell_due"] = {"why": why, "r_wbnb": p["rq"], "r_token": p["rt"], "block": B, "at": time.time(), **(dry or {})}
        self.mark()

    def ours(self, lg):
        """a log of one of our own transactions (the dry copy and the crowd's counts leave it out)"""
        return lg.get("transactionHash") in self.hashes

    def tag(self, p):
        return {"live": False, "role": self.roles.get(p["pair"])}

    def after_range(self, b):
        """the pools of open or traded positions copied after every range (this thread owns the pools; a few small records) for the
        positions file, which the worker writes on its own changes and, for these copies alone, at most every 5 s"""
        with self.lock:
            for k in set(self.pos) | self.traded:
                if k in self.E.pools:
                    self.snaps[k] = json.loads(json.dumps(self.E.pools[k]))
        if time.monotonic() - self.snapped_at >= 5:
            self.snapped_at = time.monotonic(); self.mark()

    def mark(self):
        """the reader's thread changed something: the worker writes the positions file (only the worker writes it)"""
        self.dirty = True; self.wake()

    # ------------------------------------------------------------ the worker
    def run(self):
        try:
            while not self.stop:
                try:
                    self.q.get(timeout=0.25)
                except queue.Empty:
                    pass
                try:
                    self.tick()
                except Exception as e:
                    self.alarm(f"live: {type(e).__name__}: {self.scrub(e)}", quiet_key="live", every_s=60, trace=self.scrub(traceback.format_exc(), 400))
        except BaseException:
            try:
                self.log({"ev": "alarm", "what": "the live worker crashed", "trace": self.scrub(traceback.format_exc(), 800)})
            finally:
                os._exit(1)

    def tick(self):
        self.roll_day()
        if time.monotonic() - self.balance_at > 60:
            try:
                self.read_balance()
            except Exception:
                self.balance_at = time.monotonic()
        self.poll_head()
        if self.off and self.off.startswith("the pre-buy check's self-test") and time.monotonic() - self.off_at >= self.SELFTEST_RETRY_S:
            self.off_at = time.monotonic(); why = self.self_test()                      # a failed self-test (a brief RPC error at the start) is run again
            if why is None:
                self.off = None; self.alarm("live is on again: the pre-buy check's self-test passed")
            else:
                self.alarm(f"live is still off: {why}", quiet_key="selftest", every_s=3600)
        self.sell_by_head()
        with self.lock:
            pairs = sorted(self.pos, key=lambda k: not self.pos[k].get("sell_due"))   # a sale due first: it never waits behind a check or a buy
        for pair in pairs:
            if self.stop:
                break
            x = self.pos.get(pair)
            if x is None:
                continue
            try:                                                                        # one position's trouble (a read that keeps failing) never starves the others
                self.step(x)
            except Exception as e:
                self.alarm(f"live ({pair}): {type(e).__name__}: {self.scrub(e)}", quiet_key="live-" + pair, every_s=60, pair=pair, trace=self.scrub(traceback.format_exc(), 400))
        if self.dirty:
            self.save()

    def step(self, x):
        st = x["state"]
        if st == "armed":
            self.check(x)
        elif st == "buy_due":
            self.buy(x)
        elif st == "buying":                                                            # left over (buy() resolves its own): a buy record decides
            self.unbuying(x, "a buy left half-sent")
        elif st in ("buy_sent", "approve_sent", "sell_sent"):
            self.poll(x)
        elif st == "bought" and time.time() >= x.get("sell_wait", 0):
            self.approve(x)
        elif st == "approved" and x.get("sell_due") and time.time() >= x.get("sell_wait", 0):
            self.sell(x)

    def unbuying(self, x, why):
        """a position stopped in 'buying': with a buy record it was (perhaps) sent, so its receipt decides; without one nothing went"""
        with self.lock:
            if self.pos.get(x["pair"]) is not x or x["state"] != "buying":
                return
            if any(t["kind"] == "buy" for t in x["txs"]):
                x["state"] = "buy_sent"; self.traded.add(x["pair"])
            else:
                self.traded.discard(x["pair"]); self.drop(x["pair"], "unsent", f"the buy was not sent ({why})")
        self.save()

    # ------------------------------------------------------------ the chain's head as the worker knows it
    def head(self):
        """the newest head known (no network): the reader's (its websocket or its eth_blockNumber) or the worker's own poll; when no source
        has shown a new block for HEAD_BLIND_S, extrapolated at BLOCK_S a block (a sale must not wait on a stalled reader and a dead or
        stalled feed)"""
        h = self.E.state.get("head")
        if h and (self.head_val is None or h > self.head_val):
            self.head_val, self.head_ok_at = h, time.monotonic()
        if self.head_val is None:
            return None
        blind = time.monotonic() - self.head_ok_at
        return self.head_val + (int(blind / BLOCK_S) if blind > self.HEAD_BLIND_S else 0)

    def poll_head(self):
        """the worker asks eth_blockNumber itself (with the read fallback) when no head came for HEAD_POLL_S: the reader polls only between
        its own calls, which can hang for tens of seconds. Only a newer block counts as a head that came (a node that stalls and still
        answers its last number leaves the head to be extrapolated after HEAD_BLIND_S, with an alarm)"""
        self.head()
        now = time.monotonic()
        if now - self.head_ok_at < self.HEAD_POLL_S or now - self.head_polled_at < 1:
            return
        self.head_polled_at = now
        try:
            n = int(self.rpc("eth_blockNumber", [], tries=1, timeout=3), 16)
        except Exception as e:
            self.alarm(f"no head from the reader for {now - self.head_ok_at:.0f} s and eth_blockNumber not read ({self.scrub(e, 80)})", quiet_key="headpoll", every_s=60)
            return
        if self.head_val is None or n > self.head_val:                                 # a new block only: a node that stalls and still answers its
            self.head_val, self.head_ok_at = n, now                                     # last head is no fresher than one that does not answer
        elif now - self.head_ok_at >= self.HEAD_BLIND_S:
            self.alarm(f"eth_blockNumber still answers {n}, no new block for {now - self.head_ok_at:.0f} s: the head is extrapolated at {BLOCK_S} s a block",
                       quiet_key="headstill", every_s=60)

    def sell_by_head(self):
        """the sale follows the chain, not the reader: while the reader lags (an RPC stall; it jumps only MAX_BEHIND blocks behind), a
        position holding (or buying) tokens is sold once the head is BNB_SELL_LATE blocks past its L+SELL_AT, long before the creator's
        earliest drain (+997); the sale reads the pool's reserves then"""
        head = self.head()
        if not head:
            return
        late = []
        with self.lock:
            for x in self.pos.values():
                off = head - self.E.LAG_BLOCKS - x["L"]
                if x["state"] in ("buy_sent", "bought", "approve_sent", "approved") and not x.get("sell_due") and off >= self.E.SELL_AT + self.SELL_LATE:
                    est = "" if head == self.head_val else ", estimated: no head for %.0f s" % (time.monotonic() - self.head_ok_at)
                    x["sell_due"] = {"why": f"the reader is behind: sold by the head (L+{head - x['L']}{est})", "r_wbnb": None, "r_token": None, "block": None, "at": time.time()}
                    late.append((x["pair"], off))
        for pair, off in late:
            self.alarm(f"the reader is {head - (self.E.state.get('done_to') or 0)} blocks behind the head: a live position sold by the head at +{off}", pair=pair)
        if late:
            self.mark()

    def check(self, x):
        """the pre-buy check: the token's code is one of the line's templates, and the round trip of the stake simulated by eth_call on the
        pool as it is (the harness's code by state override)"""
        q = x["q_check"]; info = {"pair": x["pair"], "L": x["L"], "pool_bnb": x["pool_bnb"], "stake_wei": q}
        try:
            code = self.rpc("eth_getCode", [x["token"], "latest"])
            ch = "0x" + bytes(self.keccak(hexstr=code)).hex(); size = max(0, len(code) // 2 - 1)
            if ch not in self.CODEHASHES:                                               # a template the line never had: a delayed tax or blacklist passes a round trip
                self.log({"ev": "live_check", **info, "ok": False, "why": f"the token's code {ch[:18]}... is not one of the line's (BNB_TOKEN_CODEHASHES)", "code_hash": ch,
                          "code_bytes": size})
                if ch not in self.new_codes:
                    self.new_codes.add(ch)
                    self.alarm(f"a launch of the line with a new token code {ch} ({size} bytes): refused; look at the token before adding its hash to "
                               "BNB_TOKEN_CODEHASHES", pair=x["pair"], token=x["token"])
                with self.lock:
                    if self.pos.get(x["pair"]) is x and x["state"] == "armed":
                        self.drop(x["pair"], "refused", "the token's code is not one of the line's templates")
                self.save(); return
            res = self.simulate(x["token"], q)
            rq, rt = self.reserves(x["pair"], x["side"])
        except Exception as e:
            self.log({"ev": "live_check", **info, "ok": False, "why": f"the check did not run ({self.scrub(e, 120)})"})
            with self.lock:
                self.drop(x["pair"], "refused", "the pre-buy check did not run")
            return
        stage, tokens, back, est = res
        tok_i = self.E.amount_out(q, rq, rt); back_i = self.E.amount_out(tok_i, rt - tok_i, rq + q)
        factor = min(PPM, back * PPM // back_i) if back_i > 0 else PPM              # the token's own cut beyond the pool's fees over the round trip, ppm (1e6: none)
        f_buy = min(PPM, tokens * PPM // tok_i) if tok_i > 0 else PPM               # each leg's own cut: the tokens the buy gave against the formula's,
        back_t = self.E.amount_out(tokens, rt - tok_i, rq + q)
        f_sell = min(PPM, back * PPM // back_t) if back_t > 0 else PPM              # and the sale of those tokens against the formula's for them
        why = ({1: "the simulated buy reverted", 2: "the simulated approve failed", 3: "the simulated sell reverted"}.get(stage)
               or (f"the simulated sale returns {back / q:.1%} of the stake, under BNB_CHECK_MIN {self.CHECK_MIN:.0%}" if back < self.CHECK_MIN * q else None)
               or next((f"the simulated {k} needs ~{est[k]} gas, over BNB_GAS_{k.upper()} {self.GAS[k]}" for k in ("buy", "approve", "sell") if est[k] > self.GAS[k]), None))
        self.log({"ev": "live_check", **info, "ok": why is None, "why": why, "stage": stage, "tokens": tokens, "back_wei": back, "back_ratio": round(back / q, 6),
                  "ideal_ratio": round(back_i / q, 6), "factor_ppm": factor, "f_buy_ppm": f_buy, "f_sell_ppm": f_sell, "gas_est": est, "code_hash": ch})
        with self.lock:
            if x["pair"] not in self.pos or x["state"] != "armed":
                return
            if why:
                self.drop(x["pair"], "refused", why)
            else:
                x.update(state="checked", factor_ppm=factor, f_buy=f_buy, f_sell=f_sell,
                         check={"ratio": round(back / q, 6), "factor_ppm": factor, "f_buy_ppm": f_buy, "f_sell_ppm": f_sell, "gas_est": est})
        self.save()

    def simulate(self, token, q):
        """(stage, tokens, BNB back, {leg: the gas limit a transaction of its own needs}) of BnbRoundTrip.run on the chain as it is: the
        harness's own gas per leg plus what a transaction of its own needs on top (the minimum limits measured Oct 12 with eth_simulateV1 on
        the two token templates: buy 155,768 / 163,541, approve ~46.5k / 48.1k, sell 135,596 / 143,369, against the harness's 136,550 /
        144,252, 24,932 / 26,525 and 70,714 / 78,473: added here 20k, 23k and 65k)"""
        data = "0x" + self.SEL_RUN + a(self.E.ROUTER) + a(self.E.WBNB) + a(token) + w(q)
        r = self.E.words(self.rpc("eth_call", [{"from": self.wallet, "to": HARNESS, "data": data, "gas": hex(3_000_000)}, "latest",
                                               {HARNESS: {"code": self.CODE, "balance": hex(q)}}]))
        if len(r) < 6:
            raise ValueError("a short answer")
        st = r[0]
        return st, r[1], r[2], {"buy": r[3] + 20_000 if st != 1 else 0, "approve": r[4] + 23_000 if st in (0, 3) else 0, "sell": r[5] + 65_000 if st == 0 else 0}

    def late(self, x, head=None):
        """(how many blocks after L+BUY_AT a buy sent now lands at the earliest, the head): the next block after the chain's head (head(),
        or the one given), never the reader's done_to alone (it lags the head by LAG_BLOCKS, and by up to MAX_BEHIND while it catches up
        after an RPC stall; inside a range it still holds the range before: the block the engine fired in was already read, so the head is
        past it too)"""
        done_to = self.E.state.get("done_to") or 0
        head = max((self.head() if head is None else head) or 0, done_to + self.E.LAG_BLOCKS, (x.get("fire_block") or 0) - 1 + self.E.LAG_BLOCKS)
        return head + 1 - (x["L"] + self.E.BUY_AT), head

    def head_now(self):
        """the head for the buy's last lateness check: eth_blockNumber read now (one try, HEAD_NOW_S at most), the newest of it and the
        reader's; when it cannot be read, or answers no newer block, the newest head known plus a block for every BLOCK_S since it came
        (a head up to HEAD_BLIND_S old is otherwise taken as it is: about 22 blocks a buy could go out late)"""
        try:
            n = int(self.rpc("eth_blockNumber", [], tries=1, timeout=HEAD_NOW_S, alt=False), 16)
            if self.head_val is None or n > self.head_val:                             # (the same head again is not a fresh one: aged below)
                self.head_val, self.head_ok_at = n, time.monotonic()
        except Exception as e:
            self.alarm(f"the head not read before a buy ({self.scrub(e, 80)}): the last one aged at {BLOCK_S} s a block", quiet_key="headnow", every_s=300)
        h = self.head()
        if h is None:
            return None
        return max(h, self.head_val + int((time.monotonic() - self.head_ok_at) / BLOCK_S))

    def buy(self, x):
        with self.lock:
            if self.pos.get(x["pair"]) is not x or x["state"] != "buy_due":
                return                                                                  # dropped meanwhile (a halt, the pool's end)
            why = "the pool was dumped or dropped before the buy (%s)" % x["sell_due"]["why"] if x.get("sell_due") else self.blocked(exclude=x["pair"])
            if not why and (x["q"] <= 0 or x["min_out"] <= 0):
                why = "a zero stake or zero minOut"
            if not why and x["q"] > self.MAX_STAKE:
                why = f"the stake {x['q'] / 1e18:.6f} BNB is over BNB_MAX_STAKE_BNB {self.MAX_STAKE / 1e18:g}"
            if not why and x["q"] * self.E.bnb_usd() / 1e18 > 1.5 * self.E.STAKE_USD:
                why = f"the stake ${x['q'] * self.E.bnb_usd() / 1e18:.2f} is over 1.5 x BNB_STAKE_USD {self.E.STAKE_USD:g}"
            late, head = self.late(x)
            if not why and late > self.BUY_LATE:                                        # already late: no read is spent on it
                why = f"the buy would go {late} blocks late (it lands at L+{self.E.BUY_AT + late} at the earliest, the head at {head}; BNB_BUY_LATE {self.BUY_LATE})"
            if why:
                self.drop(x["pair"], "held", why); self.save(); return
            x["state"] = "buying"                                                       # from here no hook drops it; a sale due is kept
        try:
            self.buy_send(x)
        except Exception as e:                                                          # never left in 'buying': a buy record decides
            self.alarm(f"the buy failed: {type(e).__name__}: {self.scrub(e)}", pair=x["pair"], trace=self.scrub(traceback.format_exc(), 400))
            self.unbuying(x, f"{type(e).__name__}: {self.scrub(e, 80)}")

    def buy_send(self, x):
        gp = self.gas_price(fast=True)                                                  # the buy's own reads: one try of 3 s each
        need = x["q"] + sum(self.GAS.values()) * gp; err = None
        try:
            bal = self.read_balance(fast=True)
        except Exception as e:
            err = self.scrub(e, 80)
            bal = self.balance if self.balance is not None and time.monotonic() - self.balance_ok_at < 60 else None   # read within the minute
        try:
            fresh = self.reserves(x["pair"], x["side"], fast=True)
        except Exception:
            fresh = None                                                                # the engine's bound alone
        if bal is None or bal < need:
            with self.lock:
                self.traded.discard(x["pair"]); self.drop(x["pair"], "held", f"the wallet's balance {'was not read (' + err + ')' if bal is None else '%.6f BNB is under the stake and the gas (%.6f)' % (bal / 1e18, need / 1e18)}")
            if bal is not None:
                self.alarm(f"the BNB wallet has {bal / 1e18:.6f} BNB, under one trade's stake and gas ({need / 1e18:.6f}): no live buy until it is funded", quiet_key="funds", every_s=3600)
            self.save(); return
        min_out, why = x["min_out"], None
        if fresh is not None:                                                           # the pool now, as the buy will meet it
            rq, rt = fresh; tok_f = self.E.amount_out(x["q"], rq, rt)
            if x.get("r_wbnb") and rq <= (1 - self.E.DUMP_SHARE) * x["r_wbnb"]:
                why = f"the pool lost its WBNB before the buy ({x['r_wbnb']} at +{self.E.BUY_AT}, {rq} now)"
            elif tok_f < min_out:
                why = f"the price moved past BNB_SLIP before the buy ({tok_f} tokens for the stake now, minOut {min_out}): it would revert"
            else:
                min_out = max(min_out, bound(tok_f, x.get("f_buy", x["factor_ppm"]), self.SLIP_PPM))
        if not why and x.get("sell_due"):                                               # a dump or the pool's end seen by the reader during the reads
            why = "the pool was dumped or dropped before the buy (%s)" % x["sell_due"]["why"]
        if not why:                                                                     # a halt (another pool's) or the daily stop during the reads
            with self.lock:
                why = self.blocked(exclude=x["pair"])
        if not why:                                                                     # measured on the chain, after the reads, just before the send:
            late, head = self.late(x, self.head_now())                                  # the head read now, never one the reads left seconds old
            if late > self.BUY_LATE:
                why = f"the buy would go {late} blocks late (it lands at L+{self.E.BUY_AT + late} at the earliest, the head at {head}; BNB_BUY_LATE {self.BUY_LATE})"
        if why:
            with self.lock:
                self.traded.discard(x["pair"]); self.drop(x["pair"], "held", why)
            self.save(); return
        x["min_out"] = min_out
        dl = int(time.time()) + self.DEADLINE_S
        rec = self.send_tx(x, "buy", self.E.ROUTER, x["q"], buy_data(min_out, x["token"], self.wallet, dl, self.E.WBNB), self.GAS["buy"], gp,
                           {"min_out": min_out, "deadline": dl})
        with self.lock:
            if rec is None:
                self.drop(x["pair"], "unsent", "the buy was not sent")
            else:
                x["state"] = "buy_sent"; self.traded.add(x["pair"])
        self.save()

    def approve(self, x):
        if x["token"] in self.approved:
            x["state"] = "approved"; self.save(); return
        rec = self.send_tx(x, "approve", x["token"], 0, approve_data(self.E.ROUTER), x.get("gas_approve") or self.GAS["approve"], self.gas_price(), {})
        if rec is not None:
            x["state"] = "approve_sent"
        else:
            x["sell_wait"] = time.time() + 2
        self.save()

    def sell(self, x):
        due = x["sell_due"]; tries = x["sell_tries"]
        try:
            bal = self.token_balance(x["token"])
        except Exception:
            if not x.get("tokens"):
                x["sell_wait"] = time.time() + 1; return                                # not read: tried again, never taken for none
            bal = x["tokens"]
        if bal <= 0:
            if any(t["kind"] == "sell" and t.get("block") is None and not t.get("unseen") for t in x["txs"]):
                x["state"] = "sell_sent"; self.save(); return                           # a sale already on its way (a stop right after its send): its receipt decides
            x["zero_reads"] = x.get("zero_reads", 0) + 1
            if x["zero_reads"] < ZERO_READS:                                            # one node behind the buy, or a balance that reads 0 a moment: asked again
                x["sell_wait"] = time.time() + 1; return
            with self.lock:
                x["state"] = "stuck"
            self.alarm(f"the wallet's balance of the token read 0 {x['zero_reads']} times, 1 s apart, at the sale (bought {x.get('tokens')}): kept as stuck, "
                       "not settled; look at the wallet on bscscan", pair=x["pair"], token=x["token"])
            self.halt(f"the wallet held none of the token it bought at the sale ({x['pair']})"); self.save(); return
        x["zero_reads"] = 0
        head = self.head()
        if tries == 0 and due.get("r_wbnb") and due.get("block") is not None and (head is None or head - self.E.LAG_BLOCKS - due["block"] <= 5):
            rq, rt = due["r_wbnb"], due["r_token"]                                      # the engine's reserves at the sale, read near the head
        else:                                                                           # a sale by the head, after a dump, the pool's end or a jump: the pool now
            try:
                rq, rt = self.reserves(x["pair"], x["side"])
            except Exception:
                x["sell_wait"] = time.time() + 1; return
        slip = min(900_000, self.SLIP_PPM * 2 ** tries)                                 # doubled on each sell after a revert
        expected = self.E.amount_out(bal, rt, rq); min_out = bound(expected, x.get("f_sell", x["factor_ppm"]), slip); dl = int(time.time()) + self.DEADLINE_S
        rec = self.send_tx(x, "sell", self.E.ROUTER, 0, sell_data(bal, min_out, x["token"], self.wallet, dl, self.E.WBNB), x.get("gas_sell") or self.GAS["sell"],
                           self.gas_price(), {"amount": bal, "min_out": min_out, "expected": expected, "slip": slip / PPM, "deadline": dl, "why": due["why"]})
        if rec is not None:
            x["state"] = "sell_sent"
        else:
            x["sell_wait"] = time.time() + 2
        self.save()

    def finalized(self):
        """the chain's finalized block (BNB Chain's fast finality: about 2 blocks behind the head), read at most every POLL_S; None when
        it cannot be read (a receipt is then acted on at once)"""
        now = time.monotonic()
        if now - self.fin_at >= self.POLL_S:
            self.fin_at = now
            try:
                self.fin = int(self.rpc("eth_getBlockByNumber", ["finalized", False], tries=1, timeout=3)["number"], 16)
            except Exception as e:
                self.fin = None
                self.alarm(f"the finalized block not read ({self.scrub(e, 80)}): receipts acted on at the tip", quiet_key="finalized", every_s=600)
        return self.fin

    def pending(self, x):
        """the position's transactions at its last one's nonce with no receipt yet: the last one and the ones it replaces"""
        n = x["txs"][-1]["nonce"]
        return [t for t in x["txs"] if t["nonce"] == n and t.get("block") is None and not t.get("unseen")]

    def poll(self, x):
        """the position's last transaction (with the ones it replaces at its nonce) while it has no receipt. What happened to it is decided
        by outcome() alone (the rule is written there) and acted on here: mined (mined()); its nonce mined with no receipt anywhere (unseen():
        the state of the endpoint whose count shows the nonce mined); never mined, or its nonce taken by another transaction of ours
        (unsent()). While it is held: a copy goes to every endpoint each BNB_REBROADCAST_S, whether a node knows it or not, while its
        deadline is REBROADCAST_BEFORE_S away or more (a copy mined at or past its deadline could only revert, 'EXPIRED', and a reverted buy
        halts the line); a buy not mined by the time the head makes it late (BNB_BUY_LATE) is never copied again and is cancelled at its
        nonce (a 0-value transfer to the wallet 1/8 dearer: it would land late, up to its deadline, about 133 blocks); one a pool holds
        unmined (BNB_RPC_URL's, or only BNB_READ_ALT_URL's) is replaced at its nonce (held()). A copy, a cancel or a replacement answered
        'nonce too low', or a cancel or a replacement refused, is a signal (signal()): nothing more is signed at that nonce"""
        rec = x["txs"][-1]; now = time.time()
        if now - rec.get("polled", 0) < self.POLL_S:
            return
        rec["polled"] = now
        group = self.pending(x) or [rec]
        v = self.outcome(x, group, rec, now)
        if v[0] == "mined":
            return self.mined(x, group, v[1], v[2])
        if v[0] == "state":
            return self.unseen(x, rec, now, v[1])
        if v[0] == "never":
            return self.unsent(x, rec, f"was never mined (no endpoint knows it; mined nonces {v[1]})", fill=True)
        if v[0] == "other":
            return self.unsent(x, rec, f"was not mined: its nonce {rec['nonce']} went to our {v[1]}")
        if v[0] == "wait":                                                              # mined, its block not final yet
            return
        where = v[1]                                                                    # held: None BNB_RPC_URL's pool holds it, a host only that one's, False none
        own_dl = rec.get("deadline")
        late = self.late(x)[0] if rec["kind"] == "buy" else 0                           # a buy mined now would land this late
        if late <= self.BUY_LATE and now - rec.get("copied_at", rec["sent_at"]) >= self.REBROADCAST_S and (own_dl is None or now < own_dl - self.REBROADCAST_BEFORE_S):
            rec["copied_at"] = now; rec["rebroadcast"] = rec.get("rebroadcast", 0) + 1; k, msg, via = self.broadcast(rec["raw"]); self.signal(rec, k, msg)
            self.log({"ev": "live_rebroadcast", "kind": rec["kind"], "pair": x["pair"], "hash": rec["hash"], "reply": k, "detail": msg, "via": via, "known": where is None})
        if late > self.BUY_LATE and not self.signalled(group) and not rec.get("no_cancel") and len(group) <= self.MAX_REPLACE \
                and now - rec.get("cancel_at", 0) >= self.REPLACE_S and not self.nonce_used(x, rec["nonce"]):    # (held or not: a pool no node shows may hold it)
            rec["cancel_at"] = now
            return self.replace(x, rec, f"not mined {late} blocks after L+{self.E.BUY_AT} (BNB_BUY_LATE {self.BUY_LATE})")
        if where is not False:
            self.held(x, rec, group, now - rec["sent_at"], now, where)

    def signalled(self, group):
        """a signal at this nonce (signal()): nothing more is signed at it"""
        return any(t.get("nonce_low") or t.get("refused") for t in group)

    def outcome(self, x, group, rec, now):
        """THE RULE: what happened to a transaction of ours with no receipt seen yet (rec, the last at its nonce, and the ones it replaces
        there: group) is decided here and nowhere else; poll() acts on the answer, unseen() and unsent() act only on what this returned.
          (a) MINED: a receipt of one of them from either read endpoint (BNB_RPC_URL, BNB_READ_ALT_URL), in a block final there.
          (b) ITS NONCE MINED, no receipt: the chain's state (the token's balance, the allowance) read from an endpoint whose count of the
              wallet's mined transactions shows that nonce mined (count > nonce), and from such an endpoint only: the one with the higher
              count, BNB_RPC_URL on a tie (a buy's tokens counted at any endpoint whose count shows it). Taken once it has waited twice
              BNB_RECEIPT_WAIT_S without a receipt (a receipt gives the true amounts), and, unless BNB_RPC_URL's pool holds it,
              EXPIRED_AFTER_S past the latest deadline at the nonce; while an endpoint cannot answer, only the safe half: a buy whose tokens
              such an endpoint shows is kept as bought, nothing else.
          (c) NEVER MINED, the one drop without (a) or (b): every endpoint answered with a count at or below the nonce, no pool holds it, no
              node answered 'nonce too low' at it, neither endpoint shows a buy's tokens, and the same waits passed (past the latest
              deadline at the nonce, a buy or a sell could land only to revert). Then it is dropped (unsent()).
        A send at the nonce answered 'nonce too low' (a copy, a replacement, a late cancel, a gap's fill), and a replacement or a late cancel
        refused, is a SIGNAL (signal()): it asks both endpoints for the receipt at once (BNB_RPC_URL at every poll, BNB_READ_ALT_URL from then
        on at most every ALT_EVERY_S) and stops anything more being signed at that nonce. It never raises a count, and it never lets a state
        decide that does not itself show the nonce mined.
        Anything else is HELD: alarms; nothing dropped, nothing sent again at a new nonce, nothing settled (a copy while its deadline allows;
        held()'s replacements while a pool holds it and no signal stopped them). So a 'nonce too low' that neither endpoint's count confirms
        is held until a receipt or a count shows the nonce mined.
        Returns ("mined", t, receipt), ("state", view) (b), ("never", count) (c), ("other", hash) (b, the nonce went to that transaction of
        ours), ("wait",) (mined, its block not final yet), or ("held", where): where None BNB_RPC_URL's pool holds it, a host only that
        endpoint's pool, False no pool shows it"""
        known = False
        for t in group[::-1]:                                                           # (a) BNB_RPC_URL's receipts, at every poll
            r, k = self.receipt(t["hash"])
            if r is not None:
                fin = self.finalized()
                return ("wait",) if fin is not None and int(r["blockNumber"], 16) > fin else ("mined", t, r)   # once final: a reorg can still undo it
            known = known or k
        age = now - rec["sent_at"]; n = rec["nonce"]
        dl = max((t["deadline"] for t in group if t.get("deadline")), default=None)    # the latest deadline at this nonce (a late buy's cancel has none)
        low = any(t.get("nonce_low") for t in group)
        due = age >= 2 * self.RECEIPT_WAIT_S and (known or dl is None or now >= dl + self.EXPIRED_AFTER_S)
        ask = bool(self.read_alt) and (due or self.signalled(group) or (not known and age >= self.REPLACE_S))
        if not (due or ask) or now - rec.get("alt_at", 0) < ALT_EVERY_S:
            return ("held", None if known else False)
        rec["alt_at"] = now
        got = err = None
        if ask:                                                                         # (a) BNB_READ_ALT_URL's receipt
            try:
                got = self.alt_receipt(group)
            except Exception as e:
                err = e
            if isinstance(got, tuple):
                return ("mined",) + got
            if got == "unfinal":
                if age > 2 * self.RECEIPT_WAIT_S:
                    self.alarm(f"the {rec['kind']} {rec['hash']} is mined at {self.E.host(self.read_alt)} in a block not final there (or its receipt is not "
                               f"served) {age:.0f} s after its send", quiet_key="unfinal-" + rec["hash"], every_s=300, pair=x["pair"])
                return ("wait",)
        where = None if known else self.E.host(self.read_alt) if got == "pending" else False
        if not due:
            return ("held", where)
        counts = [None, None]                                                           # the counts: BNB_RPC_URL's (or the second's for it), BNB_READ_ALT_URL's
        try:
            counts[0] = int(self.rpc("eth_getTransactionCount", [self.wallet, "latest"]), 16)
        except Exception as e:
            self.alarm(f"the {rec['kind']} {rec['hash']} has no receipt and the wallet's count was not read ({self.scrub(e, 80)}): held", quiet_key="count-" + rec["hash"],
                       every_s=300, pair=x["pair"])
            return ("held", where)
        if self.read_alt and err is None:
            try:
                counts[1] = int(self.alt_rpc("eth_getTransactionCount", [self.wallet, "latest"], 5), 16)
            except Exception as e:
                err = e
        shows = [i for i in (0, 1) if counts[i] is not None and counts[i] > n]         # the endpoints whose count shows the nonce mined

        def down(e):
            self.alarm(f"the {rec['kind']} {rec['hash']} has no receipt on {self.E.host(self.E.RPC_URL)} and "
                       + (f"{self.E.host(self.read_alt)} did not answer" if self.read_alt else "the chain's state was not read")
                       + f" ({self.scrub(e, 80)}): nothing is dropped or settled until it does", quiet_key="alt-" + rec["hash"], every_s=300, pair=x["pair"])
            return ("held", where)
        if where is not False and not shows:                                            # held unmined, its nonce not mined: waited for
            return down(err) if err is not None else ("held", where)
        buy = next((t for t in group if t["kind"] == "buy"), None)
        view = None
        if shows:
            other = self.mined_nonces.get(n)
            if err is None and other and other != rec["hash"]:
                return ("other", other)
            view, e = self.state_at(shows, counts, x["token"], rec["kind"] == "approve")
            err = err or e
        elif err is None:                                                               # every endpoint answered: none shows the nonce mined
            why = "a node answered 'nonce too low' at it" if low else None
            try:
                if why is None and self.known(rec["hash"]):
                    return ("held", None)                                               # BNB_RPC_URL's pool holds it now
                if why is None and buy is not None and self.token_balance(x["token"], both=True) > 0:
                    why = "the wallet holds the buy's tokens"                           # (it landed; a count that lags shows it soon)
            except Exception as e:
                err = e
            if err is None:
                if why is None:
                    return ("never", max(c for c in counts if c is not None))
                self.alarm(f"the {rec['kind']} {rec['hash']}: {why}, but no endpoint counts its nonce {n} mined (count {'/'.join(str(c) for c in counts if c is not None)}) "
                           "or shows its receipt: held (nothing dropped, sent again or settled) until one does", quiet_key="held-" + rec["hash"], every_s=300, pair=x["pair"])
                return ("held", where)
        if err is not None:                                                             # an endpoint did not answer: only the safe half
            if buy is not None and view is not None and view["any_bal"] > 0:
                return ("state", dict(view, bal=None, allowed=0))                       # a buy whose tokens an endpoint counting its nonce shows: kept
            return down(err)
        return ("state", view)

    def state_at(self, shows, counts, token, approve):
        """(view, error) for outcome() (b): the token's balance at each endpoint in shows (its count shows the nonce mined), and the
        allowance at the one with the higher count (BNB_RPC_URL on a tie): {bal, any_bal, allowed} of that one; error when one did not
        answer (the view then holds the balances read)"""
        best = max(shows, key=lambda i: counts[i])
        bals, allowed = {}, 0
        try:
            for i in shows:
                bals[i] = self.token_balance(token, alt=i == 1)
            if approve:
                allowed = self.allowance(token, alt=best == 1)
        except Exception as e:
            return {"bal": None, "any_bal": max(bals.values(), default=0), "allowed": 0}, e
        return {"bal": bals[best], "any_bal": max(bals.values()), "allowed": allowed}, None

    def signal(self, rec, k, msg, refused=False):
        """a send at rec's nonce answered (outcome()'s SIGNAL): 'nonce too low' (that nonce was mined somewhere: by one of ours, only this
        engine holds the key), or refused (a replacement or a late cancel not taken: 'nonce', 'rejected'). Nothing more is signed at that
        nonce and both endpoints are asked for its receipt at once; never a count, never a decision"""
        if k == "nonce" and "too low" in str(msg).lower():
            rec["nonce_low"] = True
        if refused and k in ("nonce", "rejected"):
            rec["refused"] = rec["no_replace"] = rec["no_cancel"] = True

    def held(self, x, rec, group, age, now, where=None):
        """a transaction a pool holds unmined (outcome()'s HELD: BNB_RPC_URL's; where: only BNB_READ_ALT_URL's): replaced at its nonce
        after BNB_REPLACE_S, its gas price raised 1/8, MAX_REPLACE times (an approve or a sell anew, a cancel, a buy once past its deadline
        by a 0-value transfer to the wallet), then once at BNB_MAX_GWEI with an alarm (a sale is not left pending for good; bounded: one
        more, at the cap); never after a signal at its nonce (signal()). An alarm while it is pending past twice BNB_RECEIPT_WAIT_S"""
        due = rec["kind"] in ("approve", "sell", "cancel") or (rec["kind"] == "buy" and rec.get("deadline") is not None and now >= rec["deadline"])
        if age >= self.REPLACE_S and due and not rec.get("no_replace") and not self.signalled(group):
            if len(group) <= self.MAX_REPLACE:
                return self.replace(x, rec)
            if not any(t.get("capped") for t in group):
                return self.replace(x, rec, cap=True)
        if age > 2 * self.RECEIPT_WAIT_S:
            low = any(t.get("nonce_low") for t in group)
            self.alarm(f"the {rec['kind']} has been pending {age:.0f} s" + (f" (held by {where} only)" if where else "")
                       + (": a node answered 'nonce too low' at its nonce, but no endpoint counts it mined or shows its receipt: held until one does" if low else ""),
                       quiet_key="pending", every_s=300, pair=x["pair"], hash=rec["hash"])

    def mined(self, x, group, t, r):
        """t mined (its receipt r, in a final block): the others at its nonce dropped, the receipt acted on"""
        with self.lock:
            for o in group:
                if o is not t:
                    x["txs"].remove(o)
                    self.log({"ev": "live_replaced", "kind": o["kind"], "pair": x["pair"], "hash": o["hash"], "nonce": o["nonce"], "by": t["hash"]})
        return self.on_receipt(x, t, r)

    def nonce_used(self, x, n):
        """another position's transaction of ours at nonce n, mined or not (an 'unknown' send reads the nonce again, and the next one may
        take it): a transfer at n would replace it or come too late, never fill a gap"""
        m = self.mined_nonces.get(n)
        if m is not None and m not in {t["hash"] for t in x.get("txs") or []}:
            return True
        return any(t["nonce"] == n for y in list(self.pos.values()) if y is not x for t in y.get("txs") or [])

    def later_out(self, n):
        """our transaction with the lowest nonce above n that has no receipt (it waits behind n), or None"""
        c = [t for y in list(self.pos.values()) for t in y.get("txs") or [] if t["nonce"] > n and t.get("block") is None and not t.get("unseen")]
        return min(c, key=lambda t: t["nonce"]) if c else None

    def replace(self, x, rec, why=None, cap=False):
        """the pending transaction signed anew at its nonce, the gas price raised by 1/8 (the node takes a replacement 10% dearer), up to
        BNB_MAX_GWEI (cap: at BNB_MAX_GWEI, once, with an alarm): an approve as it was, a sell on the pool now with a fresh deadline, a buy
        past its deadline or late (why), or a cancel, by a 0-value transfer to the wallet. One refused is a signal (signal(): nothing more is
        signed at that nonce, both endpoints asked at once)"""
        hi = int(round(self.MAX_GWEI * 1e9)); gp = hi if cap else min(hi, max(rec["gas_price"] * 9 // 8 + 1, self.gas_price()))
        if gp * 10 < rec["gas_price"] * 11:
            rec["no_replace"] = rec["no_cancel"] = True
            self.alarm(f"the {rec['kind']} {rec['hash']} is pending at {rec['gas_price'] / 1e9:g} gwei and cannot be replaced under BNB_MAX_GWEI {self.MAX_GWEI:g}", pair=x["pair"])
            return
        info = {"replaces": rec["hash"]}
        if rec["kind"] in ("buy", "cancel"):
            info["why"] = why or rec.get("why") or "still pending past its deadline"
        if rec["kind"] == "sell":
            try:
                rq, rt = self.reserves(x["pair"], x["side"])
            except Exception:
                return
            exp = self.E.amount_out(rec["amount"], rt, rq); slip = int(round(rec["slip"] * PPM)); mo = bound(exp, x.get("f_sell", x["factor_ppm"]), slip)
            dl = int(time.time()) + self.DEADLINE_S
            info.update(amount=rec["amount"], min_out=mo, expected=exp, slip=rec["slip"], deadline=dl, why=rec.get("why"))
        if cap:                                                                         # past MAX_REPLACE: once more, at the cap (bounded)
            rec["no_replace"] = True; info["capped"] = True
            self.alarm(f"the {rec['kind']} {rec['hash']} is still pending at its nonce {rec['nonce']} after {self.MAX_REPLACE} replacements "
                       f"({rec['gas_price'] / 1e9:g} gwei): signed anew once more at BNB_MAX_GWEI {self.MAX_GWEI:g} gwei", pair=x["pair"])
        if rec["kind"] == "sell":
            new = self.send_tx(x, "sell", self.E.ROUTER, 0, sell_data(rec["amount"], mo, x["token"], self.wallet, dl, self.E.WBNB), rec["gas"], gp, info, nonce=rec["nonce"])
        elif rec["kind"] == "approve":
            new = self.send_tx(x, "approve", x["token"], 0, approve_data(self.E.ROUTER), rec["gas"], gp, info, nonce=rec["nonce"])
        else:
            new = self.send_tx(x, "cancel", self.wallet, 0, "0x", 21000, gp, info, nonce=rec["nonce"])
        if new is None:
            self.signal(rec, *self.last_reply, refused=True)
        self.log({"ev": "live_replace", "kind": rec["kind"], "pair": x["pair"], "nonce": rec["nonce"], "old": rec["hash"], "new": new["hash"] if new else None,
                  "as": new["kind"] if new else None, "gwei": gp / 1e9, **({"why": why} if why else {})})

    def unsent(self, x, rec, what, fill=False):
        """a transaction outcome() found never mined (or its nonce taken by another of ours): dropped with the ones it replaced (a buy: the
        slot unsent; an approve or a sell: sent again at a fresh nonce, which fills its own). fill (its nonce never mined): a buy (or its
        cancel) whose nonce sits under a later transaction of ours with no receipt (the sequencer gave the next nonce on: that one waits
        behind the gap for good, and no new buy comes while the line is halted) has its nonce filled by a 0-value transfer to the wallet, as
        a buy past its deadline is cancelled: the slot is dropped once that is mined. A fill refused for its nonce drops nothing: 'nonce too
        low' is a signal (outcome(): held until an endpoint shows the nonce mined, never filled again), another refusal ('replacement
        transaction underpriced': a pool holds one at it) is tried again after BNB_REPLACE_S"""
        later = self.later_out(rec["nonce"]) if fill and rec["kind"] in ("buy", "cancel") and not self.nonce_used(x, rec["nonce"]) else None
        if later is not None:
            if time.time() - rec.get("fill_at", 0) < self.REPLACE_S:
                return
            rec["fill_at"] = time.time()
            gp = min(int(round(self.MAX_GWEI * 1e9)), max(rec["gas_price"] * 9 // 8 + 1, self.gas_price()))
            new = self.send_tx(x, "cancel", self.wallet, 0, "0x", 21000, gp, {"replaces": rec["hash"], "why": f"its nonce {rec['nonce']} filled: our {later['kind']} at "
                                                                                 f"nonce {later['nonce']} waited behind it"}, nonce=rec["nonce"])
            k, msg = self.last_reply
            self.log({"ev": "live_replace", "kind": rec["kind"], "pair": x["pair"], "nonce": rec["nonce"], "old": rec["hash"], "new": new["hash"] if new else None,
                      "as": "cancel" if new else None, "gwei": gp / 1e9, "why": "a nonce gap"})
            if new is not None:
                self.alarm(f"the {rec['kind']} {rec['hash']} {what}: its nonce {rec['nonce']} filled by a 0-value transfer to the wallet (our {later['kind']} "
                           f"{later['hash']} at nonce {later['nonce']} waited behind it)", pair=x["pair"])
                self.save(); return
            if k == "nonce" and "too high" not in str(msg).lower():
                self.signal(rec, k, msg)                                                # ('nonce too low': mined after all; outcome() holds it until an endpoint shows it)
                self.alarm(f"the {rec['kind']} {rec['hash']} {what}, but a transfer at its nonce {rec['nonce']} was refused ({msg}): the nonce is taken; not dropped",
                           quiet_key="fill-" + rec["hash"], every_s=300, pair=x["pair"])
                return
            what += f"; its nonce {rec['nonce']} could not be filled ({k}: {msg}): our {later['kind']} at nonce {later['nonce']} waits behind it"
        self.alarm(f"the {rec['kind']} {rec['hash']} {what}: dropped", pair=x["pair"])
        with self.lock:
            for t in self.pending(x):
                x["txs"].remove(t); self.hashes.discard(t["hash"])
            self.nonce = None
            if rec["kind"] in ("buy", "cancel"):
                self.traded.discard(x["pair"]); self.drop(x["pair"], "unsent", "the buy was never mined")
            else:
                x["state"] = "bought" if rec["kind"] == "approve" else "approved"
        self.save()

    def unseen(self, x, rec, now, view):
        """outcome() (b): the nonce mined but no endpoint shows a receipt (only this engine holds the key: most likely the transaction is
        ours, behind a lagging or partial backend). The state the endpoint whose count shows the nonce mined gives (view) decides: a buy
        whose token the wallet holds is kept as bought (BNB in its value, its gas the most it could cost), a sell whose token the wallet no
        longer holds is settled (BNB out its minOut, the lowest of the ones at that nonce: a floor; out of the gate's medians; no halt), an
        approve whose allowance is there is done; a sell whose tokens are still there is sent again; a buy whose token is not there is
        polled (an alarm every 5 min) until 10 waits past its deadline, then dropped and the line halted (a mined buy that left no tokens is
        most likely a revert the node hides); a cancel whose buy left no tokens is dropped. While an endpoint cannot answer, outcome() gives
        a view only for a buy whose tokens are shown (bal None): the first branch, kept"""
        kind, h = rec["kind"], rec["hash"]
        group = self.pending(x) or [rec]; cost = max(t["gas"] * t["gas_price"] for t in group)
        buy = next((t for t in group if t["kind"] == "buy"), None)
        dl = max((t["deadline"] for t in group if t.get("deadline")), default=None)
        bal, any_bal, allowed = view["bal"], view["any_bal"], view["allowed"]

        def took(t):
            """t taken as the one mined at that nonce; the ones it replaced (or that replaced it) dropped"""
            with self.lock:
                for o in group:
                    if o is not t:
                        x["txs"].remove(o)
                t.update(unseen=True, gas_wei=cost); x["gas_wei"] += cost; self.mined_nonces[t["nonce"]] = t["hash"]
        if kind in ("buy", "cancel") and any_bal > 0 and buy is not None:
            took(buy)
            with self.lock:
                x.update(tokens=any_bal, bnb_in=buy["value"], state="bought", unconfirmed="the buy's receipt was never shown: BNB in is its value, its gas the most it could cost")
            self.alarm(f"the buy {buy['hash']} is not shown by the node but its nonce was mined and the wallet holds {any_bal} of the token: kept as bought", pair=x["pair"])
        elif kind == "sell" and bal == 0:
            took(rec)
            x.update(bnb_out=min(t["min_out"] for t in group if t["kind"] == "sell"), bnb_out_floor=True, state="done",
                     unconfirmed="the sell's receipt was never shown: BNB out is its minOut (a floor)")
            self.alarm(f"the sell {h} is not shown by the node but its nonce was mined and the wallet holds none of the token: settled at its minOut "
                       "(a floor; look at the wallet on bscscan)", pair=x["pair"])
            self.settle(x, x["sell_due"]["why"]); return
        elif kind == "approve" and allowed >= max(bal, 1):
            took(rec)
            with self.lock:
                self.approved.add(x["token"]); x["state"] = "approved"
        elif kind in ("buy", "cancel") and now < (dl if dl is not None else rec["sent_at"]) + 10 * self.RECEIPT_WAIT_S:
            self.alarm(f"the {kind} {h}: its nonce was mined but the node shows neither it nor the buy's tokens: polled on", quiet_key="unseen-" + h, every_s=300, pair=x["pair"])
            return
        else:
            self.unsent(x, rec, "was not seen (its nonce was mined; the wallet " + ("holds none of the token)" if kind in ("buy", "cancel") else
                                                                                    "still holds the token)" if kind == "sell" else "has no allowance)"))
            if kind == "buy":
                self.halt(f"a buy whose nonce was mined shows neither itself nor its tokens {10 * self.RECEIPT_WAIT_S:.0f} s past its deadline: a revert the node "
                          f"hides? ({x['pair']}, {h})")
            return
        self.save()

    def on_receipt(self, x, rec, r):
        ok = int(r.get("status") or "0x0", 16) == 1; used = int(r.get("gasUsed") or "0x0", 16)
        gas = used * int(r.get("effectiveGasPrice") or hex(rec["gas_price"]), 16)
        rec.update(block=int(r["blockNumber"], 16), status=int(ok), gas_used=used, gas_wei=gas); x["gas_wei"] += gas; self.mined_nonces[rec["nonce"]] = rec["hash"]
        self.log({"ev": "live_receipt", "kind": rec["kind"], "pair": x["pair"], "hash": rec["hash"], "status": int(ok), "block": rec["block"], "off": rec["block"] - x["L"],
                  "gas_used": used, "gas_wei": gas})
        kind = rec["kind"]
        if kind == "cancel":                                                            # the buy (past its deadline, late or lost) replaced: nothing bought, the nonce freed
            with self.lock:
                self.pnl_today -= gas / 1e18 * self.E.bnb_usd(); self.traded.discard(x["pair"])
                self.drop(x["pair"], "unsent", f"the buy was cancelled: {rec.get('why') or 'still pending past its deadline'} (a 0-value transfer took its nonce)")
            self.save(); return
        if not ok:
            self.halt(f"a reverted {kind} ({x['pair']}, {rec['hash']})")
            if kind in ("approve", "sell") and used * 100 >= 97 * rec["gas"]:               # out of gas (a token that swaps its fees on a sell): twice the limit next
                x["gas_" + kind] = min(600_000, 2 * rec["gas"])
                self.alarm(f"the {kind} ran out of gas ({used} of {rec['gas']}): the next {kind} gets {x['gas_' + kind]}", pair=x["pair"])
            if kind == "buy":
                x["bnb_in"] = 0; x["state"] = "done"; self.settle(x, "the buy reverted", reverted="buy"); return
            if kind == "approve":
                x["approve_tries"] += 1; x["state"] = "bought" if x["approve_tries"] < 2 else "stuck"
            else:
                x["sell_tries"] += 1; x["state"] = "approved" if x["sell_tries"] < self.SELL_TRIES else "stuck"
            if x["state"] == "stuck":
                self.alarm(f"the {kind} reverted {x[kind + '_tries']} times: the tokens stay in the wallet; a restart of flip-bnb tries to sell them again", pair=x["pair"])
            self.save(); return
        if kind == "buy":
            x["tokens"] = transfers(r, x["token"], to=self.wallet); x["bnb_in"] = transfers(r, self.E.WBNB, frm=self.E.ROUTER, to=x["pair"])
            try:                                                                        # a token whose Transfer event is not the standard one: its balance
                x["tokens"] = max(x["tokens"], self.token_balance(x["token"]))
            except Exception:
                pass
            if x["bnb_in"] != rec["value"]:
                self.alarm(f"the buy's WBNB into the pair ({x['bnb_in']}) is not its value ({rec['value']})", pair=x["pair"])
            x["state"] = "bought"
            if x["tokens"] <= 0:
                x["bnb_out"] = 0; self.settle(x, "the buy delivered no tokens"); self.halt(f"a buy that delivered no tokens ({x['pair']})"); return
        elif kind == "approve":
            self.approved.add(x["token"]); x["state"] = "approved"
        else:
            x["bnb_out"] = transfers(r, self.E.WBNB, frm=x["pair"], to=self.E.ROUTER); x["state"] = "done"
            self.settle(x, x["sell_due"]["why"]); return
        self.save()

    def settle(self, x, why, reverted=None):
        """the trade from the receipts: BNB in and out, the gas of every transaction, P&L in BNB, $ and %, beside the dry price. Once: the
        position leaves the positions file, the gate and the day take the trade (a halt it makes is written) and the trade_done line is
        saved there as not yet logged, all before the line is written; a hard kill after the line then never settles the trade again (the
        start finds the line in the log), and one before it writes the line at the start"""
        bnb_in, bnb_out, gas = x.get("bnb_in") or 0, x.get("bnb_out") or 0, x["gas_wei"]; usd = self.E.bnb_usd()
        pnl = bnb_out - bnb_in - gas; due = x.get("sell_due") or {}
        by = lambda k: [t for t in x["txs"] if t["kind"] == k]
        line = {"ev": "trade_done", "live": True, "dry": False, "role": "live", "pair": x["pair"], "token": x["token"], "L": x["L"], "pool_bnb": x["pool_bnb"],
                "why": why, "reverted": reverted, "stake_wei": x.get("q"), "bnb_in_wei": bnb_in, "tokens": x.get("tokens"), "bnb_out_wei": bnb_out, "gas_wei": gas,
                "gas_used": {k: [t.get("gas_used") for t in by(k)] for k in ("buy", "approve", "sell")},
                "buy_off": next((t["block"] - x["L"] for t in by("buy") if t.get("block")), None), "sell_off": next((t["block"] - x["L"] for t in by("sell")[::-1] if t.get("block")), None),
                "hashes": {k: [t["hash"] for t in by(k)] for k in ("buy", "approve", "sell")}, "pnl_bnb": round(pnl / 1e18, 9), "pnl_usd": round(pnl / 1e18 * usd, 4),
                "pnl_pct": round(pnl / bnb_in, 6) if bnb_in else None, "gross_pct": round((bnb_out - bnb_in) / bnb_in, 6) if bnb_in else None, "bnb_usd": round(usd, 4),
                "dry_ret": due.get("dry_ret"), "dry_ret_gross": due.get("dry_ret_gross"), "dry_back_wei": due.get("dry_back_wei"), "check": x.get("check"),
                "sell_tries": x["sell_tries"], "resumed": bool(x.get("resumed")), "unconfirmed": x.get("unconfirmed")}
        median_halt, n = None, self.E.GATE_PROBES
        with self.lock:
            self.pos.pop(x["pair"], None); self.roll_day(); self.pnl_today += line["pnl_usd"]
            if not reverted and bnb_in and not x.get("bnb_out_floor"):                  # (a sale settled at its minOut floor is in the day's $, not the medians)
                if len(self.gate_rets) < n:
                    self.gate_rets.append(line["pnl_pct"])
                    if len(self.gate_rets) == n and statistics.median(self.gate_rets) < 0:
                        median_halt = f"the median of the first {n} live trades is {statistics.median(self.gate_rets):+.2%}"
                self.recent = (self.recent + [line["pnl_pct"]])[-n:]                    # the gate goes on after the first 10: any 10 in a row, 3 deep losses in a row
                if not median_halt and len(self.recent) == n and statistics.median(self.recent) < 0:
                    median_halt = f"the median of the last {n} live trades is {statistics.median(self.recent):+.2%}"
                if not median_halt and len(self.recent) >= 3 and max(self.recent[-3:]) < -0.5:
                    median_halt = "3 live trades in a row under -50%% (%s)" % ", ".join("%+.1f%%" % (100 * r_) for r_ in self.recent[-3:])
            stop = self.pnl_today <= -self.DAILY_STOP and not self.stop_logged
            self.stop_logged = self.stop_logged or stop
            self.unlogged.append(line)
        if median_halt:
            self.halt(median_halt)
        self.save()                                                                     # settled on disk before its line (see above)
        self.log(line)
        with self.lock:
            self.unlogged = [u for u in self.unlogged if u is not line]
        if stop:
            self.alarm(f"the BNB daily stop: ${self.pnl_today:+.2f} today (BNB_DAILY_STOP_USD {self.DAILY_STOP:g}): no new live buy until 00:00 UTC")
        self.save()

    def logged(self, line):
        """whether a trade_done line saved as not yet logged is in the log after all (the last 2 MB: a stop right after its line)"""
        try:
            with open(self.E.LOG_PATH, "rb") as f:
                f.seek(0, 2); f.seek(max(0, f.tell() - 2_000_000)); tail = f.read().decode("utf-8", "replace")
        except OSError:
            return False
        for s in tail.splitlines():
            if '"trade_done"' in s:
                try:
                    e = json.loads(s)
                except ValueError:
                    continue
                if e.get("live") is True and e.get("pair") == line.get("pair") and e.get("L") == line.get("L") and e.get("hashes") == line.get("hashes"):
                    return True
        return False

    # ------------------------------------------------------------ the positions file: written on every change, read at the start
    def save(self):
        """the positions file, written whole (a temporary file, then a rename) by the worker (and at the start); the reader's thread marks"""
        with self.lock:
            self.saved_at = time.monotonic(); self.dirty = False
            if self.halted and not self.halt_written:                                   # a halt file that could not be written: tried again
                self.write_halt()
            d = {"saved_at": round(time.time(), 3), "wallet": self.wallet, "positions": self.pos, "pools": {k: v for k, v in self.snaps.items() if k in self.pos or k in self.traded},
                 "traded": sorted(self.traded), "gate_rets": self.gate_rets, "recent_rets": self.recent, "day": self.day, "pnl_today_usd": round(self.pnl_today, 6), "eligible": self.eligible,
                 "approved": sorted(self.approved), "halted": self.halted, "halt_written": self.halt_written, "unlogged": self.unlogged}
            tmp = self.POS_FILE + ".tmp"
            try:
                with open(tmp, "w") as f:
                    f.write(json.dumps(d, separators=(",", ":"))); f.flush(); os.fsync(f.fileno())
                os.replace(tmp, self.POS_FILE)
                fd = os.open(os.path.dirname(os.path.abspath(self.POS_FILE)), os.O_RDONLY)    # the rename itself on disk (a power loss must not bring the old file back)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except Exception as e:
                self.alarm(f"{self.POS_FILE} not written ({self.scrub(e, 80)}): a restart now would not find the open positions", quiet_key="posfile", every_s=60)

    def start(self, head, thread=True):
        """at the start (after the engine's checks): the halt file, the positions file, the wallet, the check's self-test; the worker"""
        if os.path.exists(self.HALT_FILE):
            self.halted = (open(self.HALT_FILE).read().strip() or "halted")[:300]
        if head:
            self.head_val, self.head_ok_at = head, time.monotonic()
        resumed = self.resume(head)
        try:
            self.read_balance(); self.read_nonce()
        except Exception as e:
            self.alarm(f"the wallet's balance or nonce not read at the start ({self.scrub(e, 80)})")
        self.off = self.self_test(); self.off_at = time.monotonic()
        if self.off:
            self.alarm(f"live is off until the self-test passes (it is run again every {self.SELFTEST_RETRY_S} s): {self.off}")
        if thread:
            self.thread = threading.Thread(target=self.run, name="live", daemon=True); self.thread.start()
        return {"live": True, "wallet": self.wallet, "send": [self.E.host(u) for u in self.send_urls], "slip": self.SLIP, "probe_every": self.PROBE_EVERY,
                "max_open": self.MAX_OPEN, "daily_stop_usd": self.DAILY_STOP, "gas_limits": self.GAS, "gwei": [self.MIN_GWEI, self.MAX_GWEI], "deadline_s": self.DEADLINE_S,
                "check_min": self.CHECK_MIN, "max_stake_bnb": self.MAX_STAKE / 1e18, "live_pool_bnb": self.LIVE_SIZES, "buy_late": self.BUY_LATE,
                "sell_late": self.SELL_LATE, "receipt_wait_s": self.RECEIPT_WAIT_S, "rebroadcast_s": self.REBROADCAST_S, "replace_s": self.REPLACE_S,
                "read_alt": self.E.host(self.read_alt) if self.read_alt else None, "token_codehashes": len(self.CODEHASHES), "halted": self.halted, "live_off": self.off, "resumed": resumed,
                "balance_bnb": self.balance / 1e18 if self.balance is not None else None, "nonce": self.nonce, "halt_file": self.HALT_FILE, "positions_file": self.POS_FILE}

    def self_test(self):
        """the pre-buy check's own test: a round trip of USDT by state override; None when it passes, else why"""
        try:
            stage, tokens, back, est = self.simulate(USDT, 10 ** 15)
            if stage != 0 or back < 0.9 * 10 ** 15:
                raise ValueError(f"stage {stage}, back {back}")
        except Exception as e:
            return f"the pre-buy check's self-test failed ({self.scrub(e, 120)}): does BNB_RPC_URL take eth_call state overrides?"
        return None

    def resume(self, head):
        """the positions file: every position that bought (or may have) is taken back with its pool; one past its sell block, or whose pool
        lost its WBNB while the engine was stopped, is sold at once"""
        try:
            d = json.load(open(self.POS_FILE))
        except FileNotFoundError:
            return 0
        except Exception as e:
            raise SystemExit(f"{self.POS_FILE} is not readable JSON ({type(e).__name__}): it may hold open positions; look at it, then move it away") from None
        if (d.get("wallet") or self.wallet) != self.wallet:
            raise SystemExit(f"{self.POS_FILE} is for the wallet {d.get('wallet')}, BNB_WALLET is {self.wallet}: move it away first")
        if d.get("halted") and not self.halted and d.get("halt_written") is False:     # a halt whose file was never written (not one the owner removed)
            self.halted = d["halted"]; self.halt_written = False
            self.alarm(f"the positions file holds a halt whose file was never written: it holds ({self.halted})")
        self.gate_rets = list(d.get("gate_rets") or []); self.approved = set(d.get("approved") or []); self.eligible = int(d.get("eligible") or 0)
        self.recent = list(d.get("recent_rets") or self.gate_rets)[-self.E.GATE_PROBES:]
        if d.get("day") == self.today():
            self.pnl_today = float(d.get("pnl_today_usd") or 0.0)
        for line in d.get("unlogged") or []:                                            # settled before a hard kill: its line written once
            seen = self.logged(line)
            self.log({"ev": "live_resume", "pair": line.get("pair"), "what": "its trade_done was " + ("in the log already" if seen else "not in the log: written now")})
            if not seen:
                self.log(dict(line, resumed_line=True))
        E, n = self.E, 0; lag_head = (head or 0) - E.LAG_BLOCKS
        self.traded = set(d.get("traded") or [])
        for pair, x in (d.get("positions") or {}).items():
            if x.get("state") == "buying":                                              # stopped while sending its buy: its record says whether one went
                x["state"] = "buy_sent" if x.get("txs") else "dropped"
            last = (x.get("txs") or [None])[-1]
            if x.get("state") in OPEN and last and last.get("block") is None and not last.get("unseen"):
                want = {"buy": "buy_sent", "cancel": "buy_sent", "approve": "approve_sent", "sell": "sell_sent"}[last["kind"]]
                if want != x["state"]:                                                  # stopped after a send, before its state was saved: its receipt decides
                    self.log({"ev": "live_resume", "pair": pair, "what": f"its last {last['kind']} has no receipt: {x['state']} taken as {want}"})
                    x["state"] = want
            if x.get("state") not in OPEN:
                self.log({"ev": "live_resume", "pair": pair, "state": x.get("state"), "what": "never bought: dropped"}); continue
            x["resumed"] = True; self.pos[pair] = x; self.traded.add(pair); self.roles[pair] = "live"; n += 1
            self.hashes |= {t["hash"] for t in x.get("txs") or []}
        for pair, snap in (d.get("pools") or {}).items():
            if pair not in self.traded or lag_head - snap["L"] >= E.WATCH_TO:
                continue
            snap["pend"] = None; snap["gaps"] = snap.get("gaps", 0) + 1                 # blocks were missed: its dry line is not clean
            x = self.pos.get(pair)
            if x is None and snap.get("fired"):
                snap["sold"] = True                                                     # settled: watched for the dump gate only
            elif x is not None and not snap.get("fired"):                               # a copy older than the buy: the engine must not buy again
                q, tok = x.get("q") or 0, x.get("exp_tokens") or 0
                snap.update(fired=True, sold=False, q=q, tok=tok, sq=snap["rq"] + q, st=max(0, snap["rt"] - tok))
            try:
                rq, rt = self.reserves(pair, snap["side"])
                if snap["rq"] > 0 and rq <= (1 - E.DUMP_SHARE) * snap["rq"] and snap.get("dump") is None:
                    off = lag_head - snap["L"]
                    self.log({"ev": "live_resume", "pair": pair, "what": f"its WBNB fell from {snap['rq']} to {rq} while the engine was stopped"
                              + (": sold at once" if x is not None else "")})
                    if x is not None:
                        x["sell_due"] = x.get("sell_due") or {"why": "the pool lost its WBNB while the engine was stopped", "r_wbnb": rq, "r_token": rt, "block": None, "at": time.time()}
                    if off < E.GATE_DUMP_BEFORE:
                        self.halt(f"a traded pool lost its WBNB before +{E.GATE_DUMP_BEFORE} while the engine was stopped ({pair})")
                snap["rq"], snap["rt"] = rq, rt
            except Exception as e:
                self.alarm(f"a resumed pool's reserves not read ({self.scrub(e, 80)})", pair=pair)
            E.pools[pair] = snap; self.snaps[pair] = snap
        for pair, x in self.pos.items():
            if x.get("sell_due") is None and (pair not in E.pools or lag_head - x["L"] >= E.SELL_AT):
                x["sell_due"] = {"why": "past its sell block at the start" if pair in E.pools else "resumed without its pool", "r_wbnb": None, "r_token": None, "block": None, "at": time.time()}
            if x["state"] == "stuck":
                x["state"] = "approved" if x["token"] in self.approved else "bought"; x["sell_tries"] = 0; x["approve_tries"] = 0; x["zero_reads"] = 0
            self.log({"ev": "live_resume", "pair": pair, "L": x["L"], "state": x["state"], "sell_due": (x.get("sell_due") or {}).get("why")})
        self.save()
        return n

    def flow_info(self):
        return {"live_open": len(self.pos), "halted": bool(self.halted), "pnl_today_usd": round(self.pnl_today, 4),
                "balance_bnb": round(self.balance / 1e18, 6) if self.balance is not None else None}
