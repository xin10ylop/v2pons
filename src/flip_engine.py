#!/usr/bin/env python3
"""flip_engine: the crowd-following flip on one operator's Uniswap v4 launches on Robinhood Chain (research report 24.54).

The operator (launcher contract LAUNCHERS) creates a pool paired with native ETH and, two to six seconds later, buys it with its
own wallets for minutes before its deployer removes the liquidity. Its deployer also removes the liquidity right after an outside
buy. The flip buys right after the operator's FIRST real-size buy and sells before that reaction.

What the eight live trades of Oct 8 showed (research/live_trades.py): on the seven through the relay the operator pulled 5-13
blocks after our buy (its other sub-1% launches that day ran 29 s to 17 min), and the result was decided by one thing only,
whether our sell landed before the pull: four did (+7.5%, +19.1%, +7.9%, -0.5%), three landed one block after it (-100% each).
The profit came from the operator's crowd buys already on their way when we bought (one, twice two, landing 1-3 blocks behind
ours); after those the crowd stops. So the sell goes as soon as the feed shows a buy behind ours that prices the sell at
TAKE_PROFIT or better, and in any case lands by our buy's block + HOLD_BLOCKS (4), before the fastest pull seen (+5). Repriced on
the chain, net of gas, the eight trades come out +7.2% (or -0.8%), +7.6%, +5.5%, +5.5%, +7.5%, -0.8%, -0.5%, +0.4%: no -100%. The
eighth (release 0.2's router route) was not pulled on, and lost 9.3% only because its sell went before the buy's receipt with
minOut as its amount. If a pull ever lands at or before our sell, the engine halts itself (HALT_FILE).
DRY_RUN=1 (default) does everything but sign and send; src/score.py prices every decision from the chain afterwards.

Reads the public sequencer feed (one message per ~100 ms block; sequenceNumber = block number), decodes every signed transaction,
and acts on two kinds: a call to a launcher (the pool's key and liquidity come from the launch receipt, fetched at once), and the
transactions carrying an armed token's address with ETH as their value (buys: every one moves the engine's copy of the pool price,
exact to 1e-15 against our fills; the first with value >= MIN_TRIGGER_ETH is the operator's first buy). Then the buy at the
reserved nonce, the sell on the first buy behind ours worth TAKE_PROFIT or when the feed shows our buy's block + HOLD_BLOCKS -
SELL_LEAD_BLOCKS (or by the wall-clock fallback), the receipts, the P&L, the pull's timing against our sell. One position at a time;
a daily cap and a daily stop.

The route to the pool is FlipRelay (contracts/FlipRelay.sol): it buys with its own ETH and sells everything it holds, straight
through the PoolManager, so the sell is signed with the buy and needs no amount. Release 0.2's Universal Router route (the crowd's
own calldata from the wallet, meant to hide our buy) was removed in 0.4: the exit, not the disguise, is what keeps the trade ahead
of the pull, and the router's two approvals and per-trade sell amount made the exit slower and cost trade 8 a tenth of its tokens.

ENTRY=auto (release 0.7) picks per launch: the operator's original launcher gets the follow entry, a per-launch copy of it the
seat. Overnight Oct 8-9 the operator went back to its original launcher and its original crowd (first buy 43-58 blocks in, then a
buy every few blocks); the seat bought those at + 7/8, forty blocks before the crowd, and sold at its deadline for -0.2% and -0.3%;
the follow entry priced at +2.4% a trade on the same 14 launches (13 of 14 positive).

ENTRY=seat (release 0.5) is the operator's scheme from Oct 8 14:59: a fresh launcher contract per launch (found by its call,
LAUNCH_SELECTORS=2fcb9108), and the crowd's first three buys bunched into one block 8-9 blocks after the launch, with almost
nothing after them, so there is no buy left to follow (the follow entry priced -0.5% on all 42 such launches). The seat buys at
launch + SEAT_FIRE_AT, landing one or two blocks ahead of that burst, and sells on it with the same take-profit, deadline and
halt: +8.9% a trade on paper (42 of 42), if the operator still sends its burst after seeing our buy. That is what a live test
answers; the dust tester that buys every launch at + 3-5 gets the burst every time, but it buys a speck.

Release 0.6 closes what an independent review of the engine found: a block holding a single transaction (a bare kind-4 message)
was invisible; a buy whose reply was lost was dropped though it may have gone in; a refused sell was never sent again; the
keepalive could hold the sell's connection; a launch found by its call alone was trusted without looking at the launcher's code
(now LAUNCHER_CODE_HASHES); the time fallback shared its thread with an RPC call.

Oct 10, after the handoff (research/session_oct9_10/front_audit): the two -100% front trades of 10:49 and 11:12 UTC were pools where the
volume bot's first buy was 0.00495 ETH, its smallest size and just under the 0.005 ETH sell-on threshold; the pull came 3 blocks after
that buy as in every other pool, and our sell waited for the 18-block deadline (sold on the bot's buy, each would have been -0.17%).
Since then the bot's buy is known by its router (FRONT_BOT_ROUTERS) at any size, and the size rule (FRONT_SELL_ON_ETH) is off by default:
the operator raised its decoys to each threshold within the hour (0.001485 at 15:04, 0.00495 at 15:45) and sold us out of 323 positions ahead
of its bot's buy for the cost of two fees each; its router is the signal it has not faked. Follow got its own
halt (FOLLOW_HALT_FILE) for a near miss: a pull within FOLLOW_NEAR_MISS_BLOCKS (4) of our buy even behind our sell stops follow, not front.

Settings come from the environment (/etc/flip/engine.env on the box). Log: JSONL, one event per line, LOG_PATH.
"""
import os, sys, json, math, time, base64, threading, asyncio, socket, ssl, signal, http.client, urllib.request, urllib.parse, datetime, traceback, collections, re
import rlp
from eth_utils import keccak, to_checksum_address
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math

RELEASE = "0.9"


def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


FEED_URL = env("FEED_URL", "wss://feed.mainnet.chain.robinhood.com"); FEED_COMPRESSION = env("FEED_COMPRESSION", "deflate") or None
FEED_USER_AGENT = env("FEED_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36")   # the RPC calls have sent a browser agent since 0.1; the feed gets one too (empty = the library's)


