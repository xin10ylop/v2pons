#!/usr/bin/env python3
"""bnb_live: the LIVE path of the BNB line, loaded by src/bnb_engine.py only when BNB_LIVE=1. With BNB_LIVE=0 (the default) this file is
never imported and the engine signs and sends nothing. research/session_oct12/bnb/REPORT_BNB.md section 5: a $5 probe of the rule (buy at
L+50, sell at L+260) on every BNB_PROBE_EVERY-th launch of a traded size, the others left dry as the control, and the gate as halts.

From the wallet straight through the PancakeSwap V2 router (no contract of ours on chain):
  - at the launch (about 50 blocks before the buy) the pool is armed when its slot is live, the line is not halted, the day is not
    stopped and fewer than BNB_MAX_OPEN positions are open; then the pre-buy check: an eth_call of contracts/BnbRoundTrip.sol, placed by
    state override at a fresh address, buys the stake through the router and sells it all back (the wallet's own calls) on the pool as
    it is; the pool is refused when a leg fails, when the sale returns under BNB_CHECK_MIN (90%) of the stake, or when a leg would need
    more gas than its limit;
  - at L+BNB_BUY_AT seen: swapExactETHForTokensSupportingFeeOnTransferTokens(minOut, [WBNB, token], wallet, now + BNB_DEADLINE_S), the
    value the engine's stake (BNB_STAKE_USD at the USDT/WBNB price), minOut the engine's tokens for it on the reserves it tracks (the
    PancakeSwap formula) x (1 - BNB_SLIP);
  - after the buy's receipt: approve(router, max) at the next nonce (once a token);
  - at L+BNB_SELL_AT seen, at once on a dump seen first, or when the pool stops being watched: swapExactTokensForETHSupportingFeeOnTransfer-
    Tokens(the wallet's whole balance of the token, the BNB expected on the tracked reserves x (1 - BNB_SLIP), [token, WBNB], wallet,
    deadline); a reverted sell is sent again on the reserves then with the slippage doubled, up to BNB_SELL_TRIES sells;
  - settled from the receipts: BNB in (the WBNB the router paid the pair), the tokens (the token's Transfers to the wallet), BNB out (the
    WBNB the pair paid the router), the gas of every transaction, the P&L in BNB, $ and % beside the dry price of the same trade: a
    trade_done line with live: true.
One worker thread signs and sends everything: the nonce comes from the RPC (pending) once, is kept in memory and is read again after any
nonce error. Gas: a fixed limit per call (BNB_GAS_BUY/APPROVE/SELL), the price eth_gasPrice kept between BNB_MIN_GWEI and BNB_MAX_GWEI.
The gate halts the line (HALTED.bnb beside the log): a dump before +997 on a traded pool, no crowd buy in +60..+260 on a traded pool, any
reverted buy, approve or sell, a negative median over the first 10 live trades. A halt stops new buys and still sells what is open.
BNB_DAILY_STOP_USD of losses stops new buys for the rest of the UTC day. Open positions and the pools they need are written to
bnb_positions.json beside the log on every change and taken back at the start (sold at once when past their sell block).

The key is read from BNB_KEY_FILE (mode 600, made by deploy/bnb_wallet.py) and is never printed, logged or written anywhere.
"""
import os, re, json, time, threading, queue, statistics, datetime, traceback, urllib.request, urllib.parse, urllib.error

