#!/bin/bash
# base_v2_setup.sh: the Base V2 line's engine (src/base_v2_engine.py, docs/BASE_V2.md) on the box, beside flip-engine and flip-base and
# touching nothing of either: the shared venv (/opt/flip-venv) with what the engine needs (websockets, brotli for the Flashblocks stream,
# eth-account, rlp, eth-utils, coincurve) and py-solc-x with solc 0.8.26 (deploy/base_v2_sim.py, base_v2_relay_sim.py and
# base_v2_relay_deploy.py compile the harnesses), its own settings (/etc/flip/base_v2.env, mode 600: every BASE_V2_* setting of docs/BASE_V2.md
# section 5 with its default and a one-line comment; no key in it), its own log (/var/log/flip/base_v2.jsonl, rotated daily), the roster's
# daily cron (deploy/base_v2_roster.py at 00:20 UTC, /etc/cron.d/flip-base-v2-roster) and its own service (flip-base-v2,
# deploy/flip-base-v2.service, with this clone's path).
# The env file: an existing /etc/flip/base_v2.env is KEPT and completed, never replaced: every value in it stays (yours win over the
# template's defaults), the line BASE_WALLET= that `base_wallet.py create /etc/flip/base_v2.key /etc/flip/base_v2.env` wrote becomes
# BASE_V2_WALLET=, BASE_V2_KEY_FILE is set to /etc/flip/base_v2.key when it is not set, every setting the file lacks is added with its default
# and its comment, and a line that is not a setting of section 5 is kept at the end. Idempotent: run it again after a git pull to pick up a
# changed unit or template. The first install starts the service as a DRY RUN (BASE_V2_DRY_RUN=1). A later run restarts it only while the env
# file says BASE_V2_DRY_RUN=1: a live engine is left running, and you restart it yourself when no position is open (RUNBOOK 4m step 11).
#
#     cd ~/v2pons && sudo bash deploy/base_v2_setup.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV=/etc/flip/base_v2.env
[ "$(id -u)" = 0 ] || { echo "run it with sudo: cd ~/v2pons && sudo bash deploy/base_v2_setup.sh"; exit 1; }
[ -f "$REPO/src/base_v2_engine.py" ] || { echo "$REPO/src/base_v2_engine.py is missing: git pull first (RUNBOOK 4m step 1)"; exit 1; }
apt-get install -y -q python3-venv >/dev/null 2>&1 || true
[ -x /opt/flip-venv/bin/python3 ] || python3 -m venv /opt/flip-venv
/opt/flip-venv/bin/pip install -q --upgrade pip >/dev/null
/opt/flip-venv/bin/pip install -q websockets brotli rlp eth-account eth-utils coincurve py-solc-x
/opt/flip-venv/bin/python3 -c 'import websockets, brotli, rlp, eth_account, eth_utils, solcx' || { echo "the venv lacks a package (above): stop and paste this"; exit 1; }
# solc 0.8.26 into root's ~/.solcx (about 10 MB from github): the exit test and the relay scripts compile with it; the engine itself does not
# need it. A failed download is said, not fatal: RUNBOOK 4m step 3 installs it by hand.
/opt/flip-venv/bin/python3 - <<'PY' || echo "solc 0.8.26 was not installed (no way to github?): RUNBOOK 4m step 3 does it by hand"
import solcx
have = lambda: "0.8.26" in [str(v) for v in solcx.get_installed_solc_versions()]
if not have():
    solcx.install_solc("0.8.26", show_progress=False)
print("solc 0.8.26: " + ("installed" if have() else "MISSING"))
PY
mkdir -p /etc/flip /var/log/flip; chmod 700 /etc/flip
TPL=$(mktemp /etc/flip/.base_v2.tpl.XXXXXX); chmod 600 "$TPL"; trap 'rm -f "$TPL"' EXIT
cat > "$TPL" <<'EOF_TPL'
# the Base V2 line's settings (src/base_v2_engine.py; docs/BASE_V2.md section 5 has each one with its bound). One setting a line, comments
# on their own lines only (systemd reads this file: a comment after a value would become part of it). Restart after a change:
# sudo systemctl restart flip-base-v2. No key belongs here: the wallet's key is /etc/flip/base_v2.key (deploy/base_wallet.py create).