def parse_headers(text):
    """FEED_HEADERS: extra handshake headers for an authenticated feed (a provider's endpoint): a JSON object, or "Name: value; Name2: value2".
    The public feed blocked the box's address range on Oct 10, 2026 17:37 UTC for exceeding its limits and said that reaching it from any
    other address is unauthorized (docs/HANDOFF.md 16.11): a feed the engine may use is one whose operator has agreed to it, and such feeds
    carry a token in the URL (FEED_URL) or in a header (here). Never put a public feed back behind another address."""
    text = (text or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        d = json.loads(text)
        return {str(k): str(v) for k, v in d.items()}
    out = {}
    for part in text.split(";"):
        if ":" in part:
            k, v = part.split(":", 1); out[k.strip()] = v.strip()
    return out


FEED_HEADERS = parse_headers(env("FEED_HEADERS", ""))
SEQ_URL = env("SEQ_URL", "https://sequencer.mainnet.chain.robinhood.com"); RPC_URL = env("RPC_URL", "https://rpc.mainnet.chain.robinhood.com")
LOG_PATH = env("LOG_PATH", "flip_engine.jsonl"); DRY_RUN = env("DRY_RUN", "1") != "0"; CHAIN_ID = 4663
FOLLOW = env("FOLLOW", "1") != "0"                                                          # 0: the follow strategy (and the seat) is off: no follow launch is armed, front has the slot alone
LAUNCHERS = {a.strip().lower().replace("0x", "") for a in env("LAUNCHERS", "0x3194e32622c5d860a0572c74edda99dcfd8fc827").split(",") if a.strip()} if FOLLOW else set()
POOL_MANAGER = env("POOL_MANAGER", "0x8366a39cc670b4001a1121b8f6a443a643e40951").lower()
RELAY = env("RELAY", "").lower(); WALLET = env("WALLET", "").lower()
STAKE_ETH = float(env("STAKE_ETH", "0.0012")); STAKE_WEI = int(STAKE_ETH * 1e18); ETH_USD = float(env("ETH_USD", "2570"))
MIN_TRIGGER_ETH = float(env("MIN_TRIGGER_ETH", "0.0002")); MIN_TRIGGER_WEI = int(MIN_TRIGGER_ETH * 1e18)
FEE_MIN_PPM = int(env("FEE_MIN_PPM", "0")); FEE_MAX_PPM = int(env("FEE_MAX_PPM", "9999"))         # the sub-1% tier: the flip's edge is the operator's own flow minus two fees
MIN_LIQUIDITY = float(env("MIN_LIQUIDITY", "1e21")); TRIGGER_MAX_BLOCKS = int(env("TRIGGER_MAX_BLOCKS", "150"))
BUY_SLIP = float(env("BUY_SLIP", "0.03")); BUY_DEADLINE_S = int(env("BUY_DEADLINE_S", "3"))            # 3%: a crowd buy that lands ahead of ours makes our buy revert (behind it there is nothing left on its way)
HOLD_BLOCKS = int(env("HOLD_BLOCKS", "4")); SELL_LEAD_BLOCKS = int(env("SELL_LEAD_BLOCKS", "2")); SELL_FALLBACK_S = float(env("SELL_FALLBACK_S", "0.5"))   # the sell lands by our buy + 4; the fastest pull on us came at + 5
TAKE_PROFIT = float(env("TAKE_PROFIT", "0.01"))                                           # sell as soon as a buy behind ours prices the sell (after gas) at this return; 9 turns it off
BUY_DELAY_BLOCKS = int(env("BUY_DELAY_BLOCKS", "0"))                                      # fire this many blocks after the trigger (1: aim to land 2 after it, right ahead of the crowd's next buy)
LAUNCHER_CODE_HASHES = {x.strip().lower().replace("0x", "") for x in env("LAUNCHER_CODE_HASHES",
    "2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c,42544ef5d4754816b3cfe77f3a6fb1c8eb842d6eee101f7d15c638593a3351d2").split(",") if x.strip()}   # the operator's launcher code (6,984 bytes; from 14:59 every launcher is a copy)
LAUNCH_SELECTORS = {x.strip().lower().replace("0x", "") for x in env("LAUNCH_SELECTORS", "").split(",") if x.strip()} if FOLLOW else set()   # a launch known by its call (2fcb9108): from Oct 8 14:59 each launch has a fresh launcher
ENTRY = env("ENTRY", "follow").lower()                                                     # "follow": behind the operator's first real-size buy; "seat": SEAT_FIRE_AT blocks after the launch, ahead of its burst; "auto": per launch, by the launcher
SEAT_CODE_HASHES = {x.strip().lower().replace("0x", "") for x in env("SEAT_CODE_HASHES", "2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c").split(",") if x.strip()}   # auto: the per-launch launcher copies (the burst scheme) get the seat
SEAT_FIRE_AT = int(env("SEAT_FIRE_AT", "6"))                                               # seat: fire when the feed shows launch + 6, to land at + 7/8, one or two blocks ahead of the burst (+9 on 30 of 42 launches)
if ENTRY not in ("follow", "seat", "auto"):
    raise SystemExit(f"ENTRY is {ENTRY!r}: follow, seat or auto")
HALT_FILE = env("HALT_FILE", os.path.join(os.path.dirname(os.path.abspath(LOG_PATH)), "HALTED")); PULL_WATCH_S = float(env("PULL_WATCH_S", "3"))   # a pull at or before our sell writes HALT_FILE and stops live trading until it is removed
BUY_GAS = int(env("BUY_GAS", "350000")); SELL_GAS = int(env("SELL_GAS", "350000")); GAS_HEADROOM = float(env("GAS_HEADROOM", "3")); SELL_GAS_HEADROOM = float(env("SELL_GAS_HEADROOM", "6"))
MAX_TRADES_PER_DAY = int(env("MAX_TRADES_PER_DAY", "10")); DAILY_STOP_USD = float(env("DAILY_STOP_USD", "15"))
STOP_WAIT_S = float(env("STOP_WAIT_S", "40"))                                              # a stop (SIGTERM) waits this long at most for the open trade, under systemd's 90 s
STALE_S = float(env("STALE_S", "2.5")); RECEIPT_TIMEOUT_S = float(env("RECEIPT_TIMEOUT_S", "25"))
POSITION_MANAGER = env("POSITION_MANAGER", "0x58daec3116aae6d93017baaea7749052e8a04fa7").lower().replace("0x", "")
# the 'front' strategy: a volume bot's launches (PositionManager multicall, 1,444 bytes, exactly 2.4333285 ETH, fee 0.25%, about 330 a day) get a
# scheduled first buy of 0.05-0.25 ETH at launch + 7..13, quoted at the launch state; we buy in the launch's next block and sell into it.
# Armed from the launch transaction itself (the PoolKey, price and liquidity are in its calldata), so we fire in the launch block.
FRONT = env("FRONT", "0") != "0"; FRONT_DRY_RUN = env("FRONT_DRY_RUN", "1") != "0"
FRONT_VALUE_WEI = int(env("FRONT_VALUE_WEI", "2433328500000000000")); FRONT_CALLDATA_LEN = int(env("FRONT_CALLDATA_LEN", "1444"))
FRONT_STAKE_ETH = min(float(env("FRONT_STAKE_ETH", "0.0012")), 0.006); FRONT_STAKE_WEI = int(FRONT_STAKE_ETH * 1e18)   # the bot's first buy reverts once ~0.012 ETH sits ahead of it
FRONT_TAKE_PROFIT = float(env("FRONT_TAKE_PROFIT", "0.01")); FRONT_HOLD_BLOCKS = int(env("FRONT_HOLD_BLOCKS", "18"))       # the sell goes on the bot's buy, at the latest when the feed shows our buy + 18
# (the bot's first buy came by launch + 20 in 432 of 435 pools on Oct 9-10, by + 14 in only 420; no pool was pulled before the bot's buy)
FRONT_FIRE_MAX = int(env("FRONT_FIRE_MAX", "2")); FRONT_MAX_PER_DAY = int(env("FRONT_MAX_PER_DAY", "400"))                 # fire only while the feed is at the launch + 2 at most (land by + 4)
FRONT_HALT_FILE = env("FRONT_HALT_FILE", HALT_FILE + ".front")                                                         # a pull before our sell stops the front strategy only
# follow's own halt: the operator's pull landing within this many blocks of our buy, even behind our sell, means the margin before its reaction is
# gone (the exit survives a pull at our buy + 4 or later only: research/session_oct9_10/protect/exits_bt.out; Oct 9-10 live pulls came at + 5/+ 6,
# our sell at + 2/+ 3). Follow (and the seat) stop, front goes on. 0 turns it off.
FOLLOW_NEAR_MISS_BLOCKS = int(env("FOLLOW_NEAR_MISS_BLOCKS", "4")); FOLLOW_HALT_FILE = env("FOLLOW_HALT_FILE", HALT_FILE + ".follow")
FRONT_DAILY_STOP_USD = float(env("FRONT_DAILY_STOP_USD", "5"))                                                          # its own stop: front's results never stop follow, nor follow's front
# what identifies the bot's launches is the value and the calldata above (its other families send 3, 5, 9.33 or 40 ETH at a 1% fee; 5 ETH is
# a trap). Beyond that, every launch seen so far carried this fee, tick spacing, launch price and liquidity: the engine logs a launch that
# differs ("fingerprint": "new: ...") and trades it anyway, unless FRONT_PIN=1 (then it is not traded). For a fixed 2.4333 ETH the price and
# liquidity follow from the token amount the bot puts in; a copycat would copy them too, so the pin buys little and would stop the strategy
# if the bot changed its token. Senders are fresh wallets (532 of 532 distinct) minting to themselves: no address to allowlist.
FRONT_PIN = env("FRONT_PIN", "0") != "0"
FRONT_FEE = int(env("FRONT_FEE", "2500")); FRONT_TICK_SPACING = int(env("FRONT_TICK_SPACING", "50"))
FRONT_SQRT_P = int(env("FRONT_SQRT_P", "1604517591721945638372359205383840")); FRONT_LIQ = int(env("FRONT_LIQ", "49279426163460954002188"))
# the bot's first buy (0.05-0.25 ETH) is quoted at the launch state with minOut 99% of that quote: about 0.012 ETH bought ahead of it makes it revert
FRONT_BOT_MIN_ETH = float(env("FRONT_BOT_MIN_ETH", "0.04")); FRONT_BOT_MIN_WEI = int(FRONT_BOT_MIN_ETH * 1e18); FRONT_BOT_MINOUT = float(env("FRONT_BOT_MINOUT", "0.99"))
FRONT_AHEAD_MAX_ETH = float(env("FRONT_AHEAD_MAX_ETH", "0.008")); FRONT_AHEAD_MAX_WEI = int(FRONT_AHEAD_MAX_ETH * 1e18)   # others' buys before ours plus our stake: at most this, a third of the room left for buys behind ours
# the bot's buy is the whole profit and nothing comes after it but the pull (2-4 blocks after it, 400 of 400 live trades on Oct 10): it sells our
# position at once even below FRONT_TAKE_PROFIT, whatever its size. It is known by its router (FRONT_BOT_ROUTERS: its buys are calls to it carrying
# the token) and, if a size rule is wanted, by its size (FRONT_SELL_ON_ETH; 0 = off, the default). The size rule is the one the operator games:
# on Oct 10 its decoys behind our buy went from 0.00012 ETH to 0.001485 (15:04 UTC) to 0.00495 (about 15:45), its bot's smallest size, each
# step just above the threshold then in force, and every decoy sold our position ahead of the bot's buy for about -0.3% instead of +14% (34
# trades at 0.001, 289 at 0.004); the decoys cost it nothing, it owns the pools. The two -100% trades of Oct 10 (10:49 and 11:12 UTC) were bot
# buys of 0.00495 ETH under the then 0.005 threshold (research/session_oct9_10/front_audit). What is left: its router, the take-profit, the deadline.
FRONT_SELL_ON_ETH = max(0.0, float(env("FRONT_SELL_ON_ETH", "0"))); FRONT_SELL_ON_WEI = int(FRONT_SELL_ON_ETH * 1e18)
FRONT_BOT_ROUTERS = {a.strip().lower().replace("0x", "") for a in env("FRONT_BOT_ROUTERS", "0x1cbaf24d53fe930fce8eff149fa797d2611da149").split(",") if a.strip()}
# the bot runs several launch lines at once (2.4333 ETH at fee 0.25%; 3.0 and 5.0 ETH at fee 1%, Oct 10-11: about 440 and 220 a day, minOut 0.95 of
# the launch quote, so about 0.08 ETH of room ahead of its buy). Front trades every family listed here, told apart by the launch value: the FRONT_*
# settings above make the first; FRONT_FAMILIES (JSON: a list of {name, value_wei, fee, tick_spacing, sqrt_p, liq, bot_minout, ahead_max_eth,
# take_profit, hold_blocks, stake_eth}; a field left out takes the FRONT_* value; big numbers may be strings) adds the others. A family's fee is
# front's own fee bound (FEE_MIN/MAX_PPM are follow's): a launch at another fee is not traded, and the pin (FRONT_PIN) compares the rest.
MIN_SQRT_P = 4295128739; MAX_SQRT_P = 1461446703485210103287273052203988822378723970342                                # v4's price bounds
FRONT_FAMILY_KEYS = ("name", "value_wei", "fee", "tick_spacing", "sqrt_p", "liq", "bot_minout", "ahead_max_eth", "take_profit", "hold_blocks", "stake_eth", "dry_run", "pin",
                     "fire_at", "fire_max")
# fire_at: fire when the feed shows launch + fire_at (0: the launch block itself, landing at + 1/+ 2, for a line whose bot buys at + 6..+ 13);
# a line whose bot buys later, with the operator's trap pulls in the first blocks (the 3.0 line on Oct 11: bot at + 18..+ 58, pulls at + 7..+ 9),
# is entered after that window and before the bot: fire_at 12-16, hold_blocks past the bot's latest offset. fire_max: how many blocks after
# fire_at the fire may still go (the feed's lag); FRONT_FIRE_MAX for the base family.
FRONT_STAKE_CAP_WEI = int(0.006e18)


def _num(v, what, lo, hi, integer=False):
    """a number from the JSON within [lo, hi]: no booleans, no NaN or infinity, an integer where one is wanted (1.9 is not 1)"""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        raise SystemExit(f"{what} must be a number, not {v!r}")
    if integer and float(v) != int(v):
        raise SystemExit(f"{what} must be a whole number, not {v!r}")
    if not lo <= v <= hi:
        raise SystemExit(f"{what} {v!r} is not in {lo}..{hi}")
    return int(v) if integer else float(v)


def _flag(v, what):
    if not isinstance(v, bool):
        raise SystemExit(f"{what} must be true or false, not {v!r}")
    return v


def _eth_wei(v, what, lo, hi):
    """ETH as the JSON gives it (0.002, "0.07") to wei, to the nanoether (the float's last digits never reach the amount), within [lo, hi] ETH"""
    try:
        x = float(v) if isinstance(v, str) and v.strip() else v
    except ValueError:
        raise SystemExit(f"{what} must be an amount in ETH, not {v!r}")
    return int(round(_num(x, what, lo, hi) * 1e9)) * 10 ** 9


def _wei(v, what, lo=1, hi=None):
    """a wei amount from the JSON: an int or a string of digits (never a float, which loses digits), at least lo"""
    if isinstance(v, bool) or not (isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit())):
        raise SystemExit(f"{what} must be an integer or a string of digits, not {v!r}")
    v = int(v)
    if v < lo or (hi is not None and v > hi):
        raise SystemExit(f"{what} {v} is out of range")
    return v


def _no_dup_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise SystemExit(f"FRONT_FAMILIES: the key {k!r} is given twice in one family")
        d[k] = v
    return d


def front_family_check(fam):
    """the bounds every family must meet (the FRONT_* one too): a fee in v4's range, a stake above 0 and at most the cap, a minOut in (0, 1],
    a take-profit in (0, 9], a hold of 1..600 blocks, a room of at least the stake, a price in v4's range, liquidity above 0, a fire window
    inside the trigger window"""
    n = fam["name"]
    if not 1 <= fam["fee"] <= 999999:
        raise SystemExit(f"front family {n}: fee {fam['fee']} is not in 1..999999 ppm")
    if not 1 <= fam["tick_spacing"] <= 32767:
        raise SystemExit(f"front family {n}: tick_spacing {fam['tick_spacing']} is not in 1..32767")
    if not 0 < fam["stake_wei"] <= FRONT_STAKE_CAP_WEI:
        raise SystemExit(f"front family {n}: the stake {fam['stake_wei'] / 1e18:g} ETH is not in (0, {FRONT_STAKE_CAP_WEI / 1e18:g}]")
    if not 0 < fam["bot_minout"] <= 1:
        raise SystemExit(f"front family {n}: bot_minout {fam['bot_minout']} is not in (0, 1]")
    if not 0 < fam["take_profit"] <= 9:
        raise SystemExit(f"front family {n}: take_profit {fam['take_profit']} is not in (0, 9]")
    if not 1 <= fam["hold_blocks"] <= 600:
        raise SystemExit(f"front family {n}: hold_blocks {fam['hold_blocks']} is not in 1..600")
    if not fam["stake_wei"] <= fam["ahead_max_wei"] <= int(0.5e18):
        raise SystemExit(f"front family {n}: ahead_max_eth must be at least the stake and at most 0.5 ETH")
    if not 0 < fam["value_wei"] <= 10 ** 24 or not MIN_SQRT_P <= fam["sqrt_p"] < MAX_SQRT_P or not 0 < fam["liq"] <= 2 ** 128:
        raise SystemExit(f"front family {n}: value_wei (at most 1e6 ETH), sqrt_p (in v4's range) and liq must be above 0")
    if not 0 <= fam["fire_at"] <= 600 or not 0 <= fam["fire_max"] <= 10 or fam["fire_at"] + fam["fire_max"] > TRIGGER_MAX_BLOCKS:
        raise SystemExit(f"front family {n}: fire_at + fire_max must stay within TRIGGER_MAX_BLOCKS ({TRIGGER_MAX_BLOCKS}) and fire_max within 0..10")
    return fam


def front_base_family():
    """the FRONT_* settings as a family (none if FRONT_VALUE_WEI is 0)"""
    base = {"name": env("FRONT_FAMILY_NAME", "v2.433"), "value_wei": FRONT_VALUE_WEI, "fee": FRONT_FEE, "tick_spacing": FRONT_TICK_SPACING, "sqrt_p": FRONT_SQRT_P, "liq": FRONT_LIQ,
            "bot_minout": FRONT_BOT_MINOUT, "ahead_max_wei": FRONT_AHEAD_MAX_WEI, "take_profit": FRONT_TAKE_PROFIT, "hold_blocks": FRONT_HOLD_BLOCKS, "stake_wei": FRONT_STAKE_WEI,
            "dry_run": False, "pin": FRONT_PIN, "fire_at": 0, "fire_max": FRONT_FIRE_MAX}
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", base["name"]):
        raise SystemExit(f"FRONT_FAMILY_NAME must be 1-64 letters, digits, '.', '_' or '-', not {base['name']!r}")
    return {base["value_wei"]: front_family_check(base)} if FRONT_VALUE_WEI > 0 else {}


