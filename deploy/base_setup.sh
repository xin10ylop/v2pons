#!/bin/bash
# base_setup.sh: the Base engine (src/base_engine.py, docs/BASE.md) on the box, beside flip-engine and flip-bnb and touching nothing of either:
# the shared venv (/opt/flip-venv) with what the engine needs (websockets, brotli for the Flashblocks stream, eth-account, rlp, eth-utils,
# coincurve; py-solc-x for base_relay_sim.py), its own settings (/etc/flip/base.env, mode 600, written from the template below when it is
# not there: every setting of docs/BASE.md section 5 with its default; no key in it), its own log (/var/log/flip/base.jsonl, rotated daily)
# and its own service (flip-base, deploy/flip-base.service, with this clone's path). Idempotent: run it again after a git pull to pick up a
# changed unit; an existing /etc/flip/base.env is never rewritten (the settings it lacks are listed: the code's default applies to them).
# The first install starts the service as a DRY RUN (BASE_DRY_RUN=1). A later run restarts it only while the env file says BASE_DRY_RUN=1:
# a live engine is left running, and you restart it yourself when no position is open (RUNBOOK 4l step 9).
#
#     cd ~/v2pons && sudo bash deploy/base_setup.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV=/etc/flip/base.env
[ "$(id -u)" = 0 ] || { echo "run it with sudo: cd ~/v2pons && sudo bash deploy/base_setup.sh"; exit 1; }
[ -f "$REPO/src/base_engine.py" ] || { echo "$REPO/src/base_engine.py is missing: git pull first (RUNBOOK 4l step 1)"; exit 1; }
apt-get install -y -q python3-venv >/dev/null 2>&1 || true
[ -x /opt/flip-venv/bin/python3 ] || python3 -m venv /opt/flip-venv
/opt/flip-venv/bin/pip install -q --upgrade pip >/dev/null
/opt/flip-venv/bin/pip install -q websockets brotli rlp eth-account eth-utils coincurve py-solc-x      # py-solc-x only for base_relay_sim.py
/opt/flip-venv/bin/python3 -c 'import websockets, brotli, rlp, eth_account, eth_utils' || { echo "the venv lacks a package (above): stop and paste this"; exit 1; }
mkdir -p /etc/flip /var/log/flip; chmod 700 /etc/flip
if [ ! -f "$ENV" ]; then
OLD_UMASK=$(umask); umask 077
cat > "$ENV" <<'EOF'
# the Base engine's settings (src/base_engine.py; docs/BASE.md section 5 has each one). One setting a line, comments on their own lines
# only (systemd reads this file: a comment after a value would become part of it). Restart after a change: sudo systemctl restart flip-base
# No key belongs here: the wallet's key is /etc/flip/base.key (deploy/base_wallet.py).

# ---- feeds and keys
# 1 = the dry run (nothing signed or sent); 0 = live (RUNBOOK 4l step 6: needs BASE_WALLET, the key file and BASE_RELAY)
BASE_DRY_RUN=1
# the JSON log, one line per event (docs/BASE.md section 6); HALTED.base and base_positions.json go beside it
BASE_LOG_PATH=/var/log/flip/base.jsonl
# the confirmed feed: newHeads and the PoolManager's logs over one websocket
BASE_WS_URL=wss://base-rpc.publicnode.com
# reads (receipts, code, transactions, balances), and the catch-up eth_getLogs after the websocket fails (publicnode: mainnet.base.org
# answers eth_getLogs with HTTP 429)
BASE_RPC_URL=https://base-rpc.publicnode.com
# the second read endpoint, asked once when BASE_RPC_URL fails
BASE_READ_ALT_URL=https://mainnet.base.org
# where transactions go, every one at once (comma-separated, no spaces)
BASE_SEND_URLS=https://mainnet-sequencer.base.org,https://mainnet.base.org
# the Flashblocks stream (pending transactions, 200 ms ahead of the block); 0 = off (slower, still correct)
BASE_FLASH_URL=wss://mainnet.flashblocks.base.org/ws
# the line's own wallet (written by deploy/base_wallet.py); empty in the dry run
BASE_WALLET=
# the wallet's key file (mode 600, owned by root; never printed)
BASE_KEY_FILE=/etc/flip/base.key
# the FlipRelay on Base (written by deploy/base_relay_deploy.py --write-env); empty in the dry run
BASE_RELAY=
# Uniswap v4's PoolManager on Base
BASE_POOL_MANAGER=0x498581ff718922c3f8e6a244956af099b2652b2b
# the halt file: when it exists no new buy is made (an open position is still sold); it holds across restarts
BASE_HALT_FILE=/var/log/flip/HALTED.base
# seconds without a websocket message before the engine polls BASE_RPC_URL and reconnects
BASE_WS_SILENT_S=10