# ---- feeds and keys
# 1 = the dry run (nothing signed or sent; the guard runs); 0 = live (RUNBOOK 4m step 9: needs the wallet, the key file, the relay, the roster)
BASE_V2_DRY_RUN=1
# the JSON log, one line per event (docs/BASE_V2.md section 6); HALTED.base_v2 and base_v2_positions.json go beside it
BASE_V2_LOG_PATH=/var/log/flip/base_v2.jsonl
# the confirmed feed: newHeads, the factory's PairCreated and the followed pairs' logs over one websocket
BASE_V2_WS_URL=wss://base-rpc.publicnode.com
# reads (receipts, transactions, balances, the nonce) and the catch-up eth_getLogs after the websocket fails
BASE_V2_RPC_URL=https://base-rpc.publicnode.com
# the second read endpoint, asked once when BASE_V2_RPC_URL fails, and the exit test's second endpoint; 0 = none
BASE_V2_READ_ALT_URL=https://mainnet.base.org
# where transactions go, every one at once (comma-separated, no spaces)
BASE_V2_SEND_URLS=https://mainnet-sequencer.base.org,https://mainnet.base.org
# the Flashblocks stream (pending transactions, up to 1.8 s ahead of the block); 0 = off (slower, still correct)
BASE_V2_FLASH_URL=wss://mainnet.flashblocks.base.org/ws
# the archive endpoint for eth_getCode, totalSupply() and the exit test's eth_call with state overrides (single requests); empty = the
# engine's default of docs/BASE_V2.md section 5 (a gateway whose key sits in its URL: only its host is ever logged)
BASE_V2_ARCHIVE_URL=
# the endpoint that takes the `pending` tag; used only with BASE_V2_BACKRUN=1
BASE_V2_PENDING_URL=https://mainnet.base.org
# the line's own wallet (base_wallet.py create /etc/flip/base_v2.key /etc/flip/base_v2.env writes BASE_WALLET=, this setup makes it this line)
BASE_V2_WALLET=
# the wallet's key file (mode 600, owned by root; never printed; flock'ed by the engine while live)
BASE_V2_KEY_FILE=/etc/flip/base_v2.key
# the FlipRelayV2 on Base (written by deploy/base_v2_relay_deploy.py --write-env); empty in the dry run
BASE_V2_RELAY=
# Uniswap V2's factory on Base (PairCreated)
BASE_V2_FACTORY=0x8909dc15e40173ff4699343b6eb8132c65e18ec6
# Uniswap V2's router02 on Base (the creation's addLiquidityETH, the fleet's buys, our relay's swaps)
BASE_V2_ROUTER=0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24
# WETH on Base
BASE_V2_WETH=0x4200000000000000000000000000000000000006
# the halt file: when it exists no new buy is made (an open position is still sold); it holds across restarts
BASE_V2_HALT_FILE=/var/log/flip/HALTED.base_v2
# the fleet roster ({"built", "wallets"}, deploy/base_v2_roster.py daily); read at the start and on every change; a live start needs it
BASE_V2_ROSTER_FILE=/etc/flip/base_v2_roster.json
# seconds without a websocket message before the engine polls BASE_V2_RPC_URL and reconnects
BASE_V2_WS_SILENT_S=10

# ---- the line's fingerprint (measured Oct 15-20 on 749 pairs; docs/BASE_V2.md section 2)
# the creation's selector on the router (addLiquidityETH)
BASE_V2_CREATE_SELECTOR=f305d719
# the pull's selector on the router (removeLiquidityETH)
BASE_V2_PULL_SELECTOR=02751cec
# the creator's nonce at the creation (nonce 0 the token's CREATE, 1 the approve, 2 the creation)
BASE_V2_CREATOR_NONCE=2
# the token's runtime code size(s) in bytes, comma-separated; 0 = any
BASE_V2_TOKEN_CODE_SIZES=3553
# the Mint's token side must be at least this share of totalSupply()
BASE_V2_MIN_SUPPLY_IN_POOL=0.99
# the tolerant tier: the creation's ETH value lo,hi that is traded (1.4-2.2 measured; everything else is watched only)
BASE_V2_TIER_BAND=1.3,2.3
# ETH values never traded even inside the band (the 1.2 tier reacts to any buy), comma-separated at 0.001 ETH; may be empty
BASE_V2_TIER_EXCLUDE=1.2
# the line's probe wallet(s), comma-separated: its creation-block dust buy triggers nothing and is not an outsider
BASE_V2_PROBE=0xe71a69f434a719cd5afa411568b69716aab3b84a,0x0e77610e9f13062c2eaa709ef1c59b8c22e549c9
# a confirmed buy under this many ETH is not an outsider's; 0 = any buy, dust included
BASE_V2_OUTSIDER_MIN_ETH=0
# how many blocks a pair of the line is followed after its creation (its outsider_buy and pull lines), at most, when no Burn ends it
BASE_V2_WATCH_BLOCKS=1400
# the fire is refused once the confirmed head is at the creation block + this (1: the buy must land at N+1)
BASE_V2_LAND_MAX=1
# 1 = the back-run: the guard at the pending tag and the buy into the creation block itself (off until stage 0 measured the delay)
BASE_V2_BACKRUN=0
# the exit test's ETH back over its constant-product quote, below which the token is taxed and refused
BASE_V2_EXIT_MIN=0.98