def front_families(base=None):
    """the launch families front trades, by launch value (see FRONT_FAMILIES above): the base family plus FRONT_FAMILIES. A listed family
    must give its value, fee, tick spacing, price and liquidity (its own fingerprint) and may set the rest; unknown keys are an error"""
    base = front_base_family() if base is None else base
    fams = list(base.values())
    defaults = fams[0] if fams else {"bot_minout": FRONT_BOT_MINOUT, "take_profit": FRONT_TAKE_PROFIT, "hold_blocks": FRONT_HOLD_BLOCKS, "ahead_max_wei": FRONT_AHEAD_MAX_WEI, "stake_wei": FRONT_STAKE_WEI}
    text = env("FRONT_FAMILIES", "").strip()
    try:
        listed = json.loads(text, object_pairs_hook=_no_dup_keys) if text else []
    except ValueError as e:
        raise SystemExit(f"FRONT_FAMILIES is not valid JSON: {e}")
    if not isinstance(listed, list):
        raise SystemExit("FRONT_FAMILIES must be a JSON list of families")
    for i, f in enumerate(listed):
        if not isinstance(f, dict):
            raise SystemExit(f"FRONT_FAMILIES: family {i} is not an object")
        bad = sorted(set(f) - set(FRONT_FAMILY_KEYS))
        if bad:
            raise SystemExit(f"FRONT_FAMILIES: family {i} has unknown keys {bad} (known: {', '.join(FRONT_FAMILY_KEYS)})")
        for k in ("value_wei", "fee", "tick_spacing", "sqrt_p", "liq"):
            if k not in f:
                raise SystemExit(f"FRONT_FAMILIES: family {i} must give {k} (its own launch value and fingerprint)")
        w = f"FRONT_FAMILIES family {i}"
        try:
            fam = {"value_wei": _wei(f["value_wei"], f"{w} value_wei", 1, 10 ** 24), "sqrt_p": _wei(f["sqrt_p"], f"{w} sqrt_p", MIN_SQRT_P, MAX_SQRT_P - 1), "liq": _wei(f["liq"], f"{w} liq", 1, 2 ** 128),
                   "fee": _num(f["fee"], f"{w} fee", 1, 999999, True), "tick_spacing": _num(f["tick_spacing"], f"{w} tick_spacing", 1, 32767, True),
                   "bot_minout": _num(f.get("bot_minout", defaults["bot_minout"]), f"{w} bot_minout", 0.0, 1.0), "take_profit": _num(f.get("take_profit", defaults["take_profit"]), f"{w} take_profit", 0.0, 9.0),
                   "hold_blocks": _num(f.get("hold_blocks", defaults["hold_blocks"]), f"{w} hold_blocks", 1, 600, True),
                   "ahead_max_wei": _eth_wei(f["ahead_max_eth"], f"{w} ahead_max_eth", 0.0, 0.5) if "ahead_max_eth" in f else defaults["ahead_max_wei"],
                   "stake_wei": _eth_wei(f["stake_eth"], f"{w} stake_eth", 0.0, 0.006) if "stake_eth" in f else defaults["stake_wei"],
                   "dry_run": _flag(f.get("dry_run", False), f"{w} dry_run"), "pin": _flag(f.get("pin", FRONT_PIN), f"{w} pin"),
                   "fire_at": _num(f.get("fire_at", 0), f"{w} fire_at", 0, 600, True), "fire_max": _num(f.get("fire_max", FRONT_FIRE_MAX), f"{w} fire_max", 0, 10, True)}
        except SystemExit:
            raise
        except (TypeError, ValueError, OverflowError) as e:
            raise SystemExit(f"{w}: {e}")
        name = f["name"] if "name" in f else f"v{fam['value_wei'] / 1e18:g}"
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
            raise SystemExit(f"{w}: name must be 1-64 letters, digits, '.', '_' or '-', not {name!r}")
        fam["name"] = name
        fams.append(front_family_check(fam))
    by_value = {}
    for fam in fams:
        if fam["value_wei"] in by_value:
            raise SystemExit(f"FRONT_FAMILIES: two families launch with {fam['value_wei']} wei")
        if any(g["name"] == fam["name"] for g in by_value.values()):
            raise SystemExit(f"FRONT_FAMILIES: two families named {fam['name']}")
        by_value[fam["value_wei"]] = fam
    return by_value
try:
    FRONT_FAMILIES = front_base_family(); FRONT_FAMILY_ERROR = None
except (SystemExit, Exception) as e:                                                     # the FRONT_* line itself wrong: front is off for this run (checks); follow runs
    FRONT_FAMILIES = {}; FRONT_FAMILY_ERROR = f"{type(e).__name__}: {e}"
if FRONT_FAMILY_ERROR is None:
    try:
        FRONT_FAMILIES = front_families(FRONT_FAMILIES)
    except (SystemExit, Exception) as e:                                                 # a listed family wrong: it is dropped, the FRONT_* line trades, an alarm at start
        FRONT_FAMILY_ERROR = (f"FRONT_FAMILIES dropped, the FRONT_* line alone trades: " if FRONT_FAMILIES else "FRONT_FAMILIES dropped and there is no FRONT_* line: front is off: ") + f"{type(e).__name__}: {e}"
FRONT_DELAYED = any(f["fire_at"] for f in FRONT_FAMILIES.values())                       # some family fires after the launch block: value-0 calls are looked at for pulls meanwhile
# the decoy signal: the bot's buy behind ours is the only exit that pays (+14% on the 2.4333 line, +6% on the 3.0 line; a decoy, a revert or
# the deadline pays -0.6% to +0.3%). A live front trade whose buy filled and whose return after gas is under FRONT_NONBOT_MIN_RET counts one
# against its family; FRONT_NONBOT_HALT in a row halt front (its file), as on Oct 10 when the decoys sold 289 positions ahead of the bot for
# about -0.3% each; a paying exit resets the family's count. Judged by the return, not by who called the router (the bot's router is public,
# a decoy can go through it). 0 = off. The counts are restored from the day's log at a restart.
FRONT_NONBOT_HALT = int(env("FRONT_NONBOT_HALT", "5")); FRONT_NONBOT_MIN_RET = float(env("FRONT_NONBOT_MIN_RET", "0.02"))
if FRONT_NONBOT_HALT < 0:
    raise SystemExit("FRONT_NONBOT_HALT must be 0 (off) or above")
SEL_MULTICALL = "ac9650d8"; SEL_INIT_POOL = "f7020405"; SEL_MODLIQ = "dd46508f"

T_INIT = keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SEL_BUY = "5ed06f60"; SEL_SELL = "137f1fdd"; SEL_OWNER = "8da5cb5b"; SEL_PM = "8970cdff"
mono = time.monotonic
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
h0x = lambda s: s if s.startswith("0x") else "0x" + s

_log_lock = threading.Lock()
def log(ev):
    ev["t"] = round(time.time(), 3)
    line = json.dumps(ev, separators=(",", ":"))
    with _log_lock:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")


# ---------------------------------------------------------------- RPC and the sequencer
def rpc(method, params, tries=4, timeout=10):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC_URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
            if "result" in d:
                return d["result"]
            last = d.get("error")
            if isinstance(last, dict) and last.get("code") != 429:
                raise RuntimeError(json.dumps(last)[:300])
        except RuntimeError:
            raise
        except Exception as e:
            last = str(e)
        time.sleep(0.2 * (i + 1))
    raise RuntimeError(f"{method}: {last}")


class Sender:
    """warm HTTPS connections to the sequencer (one per slot), TCP_NODELAY, a keepalive every 5 s; post() returns the parsed reply"""
    def __init__(self, url, slots=2):
        u = urllib.parse.urlparse(url); self.host = u.hostname; self.port = u.port or 443; self.path = u.path or "/"
        self.conns = [None] * slots; self.locks = [threading.Lock() for _ in range(slots)]; self.last = [0.0] * slots
        threading.Thread(target=self._keepalive, daemon=True).start()

    def _open(self, i):
        c = http.client.HTTPSConnection(self.host, self.port, timeout=4, context=ssl.create_default_context()); c.connect()
        c.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1); self.conns[i] = c; return c

    def post(self, i, body, retry=True):
        if not self.locks[i].acquire(timeout=0.05):                             # the keepalive holds this slot (a hung ping can take 4 s): a fresh connection now
            return self._oneoff(body)
        try:
            return self._post_locked(i, body, retry)
        finally:
            self.locks[i].release()

    def _oneoff(self, body):
        try:
            c = http.client.HTTPSConnection(self.host, self.port, timeout=4, context=ssl.create_default_context()); c.connect()
            c.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            c.request("POST", self.path, body, {"Content-Type": "application/json"}); r = c.getresponse(); data = r.read(); c.close()
            return json.loads(data)
        except Exception as e:
            return {"error": {"message": f"send failed (one-off connection): {e}"}}

    def _post_locked(self, i, body, retry):
        try:
            c = self.conns[i] or self._open(i)
            c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"})
            r = c.getresponse(); data = r.read(); self.last[i] = mono()
            return json.loads(data)
        except Exception as e:
            try:
                if self.conns[i]: self.conns[i].close()
            except Exception:
                pass
            self.conns[i] = None
            if retry:
                return self._retry(i, body)
            return {"error": {"message": f"send failed: {e}"}}

    def _retry(self, i, body):
        try:
            c = self._open(i); c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"})
            r = c.getresponse(); data = r.read(); self.last[i] = mono(); return json.loads(data)
        except Exception as e:
            self.conns[i] = None; return {"error": {"message": f"send failed twice: {e}"}}

    def _keepalive(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []})
        while True:
            time.sleep(1.0)
            for i in range(len(self.conns)):
                if mono() - self.last[i] > 5.0 and self.locks[i].acquire(blocking=False):
                    try:
                        c = self.conns[i] or self._open(i)
                        c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"}); c.getresponse().read(); self.last[i] = mono()
                    except Exception:
                        self.conns[i] = None
                    finally:
                        self.locks[i].release()


def reply_kind(reply):
    """what a reply to eth_sendRawTransaction says about the transaction: "ok" (accepted), "in" (the node already has it or its
    nonce: it went in), "rejected" (the node refused it: it did not go in), "unknown" (no reply from the node: a transport failure,
    after which the transaction may or may not have been sequenced; Nitro answers only once it is in a block)"""
    if "result" in reply:
        return "ok"
    err = reply.get("error") or {}
    msg = str(err.get("message", "")).lower()
    if "code" not in err:
        return "unknown"
    if "already known" in msg or "nonce too low" in msg:
        return "in"
    return "rejected"


SENDER = None; SIGNER = None


# ---------------------------------------------------------------- feed decoding
def decode_batch(l2msg_b64):
    """the signed transactions (raw bytes) in one L2 message. Kind 4 is one signed transaction: the sequencer sends a block that
    holds a single user transaction this way (about 1 block in 190 in a quiet hour), and our own buy can be that transaction.
    Kind 3 is a batch: segments of 8-byte big-endian length + body, each body itself an L2 message (nested batches included)."""
    return _l2_txs(base64.b64decode(l2msg_b64), 0)


def _l2_txs(raw, depth):
    if not raw or depth > 16:
        return []
    if raw[0] == 4:
        return [raw[1:]]
    if raw[0] != 3:
        return []
    out = []; i = 1; n = len(raw)
    while i + 8 <= n:
        ln = int.from_bytes(raw[i:i+8], "big"); i += 8; seg = raw[i:i+ln]; i += ln
        out += _l2_txs(seg, depth + 1)
    return out


def parse_tx(t):
    """(to, value, data, nonce, hash) for legacy and type 1/2 transactions, else None; `to` lower-case hex without 0x"""
    try:
        if t[0] >= 0xc0:
            f = rlp.decode(t); nonce, to, value, data = f[0], f[3], f[4], f[5]
        elif t[0] == 1:
            f = rlp.decode(t[1:]); nonce, to, value, data = f[1], f[4], f[5], f[6]
        elif t[0] == 2:
            f = rlp.decode(t[1:]); nonce, to, value, data = f[1], f[5], f[6], f[7]
        else:
            return None
        return (to.hex() if to else "", int.from_bytes(value, "big"), bytes(data), int.from_bytes(nonce, "big"), keccak(t).hex())
    except Exception:
        return None


# ---------------------------------------------------------------- state
state = {"seq": 0, "ts": 0, "nonce": None, "base_fee": 20_000_000, "armed": {}, "position": None, "day": None, "trades_today": 0, "pnl_today_usd": 0.0,
         "launches": 0, "fires": 0, "blocks": 0, "stale_blocks": 0, "connected": False, "halted": None, "front_today": 0, "front_halted": None, "front_pnl_today_usd": 0.0, "follow_halted": None,
         "relay_wei": None, "arming": set(), "front_settling": None, "stopping": None, "stop_logged": False, "front_nonbot_streak": {}, "delayed": FRONT_DELAYED, "fam_halted": {},                 # the relay's balance (read at start and every minute when idle, moved by each trade); launches whose receipt is on its way;
                                                                                     # a live front trade out of the slot whose pull check is still running
         "recent": collections.deque(maxlen=8000)}                                   # (seq, to, value, data) of recent ETH-carrying calls: replayed onto a pool armed after its first buys
lock = threading.RLock()


def net_of_fee(x, fee):
    return x - (x * fee + 999_999) // 1_000_000


def apply_buy(p, value):
    """a buy of `value` wei on pool p moves the engine's copy of its price (exact-in ETH: 1/sqrtP grows by the net input over L)"""
    if p["liq"] > 0 and p["sp"] > 0:                                                  # a pool with no liquidity in range is never traded: count, do not price
        p["sp"] = v4math.sqrt_after_buy(p["sp"], p["liq"], net_of_fee(value, p["fee"]))
    p["buys"] += 1


def round_trip_gas_wei():
    """what the trade's own two swaps cost at the base fee"""
    return state["base_fee"] * 250_000


def load_halt():
    """a halt written before a restart still holds"""
    if os.path.exists(HALT_FILE):
        state["halted"] = open(HALT_FILE).read().strip() or "halted"
    if os.path.exists(FRONT_HALT_FILE):
        state["front_halted"] = open(FRONT_HALT_FILE).read().strip() or "halted"
    if os.path.exists(FOLLOW_HALT_FILE):
        state["follow_halted"] = open(FOLLOW_HALT_FILE).read().strip() or "halted"
    for f in FRONT_FAMILIES.values():
        if not is_base_fam(f["name"]) and os.path.exists(fam_halt_file(f["name"])):
            state["fam_halted"][f["name"]] = open(fam_halt_file(f["name"])).read().strip() or "halted"