# ---- the line's fingerprint (the operator's launch, measured on its five Base pools of Oct 14)
# the launch transactions' selectors (to the per-launch launcher), comma-separated, each with an optional /calldata length in bytes
# (c3e0ff3d, 260 B, to 19:42 UTC Oct 14; 99dfa5c4, 868-1348 B, since: a bare selector takes any length)
BASE_LAUNCH_SELECTOR=c3e0ff3d/260,99dfa5c4
# the launchers' code hash prefixes, comma-separated, any of (225f9af97d88 the first launcher, 53959585f666 from 19:42 UTC Oct 14).
# NOT aee87105d146 (from 07:16 UTC Oct 15): its hook lets only the operator's wallets sell; one stake was lost to it at 08:27 UTC.
# A new launcher goes here only after base_relay_sim.py sells on one of its pools (--block between the add and the pull).
BASE_LAUNCHER_CODEHASH_PREFIX=225f9af97d88,53959585f666
# the hook's runtime code size in bytes, comma-separated, any of (8951 the line's hook; the whitelist hook is 8957); 0 = any
BASE_HOOK_CODE_SIZES=8951
# the token's runtime code hash(es), comma-separated (the 2.433 token, byte for byte the Robinhood one)
BASE_TOKEN_CODEHASHES=0x63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb
# the pool's fee (5000 = 0.5%)
BASE_FEE=5000
# the pool's tick spacing
BASE_TICK_SPACING=100
# the hook's address flags (low 14 bits; 0x80 = beforeSwap); -1 = any hook, 0 = no hook
BASE_HOOK_FLAGS=0x80
# the liquidity add's selector (the launch wallet to the hook, at L+3)
BASE_ADD_SELECTOR=2346bb56
# the pull's selector (the launch wallet to the hook)
BASE_PULL_SELECTOR=f2f230a8
# the bot's buy contract(s): a pending transaction to it carrying our token is the bot's buy (the sell goes at once)
BASE_BOT_ROUTERS=0x987d5db84d105c1f49391af409cc34c6050fb1d0
# the bot's buy selector(s) on that contract (comma-separated); a call with another selector or no value is not a buy
BASE_BOT_SELECTORS=27f7e6ee
# Swap senders that mark the bot's buy; empty = off (the Swap's sender is the Universal Router for every swap, the bot's included)
BASE_BOT_SENDERS=
# the smallest pool (the add's ETH) traded: the 0.133 ETH test pools are skipped
BASE_MIN_POOL_ETH=1.0
# an armed launch with no add within this many blocks expires
BASE_ADD_MAX_BLOCKS=10