# ---- the trade (the stage settings: docs/BASE_V2.md section 9; RUNBOOK 4m steps 9-10)
# the stake in ETH; never above BASE_V2_STAKE_CAP_ETH (stage 1: 0.002, stage 2: 0.02, stage 3: 0.05 then 0.1)
BASE_V2_STAKE_ETH=0.02
# the stake's ceiling: the engine buys min(BASE_V2_STAKE_ETH, this); you raise it in steps, on your own decision
BASE_V2_STAKE_CAP_ETH=0.02
# the stake is also capped at this share of the pair's ETH reserve (0.05 of a 2 ETH pool = 0.1 ETH)
BASE_V2_SHARE_CAP=0.05
# the buy's minOut under the constant-product output on the Mint's reserves
BASE_V2_BUY_SLIP=0.03
# the buy's deadline in seconds (it mines and reverts at worst: a stale buy never fills late)
BASE_V2_BUY_DEADLINE_S=6
# a position is never held past the creation block + this (the earliest scheduled pull seen on the tier is +198)
BASE_V2_HARD_BLOCK=180
# the hard exit's sell is sent at the creation block + this
BASE_V2_SELL_SEND_BLOCK=176
# the hard sell is sent again at the same nonce with twice the priority when unseen by the creation block + this
BASE_V2_SELL_RESEND_BLOCK=178
# the hard exit from the wall clock, seconds after the creation block's timestamp, when no head has come
BASE_V2_SELL_FALLBACK_S=370
# sold when the reserves value the position at the stake x (1 + this)
BASE_V2_TAKE_PROFIT=0.25
# the take-profit and fleet-sell sells' minOut under the tracked output (0 for the outsider, hard and pulled sells)
BASE_V2_SELL_SLIP=0.05
# the sell's deadline in seconds
BASE_V2_SELL_DEADLINE_S=6
# 1: the fleet's first sell on our pair sells (fleet_sell); 0: off, take-profit or the hard block decide (Oct 20: +27.8% mean off, +19.7% on)
BASE_V2_FLEET_SELL_EXIT=1
# positions open at once, one per pair (stage 1: 1)
BASE_V2_MAX_POSITIONS=3
# at most this many buys a UTC day (stage 1: 5, stage 2: 10)
BASE_V2_MAX_PER_DAY=20
# the live net loss in ETH that stops new buys for the rest of the UTC day
BASE_V2_DAILY_STOP_ETH=0.15
# a Burn on a pair of the tier earlier than this many blocks after its creation ends the tier for the day
BASE_V2_SCHEDULE_MIN=190
# a sell taking this share of the ETH reserve on a pair of the tier ends the tier for the day (the dump pattern)
BASE_V2_PULL_SHARE=0.30
# a Burn within this many blocks after a buy is a reaction (on our pair with no outsider before it: the halt)
BASE_V2_REACT_BLOCKS=10
# live losses in a row that halt the line; 0 = off
BASE_V2_LOSS_STREAK_HALT=2
# live buys mined past the creation block + BASE_V2_LAND_MAX that halt the line; 0 = off
BASE_V2_LATE_HALT=2
# dollars per ETH, for the dollar figures only
BASE_V2_ETH_USD=2570
# the priority fee in gwei (above the creation's 0.006 and the fleet's 0.001; a round trip is about 0.03% of a 0.02 ETH stake)
BASE_V2_PRIO_GWEI=0.03
# the most maxFeePerGas may be, in gwei (2 x the base fee + the priority, capped here)
BASE_V2_MAX_FEE_GWEI=0.5
# the buy's gas limit
BASE_V2_BUY_GAS=250000
# the sell's gas limit
BASE_V2_SELL_GAS=250000
# the relay must hold the stake plus this much ETH beyond the open positions' stakes to fire
BASE_V2_RELAY_MARGIN_ETH=0.0005
EOF_TPL
OLD_UMASK=$(umask); umask 077
/opt/flip-venv/bin/python3 - "$TPL" "$ENV" <<'PY'
import os, re, sys
tpl, env = sys.argv[1], sys.argv[2]
line_re = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")
try:
    old = open(env).read().splitlines(); existed = True