def fam_halt_file(fam):
    """a listed front family's own halt file (the FRONT_* family halts front as a whole); names are letters, digits, . _ - (the parser)"""
    return FRONT_HALT_FILE + "." + fam


def is_base_fam(fam):
    return fam is None or any(f["value_wei"] == FRONT_VALUE_WEI and f["name"] == fam for f in FRONT_FAMILIES.values())


def halt(reason, front=False, scope=None, fam=None):
    """scope "front": the front strategy only (its own file); "follow": follow and the seat only (its own file); "all" (the default; front=True
    is "front"): all live trading. A front halt with `fam` naming a listed family halts that family alone (its own file); the FRONT_* family's
    halts are front-wide"""
    scope = scope or ("front" if front else "all")
    if scope == "front" and fam is not None and not is_base_fam(fam):
        state["fam_halted"][fam] = reason; path = fam_halt_file(fam); name = f"the front family {fam}"
    else:
        key, path, name = {"front": ("front_halted", FRONT_HALT_FILE, "the front strategy"), "follow": ("follow_halted", FOLLOW_HALT_FILE, "the follow strategy"),
                           "all": ("halted", HALT_FILE, "live trading")}[scope]
        state[key] = reason
    try:
        with open(path, "w") as f:
            f.write(reason + "\n")
        written = True
    except Exception as e:
        written = False; log({"ev": "alarm", "what": f"the halt file {path} could not be written ({str(e)[:80]}): the halt holds in memory until a restart"})
    log({"ev": "alarm", "what": f"{name} halted: {reason}; remove {path} and restart to resume", "halt_file": path})
    return written


def front_off(reason):
    """the front strategy cannot trade live in this run (a setting or the relay's balance): it stays off until a restart finds it
    right; follow is not touched. No file: the cause is checked again at the next start."""
    state["front_halted"] = reason
    log({"ev": "alarm", "what": f"the front strategy is off for this run: {reason}; follow is not affected"})


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def roll_day():
    d = today()
    if state["day"] != d:
        state["day"] = d; state["trades_today"] = 0; state["front_today"] = 0; state["pnl_today_usd"] = 0.0; state["front_pnl_today_usd"] = 0.0


def restore_today():
    """today's live trades from the log: a restart keeps the day's counts and P&L, so the daily caps and stops still hold"""
    d = today(); got = {"trades_today": 0, "front_today": 0, "pnl_today_usd": 0.0, "front_pnl_today_usd": 0.0}; streaks = {}
    for path in (LOG_PATH + ".1", LOG_PATH):                                            # a rotation during the day leaves the morning in .1
        _restore_from(path, d, got, streaks)
    for k, (v, halted_on) in list(streaks.items()):                                     # the owner cleared the decoy halt that this run caused: it starts again
        path = FRONT_HALT_FILE if is_base_fam(k) else fam_halt_file(k)
        if halted_on and not os.path.exists(path):
            log({"ev": "nonbot_streak_reset", "fam": k, "was": v, "why": "the decoy halt's file is gone"}); v = 0
        streaks[k] = v
    state.update(got); state["front_nonbot_streak"] = streaks                          # each family's run of non-paying front exits goes on across a restart
    return got


def _restore_from(path, d, got, streaks):
    try:
        for line in open(path):
            if '"trade_done"' not in line or '"dry":false' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            front = e.get("entry") == "front"
            if front and e.get("nonbot_streak") is not None:                             # the run of non-paying exits goes on across days: decoys keep no calendar
                streaks[e.get("fam") or "front"] = (e["nonbot_streak"], bool(e.get("nonbot_halted")))
            if datetime.datetime.fromtimestamp(e.get("t", 0), datetime.timezone.utc).strftime("%Y-%m-%d") != d:
                continue
            got["front_pnl_today_usd" if front else "pnl_today_usd"] += e.get("pnl_usd") or 0.0
            if e.get("buy") != "no receipt":                                           # a buy that never went in was given back (uncount)
                got["front_today" if front else "trades_today"] += 1
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        pass