# ---- the trade
# the stake in ETH (0.002 = about $5); never above BASE_STAKE_CAP_ETH
BASE_STAKE_ETH=0.002
# the stake's ceiling: the engine buys min(BASE_STAKE_ETH, this); raise it only on your own decision (RUNBOOK 4l step 8)
BASE_STAKE_CAP_ETH=0.005
# the buy's minOut under the exact v4 output
BASE_BUY_SLIP=0.03
# the buy's deadline in seconds
BASE_BUY_DEADLINE_S=20
# the buy is aimed at the add's block + this many blocks (3: two blocks before the bot's first buy at add + 5; 0 = the add's own block)
BASE_FIRE_DELAY_BLOCKS=3
# with no delay: the fire is refused once the head is this many blocks past the add's block
BASE_FIRE_MAX=2
# the deadline exit: sold at our buy's block + this many blocks if nothing sold it before
BASE_HOLD_BLOCKS=6
# a confirmed buy behind ours sells when it values our tokens at the stake x (1 + this) plus the gas
BASE_TAKE_PROFIT=0.01
# the sell's minOut under the tracked price (0 at the deadline)
BASE_SELL_SLIP=0.05
# the sell's deadline in seconds
BASE_SELL_DEADLINE_S=30
# a pull this many blocks or fewer after our buy halts the line even when our sell landed first
BASE_NEAR_MISS_BLOCKS=3
# a pull this many blocks or fewer after our sell halts the line too (the operator is reacting: 14:31 UTC Oct 14, a pull 2 blocks behind our sell)
BASE_NEAR_MISS_SELL_BLOCKS=3
# this many live trades in a row under BASE_NONBOT_MIN_RET halt the line
BASE_NONBOT_HALT=5
# the return under which a live trade counts toward BASE_NONBOT_HALT
BASE_NONBOT_MIN_RET=0.02
# at most this many buys a UTC day
BASE_MAX_PER_DAY=400
# losses in dollars that stop new buys for the rest of the UTC day
BASE_DAILY_STOP_USD=10
# dollars per ETH, for the dollar figures
BASE_ETH_USD=2570
# the priority fee in gwei (Base orders transactions by it within each 200 ms Flashblock; the bot pays 0.0011; at 0.01 the round trip's gas
# is about 0.2% of a 0.002 ETH stake, at 0.05 about 0.9%)
BASE_PRIO_GWEI=0.01
# the most maxFeePerGas may be, in gwei (2 x the base fee + the priority, capped here)
BASE_MAX_FEE_GWEI=0.5
# the buy's gas limit
BASE_BUY_GAS=400000
# the sell's gas limit
BASE_SELL_GAS=400000
# the relay must hold the stake plus this much ETH to fire
BASE_RELAY_MARGIN_ETH=0.0005
EOF
umask "$OLD_UMASK"
chmod 600 "$ENV"
echo "wrote $ENV (BASE_DRY_RUN=1)"
else
missing=$(for k in $(grep -o '^BASE_[A-Z_]*=' "$REPO/deploy/base_setup.sh" | tr -d '='); do grep -q "^$k=" "$ENV" || echo "$k"; done | tr '\n' ' ')
echo "$ENV exists: not rewritten."
[ -z "$missing" ] || echo "not in it (the engine uses the default of docs/BASE.md section 5 for each): $missing"
fi
echo '/var/log/flip/base.jsonl { daily rotate 30 missingok notifempty compress delaycompress copytruncate }' > /etc/logrotate.d/flip-base
sed "s|/home/ubuntu/v2pons|$REPO|g" "$REPO/deploy/flip-base.service" > /etc/systemd/system/flip-base.service
systemctl daemon-reload
systemctl enable flip-base >/dev/null 2>&1 || true
DRY=$(grep '^BASE_DRY_RUN=' "$ENV" | tail -1 || true)                                     # systemd takes the last line of a name
if [ -z "$DRY" ] || [ "$DRY" = "BASE_DRY_RUN=1" ]; then
    systemctl restart flip-base
    sleep 20
    echo "flip-base: $(systemctl is-active flip-base); its last start line:"
    /opt/flip-venv/bin/python3 - "$(grep '^BASE_LOG_PATH=' "$ENV" | tail -1 | cut -d= -f2- || true)" <<'PY'
import json, sys
log = sys.argv[1] or "/var/log/flip/base.jsonl"; last = None
try:
    for line in open(log):
        if '"start"' in line:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("ev") == "start":
                last = e
except OSError:
    pass
print({k: last.get(k) for k in ("release", "dry", "head")} if last else "(no start line yet in %s: journalctl -u flip-base -n 20)" % log)
PY
else
    echo "$ENV says LIVE (its last BASE_DRY_RUN= line is not 1): the unit is updated, the service is not restarted;"
    echo "restart it yourself when base_results.py shows no open position: sudo systemctl restart flip-base"
fi