except FileNotFoundError:
    old = []; existed = False
vals = {}
for l in old:
    m = line_re.match(l)
    if m:
        vals[m.group(1)] = m.group(2).strip()                                   # the last line of a name wins, as systemd reads it
created = vals.pop("BASE_WALLET", None)                                         # base_wallet.py create's line
if created and not vals.get("BASE_V2_WALLET"):
    vals["BASE_V2_WALLET"] = created
if not vals.get("BASE_V2_KEY_FILE"):
    vals["BASE_V2_KEY_FILE"] = "/etc/flip/base_v2.key"
out, known, added = [], [], []
for l in open(tpl).read().splitlines():
    m = line_re.match(l)
    if m:
        k = m.group(1); known.append(k)
        if k in vals:
            l = f"{k}={vals[k]}"
        elif existed:
            added.append(k)
    out.append(l)
extra = [k for k in vals if k not in known]
if extra:
    out += ["", "# ---- kept from the previous file (not a setting of docs/BASE_V2.md section 5: the engine ignores these)"] + [f"{k}={vals[k]}" for k in extra]
tmp = env + ".tmp"
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
try:
    os.fchmod(fd, 0o600); os.write(fd, ("\n".join(out) + "\n").encode()); os.fsync(fd)
finally:
    os.close(fd)
os.replace(tmp, env)
dry = vals.get("BASE_V2_DRY_RUN", "1")
if not existed:
    print(f"wrote {env} ({len(known)} settings, BASE_V2_DRY_RUN=1)")
else:
    print(f"{env} kept and completed ({len(known)} settings, {len(added)} added with their defaults, BASE_V2_DRY_RUN={dry})")
if created:
    print(f"BASE_WALLET={created} (base_wallet.py create's line) is now BASE_V2_WALLET={created}")
if extra:
    print("kept at the end, not settings of the V2 engine: " + " ".join(extra))
PY
umask "$OLD_UMASK"
chmod 600 "$ENV"
echo '/var/log/flip/base_v2.jsonl { daily rotate 30 missingok notifempty compress delaycompress copytruncate }' > /etc/logrotate.d/flip-base-v2
cat > /etc/cron.d/flip-base-v2-roster <<EOF_CRON
# the Base V2 line's fleet roster, rebuilt daily from the chain (deploy/base_v2_roster.py; docs/BASE_V2.md section 4); installed by base_v2_setup.sh
20 0 * * * root /opt/flip-venv/bin/python3 $REPO/deploy/base_v2_roster.py >>/var/log/flip/base_v2_roster.log 2>&1
EOF_CRON
chmod 644 /etc/cron.d/flip-base-v2-roster
sed "s|/home/ubuntu/v2pons|$REPO|g" "$REPO/deploy/flip-base-v2.service" > /etc/systemd/system/flip-base-v2.service
systemctl daemon-reload
systemctl enable flip-base-v2 >/dev/null 2>&1 || true
echo "installed: /etc/systemd/system/flip-base-v2.service, /etc/logrotate.d/flip-base-v2, /etc/cron.d/flip-base-v2-roster (00:20 UTC)"
DRY=$(grep '^BASE_V2_DRY_RUN=' "$ENV" | tail -1 || true)                                  # systemd takes the last line of a name
if [ -z "$DRY" ] || [ "$DRY" = "BASE_V2_DRY_RUN=1" ]; then
    systemctl restart flip-base-v2
    sleep 20
    echo "flip-base-v2: $(systemctl is-active flip-base-v2); its last start line:"
    /opt/flip-venv/bin/python3 - "$(grep '^BASE_V2_LOG_PATH=' "$ENV" | tail -1 | cut -d= -f2- || true)" <<'PY'
import json, sys
log = sys.argv[1] or "/var/log/flip/base_v2.jsonl"; last = None
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
print({k: last.get(k) for k in ("release", "dry", "head", "roster_n")} if last else "(no start line yet in %s: journalctl -u flip-base-v2 -n 20)" % log)
PY
else
    echo "$ENV says LIVE (its last BASE_V2_DRY_RUN= line is not 1): the unit is updated, the service is not restarted;"
    echo "restart it yourself when base_v2_results.py shows no open position: sudo systemctl restart flip-base-v2"
fi