def pool_from_receipt(rec):
    """the pool a launch receipt initialized (ETH as currency0, no hook) with its first liquidity, or None"""
    init = None; adds = []
    for l in rec.get("logs", []):
        if l["address"].lower() != POOL_MANAGER or not l["topics"]:
            continue
        tp = l["topics"][0][2:]
        if tp == T_INIT:
            init = l
        elif tp == T_ML:
            d = l["data"]; adds.append((sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), l["topics"][1]))
    if init is None:
        return None
    d = init["data"]; pid = init["topics"][1]
    p = {"pid": pid, "c0": init["topics"][2][-40:], "token": init["topics"][3][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": d[2 + 64*2 + 24: 2 + 64*3],
         "sqrt_p": W(d, 3), "tick0": sgn(W(d, 4))}
    p["liq"] = v4math.active_liquidity(p["tick0"], [(lo, hi, dl) for lo, hi, dl, ppid in adds if ppid == pid])
    p["token_bytes"] = bytes.fromhex(p["token"])
    return p


def _u(b, o):
    return int.from_bytes(b[o:o + 32], "big")


def _s(b, o):
    x = _u(b, o); return x - (1 << 256) if x >> 255 else x


def _dyn(b, base, at):
    """an abi dynamic `bytes` whose offset (from `base`) is the word at `at`: (start, length)"""
    st = base + _u(b, at); ln = _u(b, st)
    if st + 32 + ln > len(b):
        raise ValueError("bytes out of range")
    return st + 32, ln


def decode_launch(data):
    """a PositionManager multicall [initializePool(PoolKey, sqrtPriceX96), modifyLiquidities(abi.encode(actions, params), deadline)]
    as the feed shows it: the pool, its price and its first liquidity, with no receipt. None if it is not that shape."""
    b = bytes(data)
    try:
        if len(b) < 68 or b[:4].hex() != SEL_MULTICALL:
            return None
        arr = 4 + _u(b, 4); n = _u(b, arr)
        if not 0 < n <= 8:
            return None
        key = sqrt_p = None; mint = None
        for i in range(n):
            st, ln = _dyn(b, arr + 32, arr + 32 + 32 * i); sel = b[st:st + 4].hex()
            if sel == SEL_INIT_POOL and ln >= 196 and key is None:
                k = st + 4; key = (k, b[k:k + 160]); sqrt_p = _u(b, k + 160)
            elif sel == SEL_MODLIQ and mint is None:
                a = st + 4; ust, _ = _dyn(b, a, a); ast, aln = _dyn(b, ust, ust); actions = b[ast:ast + aln]
                parr = ust + _u(b, ust + 32); pn = _u(b, parr)
                for j in range(min(pn, len(actions))):
                    pst, pln = _dyn(b, parr + 32, parr + 32 + 32 * j)
                    if actions[j] == 0x02 and pln >= 384:                                # MINT_POSITION(PoolKey, tickLower, tickUpper, liquidity, ...)
                        mint = (b[pst:pst + 160], _s(b, pst + 160), _s(b, pst + 192), _u(b, pst + 224)); break
        if key is None or mint is None or mint[0] != key[1] or not MIN_SQRT_P <= sqrt_p < MAX_SQRT_P or not mint[1] < mint[2]:
            return None
        kb = key[1]
        return {"pid": "0x" + keccak(kb).hex(), "c0": kb[12:32].hex(), "token": kb[44:64].hex(), "fee": _u(kb, 64), "tick_spacing": _s(kb, 96), "hooks": kb[140:160].hex(),
                "sqrt_p": sqrt_p, "lo": mint[1], "hi": mint[2], "mint_liq": mint[3]}
    except Exception:
        return None


def tick_at(sqrt_p):
    return math.floor(2 * math.log(sqrt_p / 2 ** 96) / math.log(1.0001))


def front_mismatch(d, liq, fam):
    """why a launch of the front shape cannot be traded (None: it can): an ETH pair with no hook, a fee other than its family's (front's
    own bound: the 2.4333 line is at 0.25%, the 3.0 and 5.0 lines at 1%; FEE_MIN/MAX_PPM are follow's), liquidity at the launch price"""
    if d["c0"] != "0" * 40 or d["hooks"] != "0" * 40:
        return "not an ETH pair without a hook"
    if fam["fee"] and d["fee"] != fam["fee"]:
        return f"fee {d['fee']}"
    if liq < MIN_LIQUIDITY:
        return "no liquidity at the launch price"
    return None


def front_fingerprint(d, fam):
    """what differs from every launch of this family seen so far: [] for none (a setting of 0 is not compared)"""
    new = []
    for k, want, name in (("tick_spacing", fam["tick_spacing"], "tick spacing"), ("sqrt_p", fam["sqrt_p"], "launch price"), ("mint_liq", fam["liq"], "liquidity")):
        if want and d[k] != want:
            new.append(f"{name} {d[k]}")
    return new


def arm_front(data, h, seq, seen_at, fam):
    """a front launch in the feed (of the family `fam`, told by its value): armed at once from its calldata; it fires at the end of
    this block (ingest). Nothing here may raise into the feed (the rest of the block is follow's): a launch that does not decode or
    does not match is logged and left."""
    try:
        d = decode_launch(data)
        if d is None:
            log({"ev": "launch_undecoded", "tx": h, "seq": seq, "family": "front", "fam": fam["name"]}); return
        if d["pid"] in state["armed"]:                                                 # the same pool again: the first arming stands
            log({"ev": "skip", "why": "front: pool already armed", "pid": d["pid"], "tx": h, "seq": seq}); return
        t0 = tick_at(d["sqrt_p"]); liq = d["mint_liq"] if d["lo"] <= t0 < d["hi"] else 0
        why = front_mismatch(d, liq, fam); new = front_fingerprint(d, fam)
        if why is None and new and (FRONT_PIN or fam["pin"]):                            # FRONT_PIN pins every family; a family's own pin just itself
            why = ("new fingerprint (FRONT_PIN=1): " if FRONT_PIN else f"new fingerprint ({fam['name']} pinned): ") + ", ".join(new)
        p = {**{k: d[k] for k in ("pid", "c0", "token", "fee", "tick_spacing", "hooks", "sqrt_p")}, "tick0": t0, "liq": liq, "token_bytes": bytes.fromhex(d["token"]),
             "launch_seq": seq, "launch_ts": state["ts"], "armed_at": mono(), "arm_ms": round(1000 * (mono() - seen_at), 1), "first_buy": None, "status": "armed", "tx": h,
             "sp": float(d["sqrt_p"]), "buys": 0, "eth_in": 0, "bot_seq": None, "entry": "front", "launcher_code": "front", "arm_seq": seq, "eligible": why is None,
             "fam": fam["name"], "fam_cfg": fam}
        state["launches"] += 1
        if why is None:
            state["armed"][p["pid"]] = p
        log({"ev": "armed", "pid": p["pid"], "token": p["token"], "fee": p["fee"], "tick_spacing": p["tick_spacing"], "hooks": p["hooks"][-8:], "liq": liq, "sqrt_p": p["sqrt_p"], "seq": seq,
             "arm_ms": p["arm_ms"], "arm_seq": seq, "eligible": p["eligible"], "eth_pair": p["c0"] == "0" * 40, "buys_before_arm": 0, "launcher_code": "front", "entry": "front", "fam": fam["name"],
             "fingerprint": "new: " + ", ".join(new) if new else "known", **({"why": "front: " + why} if why else {})})
    except Exception:
        log({"ev": "alarm", "what": "front launch not armed (error)", "tx": h, "seq": seq, "trace": traceback.format_exc()[-400:]})


def wait_receipt(h, timeout, every=0.04):
    t0 = mono()
    while mono() - t0 < timeout:
        try:
            r = rpc("eth_getTransactionReceipt", [h0x(h)], tries=1, timeout=3)
            if r:
                return r
        except Exception:
            pass
        time.sleep(every)
    return None


def arm_launch(tx_hash, seq, ts, seen_at, to=None):
    """thread: the launch receipt, the pool, the arming. A launch found by its call alone (not sent to a LAUNCHERS address) is traded
    only if the contract it called carries the operator's launcher code: anyone can deploy a contract with that function."""
    code = {}

    def fetch(tag="latest"):
        try:
            c = rpc("eth_getCode", [h0x(to), tag], tries=2, timeout=3)
            if len(c) > 2:
                code["hash"] = keccak(bytes.fromhex(c[2:])).hex(); code.pop("err", None)
            else:
                code["err"] = "no code yet at " + str(tag)                    # a backend a few blocks behind: the launcher was deployed 7-8 blocks before its call
        except Exception as e:
            code["err"] = str(e)[:100]
    if to and to not in LAUNCHERS:
        ct = threading.Thread(target=fetch, daemon=True); ct.start()
    rec = wait_receipt(tx_hash, 4.0)
    if rec is None:
        log({"ev": "launch_no_receipt", "tx": tx_hash, "seq": seq}); return
    p = pool_from_receipt(rec)
    if p is None or rec.get("status") != "0x1":
        log({"ev": "launch_no_pool", "tx": tx_hash, "seq": seq, "status": rec.get("status")}); return
    p.update({"launch_seq": seq, "launch_ts": ts, "armed_at": mono(), "arm_ms": round(1000 * (mono() - seen_at), 1), "first_buy": None, "status": "armed", "tx": tx_hash,
              "sp": float(p["sqrt_p"]), "buys": 0})
    eligible = p["c0"] == "0" * 40 and p["hooks"] == "0" * 40 and FEE_MIN_PPM <= p["fee"] <= FEE_MAX_PPM and p["liq"] >= MIN_LIQUIDITY
    p["launcher_code"] = "listed"
    if to and to not in LAUNCHERS:
        ct.join(3.0)
        if "hash" not in code:                                                # no code read (an error, or a node behind): again, at the launch's own block
            fetch(rec.get("blockNumber", "latest"))
        p["launcher_code"] = "operator" if code.get("hash") in LAUNCHER_CODE_HASHES else ("unknown " + str(code.get("hash", code.get("err", "no answer")))[:16])
        eligible = eligible and p["launcher_code"] == "operator"
    if ENTRY == "auto":                                     # the original launcher: its crowd comes 40-60 blocks in, buying every few blocks (follow); a per-launch copy: one burst at + 8/9 (seat)
        p["entry"] = "seat" if (to and to not in LAUNCHERS and code.get("hash") in SEAT_CODE_HASHES) else "follow"
    else:
        p["entry"] = ENTRY
    p["eligible"] = eligible
    with lock:
        p["arm_seq"] = state["seq"]
        for s, to, value, data in list(state["recent"]):                              # buys that landed while the receipt was on its way
            if s >= seq and p["token_bytes"] in data and to != p["token"]:
                apply_buy(p, value)
                if value >= MIN_TRIGGER_WEI and p["first_buy"] is None:
                    p["first_buy"] = s; p["status"] = "late"
                    log({"ev": "first_buy", "pid": p["pid"], "seq": s, "offset": s - seq, "value": value, "fee": p["fee"], "eligible": eligible, "before_arm": True})
        state["armed"][p["pid"]] = p; state["launches"] += 1
    log({"ev": "armed", "pid": p["pid"], "token": p["token"], "fee": p["fee"], "tick_spacing": p["tick_spacing"], "hooks": p["hooks"][-8:], "liq": p["liq"], "sqrt_p": p["sqrt_p"], "seq": seq,
         "arm_ms": p["arm_ms"], "arm_seq": p["arm_seq"], "eligible": eligible, "eth_pair": p["c0"] == "0" * 40, "buys_before_arm": p["buys"], "launcher_code": p["launcher_code"], "entry": p["entry"]})


def arm_launch_thread(tx_hash, seq, ts, seen_at, to):
    """arm_launch, and the launch off the 'receipt on its way' list whatever happens (a live front trade waits while it is on it)"""
    try:
        arm_launch(tx_hash, seq, ts, seen_at, to)
    except Exception:
        log({"ev": "alarm", "what": "arming failed", "tx": tx_hash, "trace": traceback.format_exc()[-400:]})
    finally:
        with lock:
            state["arming"].discard(tx_hash)


def prune(seq):
    for pid in [k for k, p in state["armed"].items() if seq - p["launch_seq"] > 3000]:
        p = state["armed"].pop(pid)
        if p["first_buy"] is None:
            log({"ev": "no_first_buy", "pid": pid, "fee": p["fee"]})


# ---------------------------------------------------------------- transactions
RELAY_TO = to_checksum_address(RELAY) if RELAY else "0x" + "00" * 20                     # a dry run with no relay yet still builds the transactions


def tx_buy(p, nonce, min_out, deadline, stake=None):
    data = "0x" + SEL_BUY + word(p["c0"]) + word(p["token"]) + word(p["fee"]) + word(p["tick_spacing"]) + word(p["hooks"]) + word(STAKE_WEI if stake is None else stake) + word(min_out) + word(deadline)
    return {"to": RELAY_TO, "value": 0, "data": data, "gas": BUY_GAS, "gasPrice": int(state["base_fee"] * GAS_HEADROOM), "nonce": nonce, "chainId": CHAIN_ID}


def tx_sell(p, nonce, min_out=0, deadline=0):
    data = "0x" + SEL_SELL + word(p["c0"]) + word(p["token"]) + word(p["fee"]) + word(p["tick_spacing"]) + word(p["hooks"]) + word(min_out) + word(deadline)
    return {"to": RELAY_TO, "value": 0, "data": data, "gas": SELL_GAS, "gasPrice": int(state["base_fee"] * SELL_GAS_HEADROOM), "nonce": nonce, "chainId": CHAIN_ID}


def sign(tx):
    raw = bytes(SIGNER.sign_transaction(tx).raw_transaction)
    return raw, keccak(raw).hex()


def body(raw):
    return json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x" + raw.hex()]})


def fire(p, seq, ts, trig_value, trig_hash, seen_at, fire_seq=None):
    """the operator's first real-size buy on an armed pool is in block `seq` (we fire in block `fire_seq`, the same unless
    BUY_DELAY_BLOCKS): buy now, sell on the first buy behind ours worth TAKE_PROFIT, or HOLD_BLOCKS after our buy's block"""
    try:
        _fire(p, seq, ts, trig_value, trig_hash, seen_at, seq if fire_seq is None else fire_seq)
    except Exception:
        log({"ev": "alarm", "what": "fire failed", "pid": p["pid"], "trace": traceback.format_exc()[-600:]})
        pos = state["position"]
        if pos is not None and pos["pid"] == p["pid"] and pos.get("buy_hash") is None:
            state["position"] = None; uncount(pos)


def uncount(pos):
    """the trade did not happen (refused, never in): it gives its place in the day's count back"""
    k = pos.get("count_key", "trades_today"); state[k] = max(0, state[k] - 1)


def _fire(p, seq, ts, trig_value, trig_hash, seen_at, fire_seq):
    roll_day()
    if state["stopping"] is not None:
        p["status"] = "skipped"; log({"ev": "skip", "why": "stopping: no new trade", "pid": p["pid"], "seq": seq}); return
    front = p.get("entry") == "front"; dry = DRY_RUN or (front and (FRONT_DRY_RUN or p["fam_cfg"]["dry_run"]))
    halted = state["halted"] or (state["front_halted"] or state["fam_halted"].get(p.get("fam")) if front else state["follow_halted"])
    if halted and not dry:
        log({"ev": "skip", "why": "halted: " + halted, "pid": p["pid"], "seq": seq}); return
    held = state["position"]
    drop = held is not None and held["dry"] and not dry and held.get("entry") == "front"     # a dry front trade never holds up a live one (dropped below, once this one fires)
    if held is not None and not drop:
        log({"ev": "skip", "why": "position open", "pid": p["pid"], "seq": seq}); return
    count_key, cap = ("front_today", FRONT_MAX_PER_DAY) if front else ("trades_today", MAX_TRADES_PER_DAY)
    pnl_key, stop = ("front_pnl_today_usd", FRONT_DAILY_STOP_USD) if front else ("pnl_today_usd", DAILY_STOP_USD)   # each strategy against its own stop
    if state[count_key] >= cap:
        log({"ev": "skip", "why": "daily cap", "pid": p["pid"], "seq": seq, count_key: state[count_key]}); return
    if state[pnl_key] <= -stop:
        log({"ev": "skip", "why": "daily stop", "pid": p["pid"], "seq": seq, pnl_key: round(state[pnl_key], 2)}); return
    if seq - p["launch_seq"] > TRIGGER_MAX_BLOCKS:
        log({"ev": "skip", "why": "late first buy (not the crowd)", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"]}); return
    if not p["eligible"]:
        log({"ev": "skip", "why": "pool not eligible", "pid": p["pid"], "fee": p["fee"], "liq": p["liq"]}); return
    fam = p.get("fam_cfg") if front else None
    stake = fam["stake_wei"] if front else STAKE_WEI
    if not dry and state["relay_wei"] is not None and state["relay_wei"] < stake:
        log({"ev": "skip", "why": "the relay holds less than the stake", "pid": p["pid"], "seq": seq, "relay_eth": state["relay_wei"] / 1e18}); return
    if front and not dry and state["front_settling"] is not None:
        log({"ev": "skip", "why": "front: the last front trade's pull check is still running", "pid": p["pid"], "seq": seq}); return
    follow_can = (state["trades_today"] < MAX_TRADES_PER_DAY and state["pnl_today_usd"] > -DAILY_STOP_USD and (state["relay_wei"] is None or state["relay_wei"] >= STAKE_WEI))
    if front and not dry and follow_can and (state["arming"] or any(q.get("entry") != "front" and q["eligible"] and (q["status"] == "delayed" or (q["status"] == "armed" and q["first_buy"] is None))
                                                     and seq - q["launch_seq"] <= TRIGGER_MAX_BLOCKS
                                                     for q in state["armed"].values())):
        log({"ev": "skip", "why": "front: a follow launch is waiting for its trigger (follow has the slot first)", "pid": p["pid"], "seq": seq}); return
    hold, send_after = (fam["hold_blocks"], fam["hold_blocks"]) if front else (HOLD_BLOCKS, HOLD_BLOCKS - SELL_LEAD_BLOCKS)
    fee = p["fee"]; sp1 = int(p["sp"])                                             # the pool as the feed shows it: the trigger and every buy before it
    expected = v4math.buy_out_int(sp1, p["liq"], stake, fee); min_out = int(expected * (1 - BUY_SLIP))
    sp2 = int(v4math.sqrt_after_buy(sp1, p["liq"], net_of_fee(stake, fee)))
    eth_back_flat = v4math.sell_out_int(sp2, p["liq"], expected, fee)             # what the sell gets if nobody buys behind us
    nonce = state["nonce"] if state["nonce"] is not None else 0
    deadline = ts + BUY_DEADLINE_S if BUY_DEADLINE_S > 0 else 0                        # 0: no deadline (the relay skips its check)
    buy = tx_buy(p, nonce, min_out, deadline, stake); sell = tx_sell(p, nonce + 1)
    pos = {"pid": p["pid"], "token": p["token"], "fee": fee, "entry": p.get("entry", ENTRY), "trig_seq": seq, "trig_ts": ts, "trig_value": trig_value, "trig_hash": trig_hash, "fired_at": mono(), "nonce": nonce,
           "expected_tokens": expected, "min_out": min_out, "flat_eth_back": eth_back_flat, "buy_seq": None, "sell_sent": False, "sell_seq_sent": None, "buy_hash": None, "sell_hash": None, "sell_raw": None, "dry": dry,
           "fire_seq": fire_seq, "plan_buy_seq": fire_seq + 2, "plan_sell_seq": fire_seq + 2 + hold, "feed_tokens": None, "tp_ret": None,
           "stake": stake, "send_after": send_after, "tp": fam["take_profit"] if front else TAKE_PROFIT, "count_key": count_key, "pnl_key": pnl_key,
           "fallback_s": SELL_FALLBACK_S + (0.11 * (hold - (HOLD_BLOCKS - SELL_LEAD_BLOCKS)) if front else 0.0), "launch_seq": p["launch_seq"], **({"fam": p["fam"]} if front else {})}
    if drop:
        log({"ev": "skip", "why": "dry front position dropped for a live trade", "pid": held["pid"], "seq": seq})
    state["position"] = pos; state["fires"] += 1; state[count_key] += 1; p["status"] = "fired"
    if dry:
        log({"ev": "would_fire", **{k: v for k, v in pos.items() if k not in ("dry", "sell_raw")}, "buy_tx": buy, "sell_tx": sell, "react_ms": round(1000 * (mono() - seen_at), 1)})
        return
    t0 = mono(); raw_b, hb = sign(buy); raw_s, hs = sign(sell); pos["buy_hash"] = hb; pos["sell_hash"] = hs; pos["sell_raw"] = raw_s; t1 = mono()
    state["nonce"] = nonce + 2                                                     # reserved: the buy and the sell behind it
    log({"ev": "fire", **{k: v for k, v in pos.items() if k not in ("sell_raw", "dry")}, "sign_ms": round(1000 * (t1 - t0), 1), "react_ms": round(1000 * (t1 - seen_at), 1)})
    threading.Thread(target=deliver_buy, args=(pos, raw_b, t1), daemon=True).start()


def deliver_buy(pos, raw_b, t1):
    """thread: the buy to the sequencer, off the feed thread and the lock. Nitro answers once the transaction is in a block, and a
    reply that never comes (4 s timeout, then a second try) must not hold up the feed: if the buy went in, the feed shows it and the
    sell goes on schedule. A refusal closes the position; a lost reply leaves it open for the schedule and settle to finish."""
    reply = SENDER.post(0, body(raw_b)); kind = reply_kind(reply)
    log({"ev": "buy_reply", "pid": pos["pid"], "kind": kind, "reply": reply, "send_ms": round(1000 * (mono() - t1), 1)})
    if kind == "unknown":
        pos["buy_reply_lost"] = True
        log({"ev": "alarm", "what": "no reply to our buy: it may have gone in; the position stays open, the sell goes on schedule, settle reads the receipts", "pid": pos["pid"], "reply": reply})
    elif kind == "rejected":                                                       # the node refused it: it is not in
        pos["buy_rejected"] = True; log({"ev": "buy_rejected", "pid": pos["pid"], "nonce": pos["nonce"], "reply": reply})
    pos["buy_reply"] = reply
    if kind != "rejected":
        return
    with lock:
        closed = state["position"] is pos and not pos["sell_sent"]
        if closed:                                                                 # nothing to sell: the schedule stops; the position stays open (no new trade) until the nonce is right
            pos["sell_sent"] = True; pos["sell_why"] = "buy refused"
    if closed:
        n = chain_nonce()                                                          # nothing of ours is in flight: the chain's count is right
        with lock:
            state["nonce"] = n if n is not None else pos["nonce"]                  # no answer: the refused buy's nonce was not used
            state["position"] = None; uncount(pos)
        log({"ev": "nonce", "chain": n, "engine": state["nonce"]})
    # refused after its sell went out (a slow refusal): the sell is refused too, and settle closes the trade


def send_sell(why, pos=None):
    """the sell of the position in the slot (of `pos` only if it is still the one there); called under the lock"""
    cur = state["position"]
    pos = cur if pos is None else pos
    if pos is None or pos is not cur or pos["sell_sent"]:
        return
    pos["sell_sent"] = True; pos["sell_seq_sent"] = state["seq"]; pos["sell_sent_at"] = mono(); pos["sell_why"] = why
    if pos["dry"]:
        log({"ev": "would_sell", "pid": pos["pid"], "seq": state["seq"], "why": why, "buy_seq": pos["buy_seq"], "after_buy": state["seq"] - pos["buy_seq"] if pos["buy_seq"] else None, "tp_ret": pos["tp_ret"],
             "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
        threading.Thread(target=settle_dry, args=(pos,), daemon=True).start()
        return
    threading.Thread(target=deliver_sell, args=(pos, why, state["seq"]), daemon=True).start()


SELL_TRIES = 4


def deliver_sell(pos, why, seq):
    """thread: the presigned sell to the sequencer until it is in: alternating connections, a short pause between tries (a sell
    refused for its nonce while our buy is still being sequenced goes in on the next try); then the settlement"""
    replies = []
    for k in range(SELL_TRIES):
        reply = SENDER.post(1 if k % 2 == 0 else 0, body(pos["sell_raw"])); replies.append(reply)
        if reply_kind(reply) in ("ok", "in"):
            break
        time.sleep(0.05)
    pos["sell_reply"] = replies[-1]
    log({"ev": "sell_sent", "pid": pos["pid"], "seq": seq, "why": why, "buy_seq": pos["buy_seq"], "after_buy": seq - pos["buy_seq"] if pos["buy_seq"] else None, "tp_ret": pos["tp_ret"],
         "hash": pos["sell_hash"], "nonce": pos["nonce"] + 1, "tries": len(replies), "reply": replies[-1], "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
    if reply_kind(replies[-1]) not in ("ok", "in"):
        log({"ev": "alarm", "what": f"the sell was not accepted after {len(replies)} tries", "pid": pos["pid"], "replies": replies})
    settle(pos)


def settle_dry(pos):
    time.sleep(1.0)
    with lock:
        if state["position"] is pos:
            state["position"] = None
    log({"ev": "trade_done", "dry": True, "pid": pos["pid"], "trig_seq": pos["trig_seq"], "plan_buy_seq": pos["plan_buy_seq"], "plan_sell_seq": pos["plan_sell_seq"], "sell_seq_sent": pos["sell_seq_sent"],
         "sell_why": pos.get("sell_why"), "tp_ret": pos["tp_ret"], **({"fam": pos["fam"]} if pos.get("fam") else {})})


def swap_of(rec, pid):
    for l in rec.get("logs", []):
        if l["address"].lower() == POOL_MANAGER and l["topics"] and l["topics"][0][2:] == T_SWAP and l["topics"][1] == pid:
            d = l["data"]; a0 = sgn(W(d, 0)); a1 = sgn(W(d, 1))
            if a0 >= (1 << 127): a0 -= 1 << 128
            if a1 >= (1 << 127): a1 -= 1 << 128
            return a0, a1
    return None


def settle(pos):
    """thread: both receipts, the pull check, the P&L; whatever happens, the position is closed and the nonce re-read"""
    try:
        _settle(pos)
    except Exception:
        log({"ev": "alarm", "what": "settle failed", "pid": pos["pid"], "trace": traceback.format_exc()[-600:]})
        with lock:
            if state["position"] is pos:
                state["position"] = None
            if state["front_settling"] is pos:
                state["front_settling"] = None
        refresh_nonce()


def _settle(pos):
    rb = wait_receipt(pos["buy_hash"], RECEIPT_TIMEOUT_S); rs = wait_receipt(pos["sell_hash"], RECEIPT_TIMEOUT_S)
    out = {"ev": "trade_done", "dry": False, "entry": pos.get("entry"), "stake": pos.get("stake", STAKE_WEI), "pid": pos["pid"], "token": pos["token"], "fee": pos["fee"], "trig_seq": pos["trig_seq"], "trig_value": pos["trig_value"], "nonce": pos["nonce"],
           "expected_tokens": pos["expected_tokens"], "min_out": pos["min_out"], "buy_seq_feed": pos["buy_seq"], "sell_why": pos.get("sell_why"), "sell_seq_sent": pos["sell_seq_sent"],
           "launch_seq": pos.get("launch_seq"), **({"fam": pos["fam"]} if pos.get("fam") else {})}
    gas_wei = 0; eth_in = 0; eth_out = 0; tokens = 0
    for name, rec in (("buy", rb), ("sell", rs)):
        if rec is None:
            out[name] = "no receipt"; continue
        bn = int(rec["blockNumber"], 16); ok = rec.get("status") == "0x1"; g = int(rec["gasUsed"], 16) * int(rec["effectiveGasPrice"], 16); gas_wei += g
        sw = swap_of(rec, pos["pid"]) if ok else None
        out[name] = {"block": bn, "status": "ok" if ok else "reverted", "gas_usd": round(g / 1e18 * ETH_USD, 4), "index": int(rec["transactionIndex"], 16)}
        if sw:
            a0, a1 = sw
            if name == "buy":
                eth_in = -a0; tokens = a1; out[name]["eth_in"] = eth_in; out[name]["tokens"] = tokens
            else:
                eth_out = a0; out[name]["eth_out"] = eth_out; out[name]["tokens_in"] = -a1
    out["feed_tokens"] = pos["feed_tokens"]; out["tp_ret"] = pos["tp_ret"]
    if pos.get("entry") == "front" and rb is not None and rs is not None:              # both in, both nonces used: the slot is free for follow during the pull check;
        with lock:                                                                     # front itself waits for it (front_settling), so a pull still halts it before its next trade
            state["front_settling"] = pos
            if state["position"] is pos:
                state["position"] = None; state["nonce"] = max(state["nonce"] or 0, pos["nonce"] + 2)
    if rb and rs and rb.get("status") == "0x1":
        b0 = int(rb["blockNumber"], 16); b1 = int(rs["blockNumber"], 16); i1 = int(rs["transactionIndex"], 16)
        out["hold_blocks"] = out["sell_after_buy_blocks"] = b1 - b0; out["buy_offset"] = b0 - pos["trig_seq"]
        time.sleep(PULL_WATCH_S)                                                           # the operator's reaction to us comes 5-13 blocks after our buy: let it land, to measure it
        pulls = []
        try:
            head = int(rpc("eth_blockNumber", []), 16)                                     # Dwellir's node refuses a range past its head ("block range extends beyond current head block"):
            ls = rpc("eth_getLogs", [{"fromBlock": hex(b0), "toBlock": hex(min(b1 + 30, head)), "address": h0x(POOL_MANAGER), "topics": [h0x(T_ML), pos["pid"]]}])   # the halt needs blocks <= b1 only
            out["pull_check_to"] = min(b1 + 30, head) - b1
            pulls = sorted((int(l["blockNumber"], 16), int(l["transactionIndex"], 16)) for l in ls if sgn(W(l["data"], 2)) < 0)
            out["pull_after_buy_blocks"] = pulls[0][0] - b0 if pulls else None
            out["pulled_before_sell"] = bool(pulls) and pulls[0] < (b1, i1)               # the one number that decided every live trade
        except Exception as e:
            out["pull_check"] = str(e)[:100]                                           # neither halt can be decided without the logs: say so
            log({"ev": "alarm", "what": "pull check unreadable: check the pool's pull by hand", "pid": pos["pid"], "err": str(e)[:100]})
        if out.get("pulled_before_sell"):                                                  # each strategy's pull halts that strategy (Oct 11 14:41: a follow pull at +3 had halted front too)
            halt(f"the operator's pull landed {out['pull_after_buy_blocks']} blocks after our buy, at or before our sell ({b1 - b0}): its reaction is now faster than our exit",
                 scope="front" if pos.get("entry") == "front" else "follow", fam=pos.get("fam"))
        elif pulls and pos.get("entry") != "front" and FOLLOW_NEAR_MISS_BLOCKS and out["pull_after_buy_blocks"] <= FOLLOW_NEAR_MISS_BLOCKS:   # behind our sell, but too close
            out["near_miss"] = True
            halt(f"near miss: the operator's pull landed {out['pull_after_buy_blocks']} blocks after our buy, {out['pull_after_buy_blocks'] - (b1 - b0)} after our sell ({b1 - b0}): "
                 f"the margin before its reaction is gone (FOLLOW_NEAR_MISS_BLOCKS {FOLLOW_NEAR_MISS_BLOCKS})", scope="follow")
    if rb and rb.get("status") == "0x1" and not out.get("pulled_before_sell") and not (isinstance(out.get("sell"), dict) and out["sell"].get("tokens_in")):
        halt("the buy filled and the sell sold none of it (sell: " + (out["sell"]["status"] if isinstance(out.get("sell"), dict) else str(out.get("sell"))) + ")",
             front=pos.get("entry") == "front")                                          # front-wide even for a listed family: the cause is usually the sell path, not the line
    pnl = eth_out - eth_in - gas_wei
    if pos.get("entry") == "front" and rb is not None and rb.get("status") == "0x1" and eth_in and FRONT_NONBOT_HALT:   # the decoy signal, by the trade's return (see FRONT_NONBOT_HALT)
        paid = pnl / eth_in >= FRONT_NONBOT_MIN_RET; fam = pos.get("fam") or "front"
        with lock:
            state["front_nonbot_streak"][fam] = 0 if paid else state["front_nonbot_streak"].get(fam, 0) + 1
            streak = state["front_nonbot_streak"][fam]
        out["nonbot_streak"] = streak; out["bot_exit"] = bool(pos.get("bot_exit"))
        if streak >= FRONT_NONBOT_HALT and state["front_halted"] is None and not state["fam_halted"].get(fam):
            out["nonbot_halted"] = halt(f"{streak} {fam} front trades in a row paid under {FRONT_NONBOT_MIN_RET:+.0%} (last: {pos.get('sell_why')}, {pnl / eth_in:+.1%}): "
                                        f"decoys or a changed schedule (FRONT_NONBOT_HALT {FRONT_NONBOT_HALT})", front=True, fam=fam)   # a halt whose file failed resets nothing later
    out.update({"eth_in": eth_in, "eth_out": eth_out, "gas_wei": gas_wei, "pnl_eth": pnl / 1e18, "pnl_usd": round(pnl / 1e18 * ETH_USD, 3), "ret": round((eth_out - eth_in) / eth_in, 4) if eth_in else None,
                "flat_eth_back": pos["flat_eth_back"]})
    n = chain_nonce()                                                                  # both transactions are final now: the chain's count is the truth
    with lock:
        roll_day(); k = pos.get("pnl_key", "pnl_today_usd"); state[k] += out["pnl_usd"]
        if state["relay_wei"] is not None:                                             # the relay paid the stake and got the sell (the wallet pays the gas); fee_loop reconciles
            state["relay_wei"] += eth_out - eth_in
        if rb is None:                                                                 # no buy receipt: the buy never went in; it does not count against the cap
            uncount(pos)
        released = state["front_settling"] is pos
        if n is not None:                                                              # a front trade out of the slot early: a follow trade may hold nonces above the chain's count
            state["nonce"] = max(n, state["nonce"] or 0) if released else n
        if released:
            state["front_settling"] = None
        if state["position"] is pos:
            state["position"] = None
    log(out)
    log({"ev": "nonce", "chain": n, "engine": state["nonce"]})


NONCE_TRIES = 60


def chain_nonce(tries=None):
    """the wallet's next nonce from the chain, retried with backoff (4 minutes in all if the RPC fails fast, 9 if it hangs): a nonce
    left above the chain's would make every later buy refused; the caller keeps its position open meanwhile, so no trade starts on a
    wrong nonce"""
    err = None
    for i in range(tries or NONCE_TRIES):
        if i and state["stopping"] is not None:                                        # stopping: no trade will use it, the next start reads the chain's count
            return None
        try:
            return int(rpc("eth_getTransactionCount", [h0x(WALLET), "pending"], tries=1, timeout=5), 16)
        except Exception as e:
            err = e; time.sleep(min(5.0, 0.25 * (i + 1)))
    log({"ev": "alarm", "what": "nonce refresh failed", "err": str(err)[:200]})
    return None


def refresh_nonce():
    """after a settle that failed: the chain's count, never below the engine's"""
    n = chain_nonce()
    with lock:
        if n is not None and state["position"] is None:
            state["nonce"] = max(n, state["nonce"] or 0)
    log({"ev": "nonce", "chain": n, "engine": state["nonce"]})


def watchdog_tick():
    """the sell's wall-clock fallback, if the feed stalls: for the position it looked at, and only if that one is still in the slot"""
    pos = state["position"]
    if pos and not pos["sell_sent"] and mono() - pos["fired_at"] > pos.get("fallback_s", SELL_FALLBACK_S):
        with lock:
            send_sell("time fallback", pos)


def on_stop(signum, frame):
    """SIGTERM (systemctl stop or restart): only a flag (a signal handler may run while the main thread holds the log's lock). The feed
    runs on, so an open trade sells on schedule; no new trade starts; stop_tick ends the engine once nothing is open."""
    if state["stopping"] is None:
        state["stopping"] = mono()


EXIT = os._exit


def stop_tick():
    """on the watchdog's thread: once stopping, exit when no trade is open and no front trade's pull check is running, or after
    STOP_WAIT_S (an open trade then is logged as an alarm: its result must be checked)"""
    t0 = state["stopping"]
    if t0 is None:
        return
    pos = state["position"]
    if not state["stop_logged"]:
        state["stop_logged"] = True
        log({"ev": "stopping", "position": pos["pid"] if pos else None, "sell_sent": pos["sell_sent"] if pos else None, "front_settling": state["front_settling"] is not None})
    idle = pos is None and state["front_settling"] is None
    if idle or mono() - t0 > STOP_WAIT_S:
        if not idle:
            log({"ev": "alarm", "what": f"stopped with a trade still open after {STOP_WAIT_S:g} s: check it", "pid": (pos or state["front_settling"] or {}).get("pid")})
        log({"ev": "stopped", "idle": idle, "waited_s": round(mono() - t0, 2)})
        EXIT(0)


def watchdog():
    last_err = 0.0
    while True:
        time.sleep(0.02)
        for tick in (watchdog_tick, stop_tick):
            try:
                tick()
            except Exception:                                                          # the fallback and the stop must outlive any one error
                if mono() - last_err > 60:
                    last_err = mono(); log({"ev": "alarm", "what": f"{tick.__name__} failed", "trace": traceback.format_exc()[-400:]})


def relay_balance():
    """the relay's ETH (the stakes come from it), or None"""
    if not RELAY:
        return None
    try:
        return int(rpc("eth_getBalance", [h0x(RELAY), "latest"], tries=2, timeout=3), 16)
    except Exception:
        return None


def fee_loop():
    """the base fee every 10 s, on its own thread (a slow RPC never holds up the time fallback); the relay's balance every minute
    while no trade is open (during one, the stake is out of it)"""
    k = 0
    while True:
        try:
            b = rpc("eth_getBlockByNumber", ["latest", False], tries=1, timeout=3); state["base_fee"] = int(b["baseFeePerGas"], 16); state["fee_at"] = mono()
        except Exception:
            pass
        k += 1
        if k % 6 == 0 and state["position"] is None and state["front_settling"] is None:
            bal = relay_balance()
            with lock:
                if bal is not None and state["position"] is None and state["front_settling"] is None:
                    state["relay_wei"] = bal
        time.sleep(10)


# ---------------------------------------------------------------- the feed
def our_buy_landed(pos, seq, virtual=False):
    """our buy is in block `seq` (the dry run: its planned block): the tokens it got, from the pool as the feed shows it at that
    point (exact to 1e-15 against the seven live fills), and, live, the pool moved by it"""
    pos["buy_seq"] = seq; p = state["armed"].get(pos["pid"])
    if p is not None:
        pos["feed_tokens"] = v4math.buy_out_int(int(p["sp"]), p["liq"], pos["stake"], p["fee"])
        if not virtual:
            apply_buy(p, pos["stake"])
    log({"ev": "buy_seen", "pid": pos["pid"], "seq": seq, "offset": seq - pos["trig_seq"], "feed_tokens": pos["feed_tokens"], "expected_tokens": pos["expected_tokens"], "dry": virtual,
         "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
    if p is not None and pos.get("entry") == "front" and p.get("bot_seq") is not None and not pos["sell_sent"]:   # the bot bought ahead of ours in our own block (small enough to pass our minOut): the pull is 2-4 blocks away
        send_sell("the bot's buy landed ahead of ours in the same block: nothing is coming behind ours, out before the pull", pos)


def take_profit(pos, p):
    """a buy landed behind ours: what the sell gets now, after the fee and the trade's gas. The crowd buys that were already on
    their way when we bought are the whole profit (the operator stops its crowd and pulls once it sees us), so the first one that
    pays TAKE_PROFIT is the exit: every block after it is only the pull's risk."""
    stake = pos["stake"]
    sp = p["sp"] if not pos["dry"] else v4math.sqrt_after_buy(p["sp"], p["liq"], net_of_fee(stake, p["fee"]))   # the dry run is not in the pool: put our buy in (1/sqrtP adds)
    eth = v4math.sell_out_int(int(sp), p["liq"], pos["feed_tokens"], p["fee"])
    ret = (eth - stake - round_trip_gas_wei()) / stake
    if ret >= pos["tp"]:
        pos["tp_ret"] = round(ret, 4); send_sell(f"take profit: a buy behind ours, the sell prices at {ret:+.1%}")
    return ret


def on_front_buy(p, seq, to, value, h, stale):
    """a buy on a front pool. Before we fire: what others buy ahead of the bot's first buy (with our stake, more than
    FRONT_AHEAD_MAX leaves too little room for its minOut), and a buy the bot's size (it has bought): either makes the pool late. The
    bot's buy itself, quoted at the launch state with minOut FRONT_BOT_MINOUT of that quote: if what sits ahead of it (ours
    included) fails that, it reverts on the chain though the feed shows it, so it does not move the pool and is no take-profit;
    our position, if its buy is in, sells at once (nothing is coming behind it). Otherwise it is the take-profit's moment."""
    pos = state["position"]; ours = pos if pos is not None and pos["pid"] == p["pid"] else None
    bot = to in FRONT_BOT_ROUTERS or value >= FRONT_BOT_MIN_WEI                            # the bot's buy: through its router at any size, or any buy of its usual size
    if bot and p["bot_seq"] is None:
        p["bot_seq"] = seq
        sp = p["sp"]
        if ours is not None and ours["dry"] and ours["buy_seq"] is not None:                # the dry run's buy is not in the pool: put it in
            sp = v4math.sqrt_after_buy(sp, p["liq"], net_of_fee(ours["stake"], p["fee"]))
        q0 = v4math.buy_out_int(p["sqrt_p"], p["liq"], value, p["fee"]); q1 = v4math.buy_out_int(int(sp), p["liq"], value, p["fee"])
        if q1 < q0 * p["fam_cfg"]["bot_minout"]:
            p["buys"] += 1
            log({"ev": "front_bot_reverts", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"], "value": value, "eth_in": p["eth_in"], "quote_ratio": round(q1 / q0, 5) if q0 else None,
                 "ours": ours is not None})
            if p["status"] == "armed":
                p["status"] = "late"; log({"ev": "skip", "why": "front: the bot's buy came (and reverts) before our fire", "pid": p["pid"], "seq": seq})
            if ours is not None and ours["buy_seq"] is not None and not ours["sell_sent"] and not stale:
                send_sell("the bot's buy reverts: too much ETH ahead of it, nothing is coming behind ours", ours)
            return
    apply_buy(p, value); p["eth_in"] += value
    if p["first_buy"] is None and value >= MIN_TRIGGER_WEI:
        p["first_buy"] = seq
        log({"ev": "first_buy", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"], "value": value, "to": to, "fee": p["fee"], "eligible": p["eligible"], "stale": stale, "entry": "front"})
    if p["status"] == "armed" and (bot or p["eth_in"] + p["fam_cfg"]["stake_wei"] > p["fam_cfg"]["ahead_max_wei"]):
        p["status"] = "late"
        log({"ev": "skip", "why": "front: the bot's buy came first" if bot else "front: too much ETH bought ahead of the bot's buy", "pid": p["pid"], "seq": seq,
             "eth_in": p["eth_in"]})
    if ours is not None and ours["buy_seq"] is not None and not ours["sell_sent"] and ours["feed_tokens"] and not stale:
        if to in FRONT_BOT_ROUTERS:
            ours["bot_exit"] = True                                                        # whichever rule sends the sell on this buy, the exit is into the bot's buy (the streak's reset)
        ret = take_profit(ours, p)
        if not ours["sell_sent"] and (to in FRONT_BOT_ROUTERS or (FRONT_SELL_ON_WEI and value >= FRONT_SELL_ON_WEI)):   # the bot's buy (its router, any size), or, if set, any buy of FRONT_SELL_ON_ETH: out now, not at the deadline
            ours["tp_ret"] = round(ret, 4)
            who = f"the bot's buy behind ours ({value / 1e18:.5f} ETH)" if to in FRONT_BOT_ROUTERS else f"a real-size buy behind ours ({value / 1e18:.5f} ETH, not through the bot's router)"
            send_sell(who + f": out before the pull, the sell prices at {ret:+.1%}", ours)


def on_buy(p, seq, to, value, h, stale, seen_at):
    """a transaction carrying p's token with ETH as its value: a buy. It moves the pool; the first real-size one is the trigger;
    one behind our own buy is the take-profit's moment."""
    if p.get("entry") == "front":
        on_front_buy(p, seq, to, value, h, stale); return
    apply_buy(p, value)
    if value < MIN_TRIGGER_WEI:
        return
    if p["first_buy"] is None:
        p["first_buy"] = seq
        log({"ev": "first_buy", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"], "value": value, "to": to, "fee": p["fee"], "eligible": p["eligible"], "stale": stale,
             "ms_since_arm": round(1000 * (mono() - p["armed_at"]), 1)})
        if p["status"] == "armed" and p.get("entry") == "seat":                         # the burst came before our seat: no trade on this pool
            p["status"] = "late"
        elif p["status"] == "armed" and not stale:                                     # a stale first buy is late: no trade on this pool, not on its next buy either
            if BUY_DELAY_BLOCKS > 0:
                p["status"] = "delayed"; p["trig"] = (seq, value, h)
            else:
                fire(p, seq, state["ts"], value, h, seen_at)
    elif p["status"] == "delayed":                                                     # the crowd's next buy came before our delayed one: we would sit behind it
        p["status"] = "skipped"; log({"ev": "skip", "why": "a real buy landed between the trigger and our delayed buy", "pid": p["pid"], "seq": seq, "trig_seq": p["trig"][0]})
        return
    pos = state["position"]
    if pos is not None and pos["pid"] == p["pid"] and pos["buy_seq"] is not None and not pos["sell_sent"] and pos["feed_tokens"] and not stale:
        take_profit(pos, p)


def ingest(raw):
    """one feed frame: every block in it, every transaction; the launches, every buy on an armed pool (the trigger, the pool's
    price, the take-profit), our own buy, the sell's deadline"""
    try:
        frame = json.loads(raw)
    except Exception:
        return
    wall = time.time()
    for m in frame.get("messages", []):
        seq = m.get("sequenceNumber"); inner = (m.get("message") or {}).get("message") or {}; hdr = inner.get("header") or {}
        if seq is None or hdr.get("kind") != 3:
            continue
        with lock:
            if seq <= state["seq"]:
                continue
            state["seq"] = seq; state["ts"] = hdr.get("timestamp", 0); state["blocks"] += 1
            stale = wall - state["ts"] > STALE_S
            if stale:
                state["stale_blocks"] += 1
            seen_at = mono(); txs = decode_batch(inner.get("l2Msg", "")); state["txs"] = state.get("txs", 0) + len(txs)
            pos = state["position"]
            if pos is not None and pos["dry"] and pos["buy_seq"] is None and seq >= pos["plan_buy_seq"]:
                our_buy_landed(pos, seq, virtual=True)                                 # the dry run's buy at the head of its planned block
            for t in txs:
                try:
                    ingest_tx(t, seq, stale, seen_at)
                except Exception:                                                      # one bad transaction never costs the rest of the block
                    if seq - state.get("tx_alarm_seq", -10**9) >= 600:
                        state["tx_alarm_seq"] = seq
                        log({"ev": "alarm", "what": "a transaction failed to process and was skipped (at most one such alarm a minute)", "seq": seq, "trace": traceback.format_exc()[-600:]})
            for p in list(state["armed"].values()):                                    # BUY_DELAY_BLOCKS: fire once the delay's blocks passed with no other real buy
                if p["status"] == "delayed" and seq >= p["trig"][0] + BUY_DELAY_BLOCKS:
                    p["status"] = "armed" if not stale else "skipped"
                    if not stale:
                        fire(p, p["trig"][0], state["ts"], p["trig"][1], p["trig"][2], seen_at, fire_seq=seq)
                elif p.get("entry") == "front" and p["status"] == "armed" and seq >= p["launch_seq"] + p["fam_cfg"]["fire_at"]:   # buys ahead of ours make it late (on_front_buy), not any buy
                    if stale or seq > p["launch_seq"] + p["fam_cfg"]["fire_at"] + p["fam_cfg"]["fire_max"]:   # too late to land ahead of the bot's buy (its window is the family's)
                        p["status"] = "late"; log({"ev": "skip", "why": "front: too late to land ahead of the bot's first buy", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"]})
                    else:
                        fire(p, seq, state["ts"], 0, p["tx"], seen_at)
                elif p.get("entry") == "seat" and p["status"] == "armed" and p["first_buy"] is None and seq >= p["launch_seq"] + SEAT_FIRE_AT:
                    if stale or seq > p["launch_seq"] + SEAT_FIRE_AT + 1:                     # armed too late to land ahead of the burst
                        p["status"] = "late"; log({"ev": "skip", "why": "seat: armed too late to land ahead of the burst", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"]})
                    else:
                        fire(p, seq, state["ts"], 0, p["tx"], seen_at)                          # the seat's trigger is the launch, its block the fire block
            pos = state["position"]
            if pos is not None and not pos["sell_sent"]:
                if pos["buy_seq"] is not None and seq >= pos["buy_seq"] + pos["send_after"]:
                    send_sell("deadline: no buy behind ours paid TAKE_PROFIT; out before the operator's reaction")
                elif pos["buy_seq"] is None and seq >= pos["plan_buy_seq"] + pos["send_after"]:
                    send_sell("deadline from the planned buy block (buy not seen in the feed)")
            if state["blocks"] % 600 == 0:                                   # about once a minute: alive, decoding, and what it has seen
                prune(seq); log({"ev": "flow", "seq": seq, "ts": state["ts"], "lag_s": round(wall - state["ts"], 1), "blocks": state["blocks"], "txs": state["txs"], "launches": state["launches"], "fires": state["fires"], "armed": len(state["armed"]),
                                 "stale_blocks": state["stale_blocks"], "trades_today": state["trades_today"], "front_today": state["front_today"], "pnl_today_usd": round(state["pnl_today_usd"], 2),
                                 "front_pnl_today_usd": round(state["front_pnl_today_usd"], 2), "relay_eth": state["relay_wei"] / 1e18 if state["relay_wei"] is not None else None,
                                 "halted": state["halted"], "front_halted": state["front_halted"], "follow_halted": state["follow_halted"], "fam_halted": state["fam_halted"]})


def ingest_tx(t, seq, stale, seen_at):
    """one signed transaction of block `seq` (under the lock)"""
    tx = parse_tx(t)
    if tx is None:
        return
    to, value, data, nonce, h = tx
    pos = state["position"]
    if pos is not None and pos["buy_hash"] == h and pos["buy_seq"] is None:
        our_buy_landed(pos, seq); return
    fam = FRONT_FAMILIES.get(value) if FRONT and to == POSITION_MANAGER and len(data) == FRONT_CALLDATA_LEN and data[:4].hex() == SEL_MULTICALL else None
    if fam is not None:
        if not stale:
            log({"ev": "launch", "tx": h, "seq": seq, "to": to, "family": "front", "fam": fam["name"]}); arm_front(data, h, seq, seen_at, fam)
        return
    if to in LAUNCHERS or (LAUNCH_SELECTORS and data[:4].hex() in LAUNCH_SELECTORS):
        if not stale:
            log({"ev": "launch", "tx": h, "seq": seq, "to": to})
            threading.Thread(target=arm_launch_thread, args=(h, seq, state["ts"], seen_at, to), daemon=True).start()
            state["arming"].add(h)                                                     # once started (its discard waits for the lock we hold): a thread that never ran leaves nothing behind
        return
    if value == 0 or len(data) < 20:
        if value == 0 and len(data) >= 36 and state["delayed"] and (to in FRONT_BOT_ROUTERS or to == POSITION_MANAGER or to == POOL_MANAGER[2:]):
            for q in list(state["armed"].values()):                                    # a front pool waiting for its fire offset: a pull-shaped call carrying its token ends it
                if q.get("entry") == "front" and q["status"] == "armed" and q["fam_cfg"]["fire_at"] and q["token_bytes"] in data:
                    q["status"] = "late"; log({"ev": "skip", "why": "front: a liquidity call on the pool before our fire (a pull)", "pid": q["pid"], "seq": seq, "to": to, "offset": seq - q["launch_seq"]})
        return
    state["recent"].append((seq, to, value, data))
    for pid, p in list(state["armed"].items()):
        if p["token_bytes"] in data and to != p["token"]:
            on_buy(p, seq, to, value, h, stale, seen_at); break


async def feed_loop():
    import websockets
    backoff = 0.2
    while True:
        try:
            async with websockets.connect(FEED_URL, open_timeout=10, max_size=None, ping_interval=10, ping_timeout=5, max_queue=4, compression=FEED_COMPRESSION,
                                          **({"user_agent_header": FEED_USER_AGENT} if FEED_USER_AGENT else {}), **({"additional_headers": FEED_HEADERS} if FEED_HEADERS else {})) as ws:
                state["connected"] = True; log({"ev": "feed_connected", "url": FEED_URL}); backoff = 0.2
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        log({"ev": "feed_stall", "seq": state["seq"]}); break
                    ingest(raw)
        except Exception as e:
            log({"ev": "feed_error", "err": str(e)[:200]})
            code = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "status_code", None)   # websockets 14+ / the older client
            if code in (403, 429, 503):                                                # refused by the server: retrying every 5 s only keeps the address flagged
                backoff = max(backoff, 15.0)
        state["connected"] = False
        await asyncio.sleep(backoff); backoff = min(60.0 if backoff >= 15.0 else 5.0, backoff * 2)


# ---------------------------------------------------------------- start
def checks():
    load_halt()
    chain = int(rpc("eth_chainId", []), 16)
    if chain != CHAIN_ID:
        raise SystemExit(f"RPC_URL is chain {chain}, not {CHAIN_ID}")
    b = rpc("eth_getBlockByNumber", ["latest", False]); state["base_fee"] = int(b["baseFeePerGas"], 16); state["fee_at"] = mono()
    info = {"chain": chain, "head": int(b["number"], 16), "base_fee_gwei": state["base_fee"] / 1e9}
    if RELAY:
        code = rpc("eth_getCode", [h0x(RELAY), "latest"]); owner = rpc("eth_call", [{"to": h0x(RELAY), "data": "0x" + SEL_OWNER}, "latest"]); pm = rpc("eth_call", [{"to": h0x(RELAY), "data": "0x" + SEL_PM}, "latest"])
        bal = int(rpc("eth_getBalance", [h0x(RELAY), "latest"]), 16)
        info.update({"relay_code_bytes": len(code) // 2 - 1, "relay_owner": "0x" + owner[-40:], "relay_pm": "0x" + pm[-40:], "relay_eth": bal / 1e18})
        if len(code) <= 2:
            raise SystemExit("RELAY has no code")
        if ("0x" + pm[-40:]).lower() != POOL_MANAGER:
            raise SystemExit(f"the relay's PoolManager is {pm[-40:]}, not {POOL_MANAGER}")
        if WALLET and ("0x" + owner[-40:]).lower() != h0x(WALLET):
            raise SystemExit(f"the relay's owner is 0x{owner[-40:]}, WALLET is {WALLET}")
        if not DRY_RUN and bal < STAKE_WEI:
            raise SystemExit(f"the relay holds {bal / 1e18:.6f} ETH, under the stake {STAKE_ETH}")
        state["relay_wei"] = bal
        live_stakes = [FRONT_STAKE_WEI if f["value_wei"] == FRONT_VALUE_WEI else f["stake_wei"] for f in FRONT_FAMILIES.values() if not f["dry_run"]]   # the base family's stake is FRONT_STAKE_WEI
        if FRONT and not DRY_RUN and not FRONT_DRY_RUN and live_stakes and bal < min(live_stakes):   # front's own shortfall: front off, follow runs
            front_off(f"the relay holds {bal / 1e18:.6f} ETH, under the smallest live front stake {min(live_stakes) / 1e18:g}")
    if FRONT and FRONT_STAKE_WEI <= 0:
        front_off(f"FRONT_STAKE_ETH is {FRONT_STAKE_ETH}: it must be above 0")
    if FRONT and FRONT_FAMILY_ERROR and not FRONT_FAMILIES:
        front_off(FRONT_FAMILY_ERROR)
    elif FRONT and FRONT_FAMILY_ERROR:
        log({"ev": "alarm", "what": FRONT_FAMILY_ERROR})
    elif FRONT and not FRONT_FAMILIES:
        front_off("no front family: FRONT_VALUE_WEI is 0 and FRONT_FAMILIES is empty")
    if WALLET:
        state["nonce"] = int(rpc("eth_getTransactionCount", [h0x(WALLET), "pending"]), 16); info["wallet_nonce"] = state["nonce"]
        info["wallet_eth"] = int(rpc("eth_getBalance", [h0x(WALLET), "latest"]), 16) / 1e18
    if not DRY_RUN:
        global SIGNER, SENDER
        from eth_account import Account
        SIGNER = Account.from_key(os.environ["PRIVATE_KEY"])
        if SIGNER.address.lower() != h0x(WALLET):
            raise SystemExit(f"PRIVATE_KEY is for {SIGNER.address}, WALLET is {WALLET}")
        if not RELAY:
            raise SystemExit("RELAY is required when DRY_RUN=0")
        SENDER = Sender(SEQ_URL)
    return info


def main():
    roll_day(); restored = restore_today(); info = checks()
    log({"ev": "start", "release": RELEASE, "dry_run": DRY_RUN, "launchers": sorted(LAUNCHERS), "relay": RELAY, "wallet": WALLET, "stake_eth": STAKE_ETH, "min_trigger_eth": MIN_TRIGGER_ETH,
         "fee_ppm": [FEE_MIN_PPM, FEE_MAX_PPM], "min_liquidity": MIN_LIQUIDITY, "trigger_max_blocks": TRIGGER_MAX_BLOCKS, "buy_slip": BUY_SLIP, "buy_deadline_s": BUY_DEADLINE_S, "gas_headroom": GAS_HEADROOM,
         "hold_blocks": HOLD_BLOCKS, "sell_lead_blocks": SELL_LEAD_BLOCKS, "take_profit": TAKE_PROFIT, "buy_delay_blocks": BUY_DELAY_BLOCKS,
         "entry": ENTRY, "seat_fire_at": SEAT_FIRE_AT, "launch_selectors": sorted(LAUNCH_SELECTORS), "launcher_code_hashes": len(LAUNCHER_CODE_HASHES),
         "front": FRONT, "front_dry_run": FRONT_DRY_RUN, "front_stake_eth": FRONT_STAKE_ETH, "front_take_profit": FRONT_TAKE_PROFIT, "front_hold_blocks": FRONT_HOLD_BLOCKS,
         "front_fire_max": FRONT_FIRE_MAX, "front_max_per_day": FRONT_MAX_PER_DAY, "front_value_wei": FRONT_VALUE_WEI, "front_halted": state["front_halted"],
         "front_daily_stop_usd": FRONT_DAILY_STOP_USD, "front_pin": FRONT_PIN, "front_fee": FRONT_FEE, "front_tick_spacing": FRONT_TICK_SPACING, "front_sqrt_p": FRONT_SQRT_P, "front_liq": FRONT_LIQ,
         "front_ahead_max_eth": FRONT_AHEAD_MAX_ETH, "front_sell_on_eth": FRONT_SELL_ON_ETH, "front_bot_min_eth": FRONT_BOT_MIN_ETH, "front_bot_minout": FRONT_BOT_MINOUT, "front_bot_routers": sorted(FRONT_BOT_ROUTERS),
         "front_families": [{"name": f["name"], "value_eth": f["value_wei"] / 1e18, "fee": f["fee"], "tick_spacing": f["tick_spacing"], "bot_minout": f["bot_minout"], "ahead_max_eth": f["ahead_max_wei"] / 1e18,
                             "take_profit": f["take_profit"], "hold_blocks": f["hold_blocks"], "stake_eth": f["stake_wei"] / 1e18, "dry_run": f["dry_run"], "pin": f["pin"], "fire_at": f["fire_at"],
                             "fire_max": f["fire_max"]} for f in FRONT_FAMILIES.values()],
         "front_nonbot_halt": FRONT_NONBOT_HALT, "front_nonbot_min_ret": FRONT_NONBOT_MIN_RET, "front_nonbot_streak": state["front_nonbot_streak"], "fam_halted": state["fam_halted"],
         "front_family_error": FRONT_FAMILY_ERROR,
         "halted": state["halted"], "halt_file": HALT_FILE, "follow_halted": state["follow_halted"], "follow_halt_file": FOLLOW_HALT_FILE, "follow_near_miss_blocks": FOLLOW_NEAR_MISS_BLOCKS, "feed_headers": sorted(FEED_HEADERS), "today_restored": {k: round(v, 3) for k, v in restored.items()}, "sell_fallback_s": SELL_FALLBACK_S, "max_trades_per_day": MAX_TRADES_PER_DAY, "daily_stop_usd": DAILY_STOP_USD, "feed": FEED_URL, "seq": SEQ_URL, "rpc": RPC_URL, **info})
    signal.signal(signal.SIGTERM, on_stop)
    threading.Thread(target=watchdog, daemon=True).start(); threading.Thread(target=fee_loop, daemon=True).start()
    try:
        asyncio.run(feed_loop())
    except KeyboardInterrupt:
        pass
    except Exception:
        log({"ev": "alarm", "what": "engine crashed", "trace": traceback.format_exc()[-800:]}); raise


if __name__ == "__main__":
    main()