SEL_BUY = "b6f9de95"                     # swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)
SEL_SELL = "791ac947"                    # swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
SEL_APPROVE = "095ea7b3"                 # approve(address,uint256)
SEL_BALANCE = "70a08231"                 # balanceOf(address)
SEL_RESERVES = "0902f1ac"                # getReserves()
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"     # Transfer(address,address,uint256)
MAX_UINT = 2 ** 256 - 1
HARNESS = "0x00000000000000000000000000000000b0b0b0b0"                              # where the check's code is placed (an empty account)
USDT = "0x55d398326f99059ff775485246999027b3197955"                                  # the start's self-test of the check: a round trip of USDT
ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts", "BnbRoundTrip.json")
OPEN = ("buying", "buy_sent", "bought", "approve_sent", "approved", "sell_sent", "stuck")   # a position holding (or buying) tokens: never dropped
w = lambda x: "%064x" % x
a = lambda s: "%064x" % int(s, 16)


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
        for u in self.send_urls:
            x = urllib.parse.urlparse(u)
            if x.scheme != "https" or not x.hostname:
                raise SystemExit(f"BNB_SEND_URL / BNB_SEND_ALT_URL must be https URLs (host {E.host(u)})")
        self.SLIP = s("BNB_SLIP", "0.05", 0.001, 0.5); self.SLIP_PPM = int(round(self.SLIP * 1e6))      # integer arithmetic for every bound
        self.PROBE_EVERY = s("BNB_PROBE_EVERY", "2", 1, 1000, True)
        self.MAX_OPEN = s("BNB_MAX_OPEN", "2", 1, 20, True)
        self.DAILY_STOP = s("BNB_DAILY_STOP_USD", "10", 0.1, 100000)
        self.GAS = {"buy": s("BNB_GAS_BUY", "200000", 21000, 3_000_000, True), "approve": s("BNB_GAS_APPROVE", "80000", 21000, 3_000_000, True),
                    "sell": s("BNB_GAS_SELL", "180000", 21000, 3_000_000, True)}
        self.MIN_GWEI = s("BNB_MIN_GWEI", "0.1", 0.01, 100); self.MAX_GWEI = s("BNB_MAX_GWEI", "1", self.MIN_GWEI, 100)
        self.DEADLINE_S = s("BNB_DEADLINE_S", "60", 5, 3600, True)
        self.CHECK_MIN = s("BNB_CHECK_MIN", "0.9", 0.5, 1.0)
        self.MAX_STAKE = int(s("BNB_MAX_STAKE_BNB", "0.05", 0.0001, 10) * 1e18)
        self.SELL_TRIES = s("BNB_SELL_TRIES", "3", 1, 10, True)
        self.RECEIPT_WAIT_S = s("BNB_RECEIPT_WAIT_S", "60", 5, 3600)
        self.BUY_LATE = s("BNB_BUY_LATE", "10", 0, 1000, True)                        # blocks past L+BUY_AT after which a buy is not sent
        logdir = os.path.dirname(os.path.abspath(E.LOG_PATH))
        self.HALT_FILE = env("BNB_HALT_FILE", os.path.join(logdir, "HALTED.bnb")); self.POS_FILE = env("BNB_POSITIONS_FILE", os.path.join(logdir, "bnb_positions.json"))
        art = json.load(open(ART)); self.CODE = art["deployedBytecode"]; self.SEL_RUN = art["selectors"]["run(address,address,address,uint256)"]
        self.load_key()
        self.lock = threading.RLock(); self.q = queue.Queue(); self.stop = False
        self.pos, self.snaps, self.roles, self.hashes, self.traded = {}, {}, {}, set(), set()
        self.gate_rets, self.approved, self.eligible = [], set(), 0
        self.day, self.pnl_today, self.stop_logged = self.today(), 0.0, False
        self.halted = None; self.off = None; self.nonce = None; self.balance = None; self.balance_at = 0.0; self.saved_at = 0.0
        self.POLL_S = 0.4                                                                # a transaction's receipt asked at most this often
        self.dirty = False; self.snapped_at = 0.0

    # ------------------------------------------------------------ the key: read once, checked against BNB_WALLET, never shown
    def load_key(self):
        try:
            st = os.stat(self.key_file)
        except OSError as e:
            raise SystemExit(f"BNB_KEY_FILE {self.key_file} cannot be read ({e.strerror}): deploy/bnb_wallet.py creates it") from None
        if st.st_mode & 0o077:
            raise SystemExit(f"{self.key_file} is open to other users (mode {oct(st.st_mode & 0o777)}): sudo chmod 600 {self.key_file}")
        try:
            from eth_account import Account
            from eth_utils import to_checksum_address
            with open(self.key_file) as f:
                acct = Account.from_key(f.read().strip())
        except Exception:
            raise SystemExit(f"{self.key_file} does not hold a usable key (its content is never printed), or eth_account is missing") from None
        if acct.address.lower() != self.wallet:
            raise SystemExit(f"the key in {self.key_file} is for {acct.address.lower()}, BNB_WALLET is {self.wallet}")
        self.acct = acct; self.checksum = to_checksum_address

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
        for u in self.send_urls:
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
            try:
                with open(self.HALT_FILE, "w") as f:
                    f.write(reason + "\n")
            except Exception as e:
                self.alarm(f"the halt file {self.HALT_FILE} could not be written ({self.scrub(e, 80)}): the halt holds in memory until a restart")
        self.alarm(f"the BNB line halted: {reason}; open positions are still sold; remove {self.HALT_FILE} and restart flip-bnb to resume" if first
                   else f"the BNB line (already halted) would halt again: {reason}", halt_file=self.HALT_FILE)
        self.mark()

    def drop(self, pair, role, why):
        """a position that never bought: the pool stays dry (its role says why)"""
        x = self.pos.pop(pair, None)
        self.roles[pair] = role
        self.log({"ev": "live_skip", "pair": pair, "L": x["L"] if x else None, "role": role, "why": why})

    # ------------------------------------------------------------ chain reads (the engine's RPC: tried again, never the key)
    def rpc(self, method, params, tries=3):
        return self.E.rpc(method, params, tries=tries)

    def gas_price(self):
        lo, hi = int(round(self.MIN_GWEI * 1e9)), int(round(self.MAX_GWEI * 1e9))
        try:
            gp = int(self.rpc("eth_gasPrice", []), 16)
        except Exception as e:
            self.alarm(f"eth_gasPrice not read ({self.scrub(e, 80)}): {self.MIN_GWEI:g} gwei", quiet_key="gasprice", every_s=300); gp = lo
        if gp > hi:
            self.alarm(f"the network asks {gp / 1e9:g} gwei, above BNB_MAX_GWEI {self.MAX_GWEI:g}: sent at the cap", quiet_key="gascap", every_s=300)
        return min(max(gp, lo), hi)

    def reserves(self, pair, side):
        r = self.E.words(self.rpc("eth_call", [{"to": pair, "data": "0x" + SEL_RESERVES}, "latest"]))
        return (r[0], r[1]) if side == 0 else (r[1], r[0])                           # (WBNB, token)

    def token_balance(self, token):
        return self.E.words(self.rpc("eth_call", [{"to": token, "data": "0x" + SEL_BALANCE + a(self.wallet)}, "latest"]))[0]

    def read_balance(self):
        self.balance = int(self.rpc("eth_getBalance", [self.wallet, "latest"]), 16); self.balance_at = time.monotonic()
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

    def broadcast(self, raw):
        """the same signed transaction to each send endpoint in turn until one takes it (one transaction has one hash: a second copy is
        harmless); a second round when no endpoint gave a definite answer. Otherwise the most telling answer: nonce, rejected, unknown"""
        got = []
        for _ in range(2):
            for u in self.send_urls:
                k, msg = self.post(u, raw)
                if k in ("ok", "in"):
                    return k, msg, self.E.host(u)
                got.append((k, msg, self.E.host(u)))
            if any(k != "unknown" for k, _, _ in got):
                break
        return next(g for want in ("nonce", "rejected", "unknown") for g in got if g[0] == want)

    def read_nonce(self):
        self.nonce = int(self.rpc("eth_getTransactionCount", [self.wallet, "pending"]), 16)
        self.log({"ev": "live_nonce", "nonce": self.nonce})
        return self.nonce

    def send_tx(self, x, kind, to, value, data, gas, gp, info):
        """sign with the sequencer's nonce and send; the record is written before the send (a restart finds it). Returns the record, or
        None when nothing went in. A nonce error reads the nonce again and signs anew (at most 3 times), unless this very transaction is
        already known (a copy that went in)."""
        for attempt in range(3):
            n = self.nonce if self.nonce is not None else self.read_nonce()
            raw, h = self.sign({"nonce": n, "gasPrice": gp, "gas": gas, "to": self.checksum(to), "value": value, "data": data, "chainId": self.E.CHAIN_ID})
            rec = {"kind": kind, "hash": h, "nonce": n, "gas": gas, "gas_price": gp, "value": value, "raw": raw, "sent_at": time.time(), "rebroadcast": 0, **info}
            with self.lock:
                x["txs"].append(rec); self.hashes.add(h)
            self.save()
            k, msg, via = self.broadcast(raw)
            if k == "nonce" and self.known(h):
                k = "in"
            self.log({"ev": "live_send", "kind": kind, "pair": x["pair"], "L": x["L"], "hash": h, "nonce": n, "gas": gas, "gwei": gp / 1e9, "value_wei": value,
                      **info, "reply": k, "detail": msg, "via": via, "attempt": attempt + 1})
            if k in ("ok", "in", "unknown"):                                       # unknown: perhaps in; its receipt (or its absence) decides
                self.nonce = n + 1 if k != "unknown" else None
                return rec
            with self.lock:
                x["txs"].remove(rec); self.hashes.discard(h)
            self.save()
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
        """a launch of a traded size: its slot (live or control); a live slot is armed and checked by the worker"""
        if p["skip"]:
            return
        with self.lock:
            self.eligible += 1; n = self.eligible
            role = "live" if (n - 1) % self.PROBE_EVERY == 0 else "control"
            why = self.blocked() if role == "live" else None
            role = "held" if why else role
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
            x.update(state="buy_due", q=p["q"], exp_tokens=p["tok"], min_out=bound(p["tok"], x["factor_ppm"], self.SLIP_PPM), r_wbnb=p["rq"], r_token=p["rt"], fire_block=B)
        self.mark()

    def on_sell(self, p, B, back):
        """the engine's sale at L+SELL_AT: the live position is sold; a traded pool with no crowd buy in +60..+260 halts the line"""
        q = p["q"]; dry = {"dry_ret": round((back - q - int(round(self.E.GAS_UNITS * self.E.GAS_GWEI * 1e9))) / q, 6), "dry_ret_gross": round((back - q) / q, 6), "dry_back_wei": back}
        self.sell_due(p, f"sell at +{self.E.SELL_AT}", dry, B)
        if p["pair"] in self.traded and p["crowd_gate"] == 0:
            self.halt(f"no crowd buy in +{self.E.GATE_CROWD_FROM}..+{self.E.SELL_AT} on a traded pool ({p['pair']}, {p['size']:g} BNB)")

    def on_dump(self, p, off):
        """a dump: an open position is sold at once; before +997 on a traded pool it halts the line"""
        self.sell_due(p, f"the dump at +{off}", {"dry_ret": -1.0, "dry_ret_gross": -1.0, "dry_back_wei": 0}, None)
        if p["pair"] in self.traded and off < self.E.GATE_DUMP_BEFORE:
            self.halt(f"a dump at +{off}, before +{self.E.GATE_DUMP_BEFORE}, on a traded pool ({p['pair']}, {p['size']:g} BNB)")

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
        with self.lock:
            pairs = list(self.pos)
        for pair in pairs:
            x = self.pos.get(pair)
            if x is None:
                continue
            st = x["state"]
            if st == "armed":
                self.check(x)
            elif st == "buy_due":
                self.buy(x)
            elif st in ("buy_sent", "approve_sent", "sell_sent"):
                self.poll(x)
            elif st == "bought" and time.time() >= x.get("sell_wait", 0):
                self.approve(x)
            elif st == "approved" and x.get("sell_due") and time.time() >= x.get("sell_wait", 0):
                self.sell(x)
        if self.dirty:
            self.save()

    def check(self, x):
        """the pre-buy check: the round trip of the stake simulated by eth_call on the pool as it is (the harness's code by state override)"""
        q = x["q_check"]; info = {"pair": x["pair"], "L": x["L"], "pool_bnb": x["pool_bnb"], "stake_wei": q}
        try:
            res = self.simulate(x["token"], q)
            rq, rt = self.reserves(x["pair"], x["side"])
        except Exception as e:
            self.log({"ev": "live_check", **info, "ok": False, "why": f"the check did not run ({self.scrub(e, 120)})"})
            with self.lock:
                self.drop(x["pair"], "refused", "the pre-buy check did not run")
            return
        stage, tokens, back, est = res
        tok_i = self.E.amount_out(q, rq, rt); back_i = self.E.amount_out(tok_i, rt - tok_i, rq + q)
        factor = min(PPM, back * PPM // back_i) if back_i > 0 else PPM              # the token's own cut beyond the pool's fees, ppm (1e6: none)
        why = ({1: "the simulated buy reverted", 2: "the simulated approve failed", 3: "the simulated sell reverted"}.get(stage)
               or (f"the simulated sale returns {back / q:.1%} of the stake, under BNB_CHECK_MIN {self.CHECK_MIN:.0%}" if back < self.CHECK_MIN * q else None)
               or next((f"the simulated {k} needs ~{est[k]} gas, over BNB_GAS_{k.upper()} {self.GAS[k]}" for k in ("buy", "approve", "sell") if est[k] > self.GAS[k]), None))
        self.log({"ev": "live_check", **info, "ok": why is None, "why": why, "stage": stage, "tokens": tokens, "back_wei": back, "back_ratio": round(back / q, 6),
                  "ideal_ratio": round(back_i / q, 6), "factor_ppm": factor, "gas_est": est})
        with self.lock:
            if x["pair"] not in self.pos or x["state"] != "armed":
                return
            if why:
                self.drop(x["pair"], "refused", why)
            else:
                x.update(state="checked", factor_ppm=factor, check={"ratio": round(back / q, 6), "factor_ppm": factor, "gas_est": est})
        self.save()

    def simulate(self, token, q):
        """(stage, tokens, BNB back, {leg: top-level gas estimate}) of BnbRoundTrip.run on the chain as it is; the harness's own gas per leg
        plus what a transaction of its own adds (measured Oct 12: buy -5.5k, approve +21.5k, sell +36k; added here: 0, 23k, 40k)"""
        data = "0x" + self.SEL_RUN + a(self.E.ROUTER) + a(self.E.WBNB) + a(token) + w(q)
        r = self.E.words(self.rpc("eth_call", [{"from": self.wallet, "to": HARNESS, "data": data, "gas": hex(3_000_000)}, "latest",
                                               {HARNESS: {"code": self.CODE, "balance": hex(q)}}]))
        if len(r) < 6:
            raise ValueError("a short answer")
        st = r[0]
        return st, r[1], r[2], {"buy": r[3] if st != 1 else 0, "approve": r[4] + 23_000 if st in (0, 3) else 0, "sell": r[5] + 40_000 if st == 0 else 0}

    def buy(self, x):
        with self.lock:
            if self.pos.get(x["pair"]) is not x or x["state"] != "buy_due":
                return                                                                  # dropped meanwhile (a halt, the pool's end)
            why = "the pool was dumped or dropped before the buy (%s)" % x["sell_due"]["why"] if x.get("sell_due") else self.blocked(exclude=x["pair"])
            done_to = self.E.state.get("done_to") or 0
            if not why and done_to - (x["L"] + self.E.BUY_AT) > self.BUY_LATE:
                why = f"the buy would go {done_to - x['L'] - self.E.BUY_AT} blocks late (BNB_BUY_LATE {self.BUY_LATE})"
            if not why and x["q"] > self.MAX_STAKE:
                why = f"the stake {x['q'] / 1e18:.6f} BNB is over BNB_MAX_STAKE_BNB {self.MAX_STAKE / 1e18:g}"
            if why:
                self.drop(x["pair"], "held", why); self.save(); return
            x["state"] = "buying"                                                       # from here no hook drops it; a sale due is kept
        gp = self.gas_price()
        need = x["q"] + sum(self.GAS.values()) * gp
        try:
            bal = self.read_balance()
        except Exception as e:
            bal = None; err = self.scrub(e, 80)
        if bal is None or bal < need:
            with self.lock:
                self.traded.discard(x["pair"]); self.drop(x["pair"], "held", f"the wallet's balance {'was not read (' + err + ')' if bal is None else '%.6f BNB is under the stake and the gas (%.6f)' % (bal / 1e18, need / 1e18)}")
            if bal is not None:
                self.alarm(f"the BNB wallet has {bal / 1e18:.6f} BNB, under one trade's stake and gas ({need / 1e18:.6f}): no live buy until it is funded", quiet_key="funds", every_s=3600)
            self.save(); return
        dl = int(time.time()) + self.DEADLINE_S
        rec = self.send_tx(x, "buy", self.E.ROUTER, x["q"], buy_data(x["min_out"], x["token"], self.wallet, dl, self.E.WBNB), self.GAS["buy"], gp,
                           {"min_out": x["min_out"], "deadline": dl})
        with self.lock:
            if rec is None:
                self.drop(x["pair"], "unsent", "the buy was not sent")
            else:
                x["state"] = "buy_sent"; self.traded.add(x["pair"])
        self.save()

    def approve(self, x):
        if x["token"] in self.approved:
            x["state"] = "approved"; self.save(); return
        rec = self.send_tx(x, "approve", x["token"], 0, approve_data(self.E.ROUTER), self.GAS["approve"], self.gas_price(), {})
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
            x["bnb_out"] = 0; self.settle(x, "the wallet holds none of the token at the sale")
            self.halt(f"the wallet held none of the token it bought at the sale ({x['pair']})"); return
        if tries == 0 and due.get("r_wbnb"):
            rq, rt = due["r_wbnb"], due["r_token"]                                      # the engine's reserves at the sale
        else:
            try:
                rq, rt = self.reserves(x["pair"], x["side"])
            except Exception:
                x["sell_wait"] = time.time() + 1; return
        slip = min(900_000, self.SLIP_PPM * 2 ** tries)                                 # doubled on each sell after a revert
        expected = self.E.amount_out(bal, rt, rq); min_out = bound(expected, x["factor_ppm"], slip); dl = int(time.time()) + self.DEADLINE_S
        rec = self.send_tx(x, "sell", self.E.ROUTER, 0, sell_data(bal, min_out, x["token"], self.wallet, dl, self.E.WBNB), self.GAS["sell"], self.gas_price(),
                           {"amount": bal, "min_out": min_out, "expected": expected, "slip": slip / PPM, "deadline": dl, "why": due["why"]})
        if rec is not None:
            x["state"] = "sell_sent"
        else:
            x["sell_wait"] = time.time() + 2
        self.save()

    def poll(self, x):
        """the receipt of the position's last transaction; a transaction the node does not know after BNB_RECEIPT_WAIT_S is sent again
        once, and after twice that, if its nonce went to no transaction of ours, it is dropped"""
        rec = x["txs"][-1]; now = time.time()
        if now - rec.get("polled", 0) < self.POLL_S:
            return
        rec["polled"] = now
        r, known = self.receipt(rec["hash"])
        if r is not None:
            return self.on_receipt(x, rec, r)
        age = now - rec["sent_at"]
        if known or age < self.RECEIPT_WAIT_S:
            if known and age > 2 * self.RECEIPT_WAIT_S:
                self.alarm(f"the {rec['kind']} has been pending {age:.0f} s", quiet_key="pending", every_s=300, pair=x["pair"], hash=rec["hash"])
            return
        if rec["rebroadcast"] == 0:
            rec["rebroadcast"] = 1; k, msg, via = self.broadcast(rec["raw"])
            self.log({"ev": "live_rebroadcast", "kind": rec["kind"], "pair": x["pair"], "hash": rec["hash"], "reply": k, "detail": msg, "via": via}); return
        if age < 2 * self.RECEIPT_WAIT_S:
            return
        try:
            mined = int(self.rpc("eth_getTransactionCount", [self.wallet, "latest"]), 16)
        except Exception:
            return
        if mined <= rec["nonce"] and self.known(rec["hash"]):
            return
        self.alarm(f"the {rec['kind']} {rec['hash']} was never mined (the node does not know it; mined nonces {mined}): dropped", pair=x["pair"])
        with self.lock:
            x["txs"].remove(rec); self.hashes.discard(rec["hash"]); self.nonce = None
            if rec["kind"] == "buy":
                self.traded.discard(x["pair"]); self.drop(x["pair"], "unsent", "the buy was never mined")
            else:
                x["state"] = "bought" if rec["kind"] == "approve" else "approved"
        self.save()

    def on_receipt(self, x, rec, r):
        ok = int(r.get("status") or "0x0", 16) == 1; used = int(r.get("gasUsed") or "0x0", 16)
        gas = used * int(r.get("effectiveGasPrice") or hex(rec["gas_price"]), 16)
        rec.update(block=int(r["blockNumber"], 16), status=int(ok), gas_used=used, gas_wei=gas); x["gas_wei"] += gas
        self.log({"ev": "live_receipt", "kind": rec["kind"], "pair": x["pair"], "hash": rec["hash"], "status": int(ok), "block": rec["block"], "off": rec["block"] - x["L"],
                  "gas_used": used, "gas_wei": gas})
        kind = rec["kind"]
        if not ok:
            self.halt(f"a reverted {kind} ({x['pair']}, {rec['hash']})")
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
        """the trade from the receipts: BNB in and out, the gas of every transaction, P&L in BNB, $ and %, beside the dry price"""
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
                "sell_tries": x["sell_tries"], "resumed": bool(x.get("resumed"))}
        self.log(line)
        median_halt = None
        with self.lock:
            self.pos.pop(x["pair"], None); self.roll_day(); self.pnl_today += line["pnl_usd"]
            if not reverted and bnb_in and len(self.gate_rets) < self.E.GATE_PROBES:
                self.gate_rets.append(line["pnl_pct"])
                if len(self.gate_rets) == self.E.GATE_PROBES and statistics.median(self.gate_rets) < 0:
                    median_halt = f"the median of the first {self.E.GATE_PROBES} live trades is {statistics.median(self.gate_rets):+.2%}"
            stop = self.pnl_today <= -self.DAILY_STOP and not self.stop_logged
            self.stop_logged = self.stop_logged or stop
        if median_halt:
            self.halt(median_halt)
        if stop:
            self.alarm(f"the BNB daily stop: ${self.pnl_today:+.2f} today (BNB_DAILY_STOP_USD {self.DAILY_STOP:g}): no new live buy until 00:00 UTC")
        self.save()

    # ------------------------------------------------------------ the positions file: written on every change, read at the start
    def save(self):
        """the positions file, written whole (a temporary file, then a rename) by the worker (and at the start); the reader's thread marks"""
        with self.lock:
            self.saved_at = time.monotonic(); self.dirty = False
            d = {"saved_at": round(time.time(), 3), "wallet": self.wallet, "positions": self.pos, "pools": {k: v for k, v in self.snaps.items() if k in self.pos or k in self.traded},
                 "traded": sorted(self.traded), "gate_rets": self.gate_rets, "day": self.day, "pnl_today_usd": round(self.pnl_today, 6), "eligible": self.eligible,
                 "approved": sorted(self.approved), "halted": self.halted}
            tmp = self.POS_FILE + ".tmp"
            try:
                with open(tmp, "w") as f:
                    f.write(json.dumps(d, separators=(",", ":"))); f.flush(); os.fsync(f.fileno())
                os.replace(tmp, self.POS_FILE)
            except Exception as e:
                self.alarm(f"{self.POS_FILE} not written ({self.scrub(e, 80)}): a restart now would not find the open positions", quiet_key="posfile", every_s=60)

    def start(self, head, thread=True):
        """at the start (after the engine's checks): the halt file, the positions file, the wallet, the check's self-test; the worker"""
        if os.path.exists(self.HALT_FILE):
            self.halted = (open(self.HALT_FILE).read().strip() or "halted")[:300]
        resumed = self.resume(head)
        try:
            self.read_balance(); self.read_nonce()
        except Exception as e:
            self.alarm(f"the wallet's balance or nonce not read at the start ({self.scrub(e, 80)})")
        try:
            stage, tokens, back, est = self.simulate(USDT, 10 ** 15)
            if stage != 0 or back < 0.9 * 10 ** 15:
                raise ValueError(f"stage {stage}, back {back}")
        except Exception as e:
            self.off = f"the pre-buy check's self-test failed ({self.scrub(e, 120)}): does BNB_RPC_URL take eth_call state overrides?"
            self.alarm(f"live is off for this run: {self.off}")
        if thread:
            threading.Thread(target=self.run, name="live", daemon=True).start()
        return {"live": True, "wallet": self.wallet, "send": [self.E.host(u) for u in self.send_urls], "slip": self.SLIP, "probe_every": self.PROBE_EVERY,
                "max_open": self.MAX_OPEN, "daily_stop_usd": self.DAILY_STOP, "gas_limits": self.GAS, "gwei": [self.MIN_GWEI, self.MAX_GWEI], "deadline_s": self.DEADLINE_S,
                "check_min": self.CHECK_MIN, "max_stake_bnb": self.MAX_STAKE / 1e18, "halted": self.halted, "live_off": self.off, "resumed": resumed,
                "balance_bnb": self.balance / 1e18 if self.balance is not None else None, "nonce": self.nonce, "halt_file": self.HALT_FILE, "positions_file": self.POS_FILE}

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
        self.gate_rets = list(d.get("gate_rets") or []); self.approved = set(d.get("approved") or []); self.eligible = int(d.get("eligible") or 0)
        if d.get("day") == self.today():
            self.pnl_today = float(d.get("pnl_today_usd") or 0.0)
        E, n = self.E, 0; lag_head = (head or 0) - E.LAG_BLOCKS
        self.traded = set(d.get("traded") or [])
        for pair, x in (d.get("positions") or {}).items():
            if x.get("state") == "buying":                                              # stopped while sending its buy: its record says whether one went
                x["state"] = "buy_sent" if x.get("txs") else "dropped"
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
                x["state"] = "approved" if x["token"] in self.approved else "bought"; x["sell_tries"] = 0; x["approve_tries"] = 0
            self.log({"ev": "live_resume", "pair": pair, "L": x["L"], "state": x["state"], "sell_due": (x.get("sell_due") or {}).get("why")})
        self.save()
        return n

    def flow_info(self):
        return {"live_open": len(self.pos), "halted": bool(self.halted), "pnl_today_usd": round(self.pnl_today, 4),
                "balance_bnb": round(self.balance / 1e18, 6) if self.balance is not None else None}
