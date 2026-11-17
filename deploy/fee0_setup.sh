#!/bin/bash
# fee0_setup.sh: the fee-0 line's engine on the box (RUNBOOK 4o), beside the other flip engines and touching nothing of them: the shared
# venv (/opt/flip-venv, made by flip_setup.sh), its own settings (/etc/flip/fee0.env, mode 600, written once, never overwritten), its own
# log (/var/log/flip/fee0.jsonl) and its own service (flip-fee0). Idempotent: run it again after a git pull to pick up a changed unit.
# Starts the service in DRY_RUN=1 (a new fee0.env says so; an existing one is left as it is).
#
#     cd ~/v2pons && sudo bash deploy/fee0_setup.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[ -x /opt/flip-venv/bin/python3 ] || { echo "no /opt/flip-venv: run deploy/flip_setup.sh first"; exit 1; }
/opt/flip-venv/bin/pip install -q eth-account eth-utils >/dev/null
mkdir -p /etc/flip /var/log/flip; chmod 700 /etc/flip
if [ ! -f /etc/flip/fee0.env ]; then
cat > /etc/flip/fee0.env <<'EOF'
# flip-fee0 settings (src/fee0_engine.py reads every line; comments only on their own lines). A dry run until DRY_RUN=0.
DRY_RUN=1
LOG_PATH=/var/log/flip/fee0.jsonl
HALT_FILE=/var/log/flip/FEE0_HALTED
RPC_URL=https://rpc.mainnet.chain.robinhood.com
SEQ_URL=https://sequencer.mainnet.chain.robinhood.com
# its own wallet (gas only) and the FlipRelay it owns (the stake): deploy/new_wallet.py /etc/flip/fee0.env, then relay_deploy.py with
# FLIP_ENV=/etc/flip/fee0.env FLIP_SERVICE=flip-fee0 (RUNBOOK 4o steps 3-4). Never flip-engine's wallet.
WALLET=
RELAY=
PRIVATE_KEY=
# the trade: $5 at $3000/ETH
STAKE_ETH=0.0017
ETH_USD=3000
TRIG_ETH=0.02
TAKE_PROFIT=0.08
STOP_LOSS=0.05
HOLD_BLOCKS=2000
TRIGGER_MAX_BLOCKS=2500
BUY_SLIP=0.05
MAX_TRADES_PER_DAY=40
DAILY_STOP_USD=10
EOF
chmod 600 /etc/flip/fee0.env; echo "wrote /etc/flip/fee0.env (DRY_RUN=1)"
fi
echo '/var/log/flip/fee0.jsonl { daily rotate 30 missingok notifempty compress delaycompress copytruncate }' > /etc/logrotate.d/flip-fee0
sed "s#/home/ubuntu/v2pons#$REPO#g" "$REPO/deploy/flip-fee0.service" > /etc/systemd/system/flip-fee0.service
systemctl daemon-reload; systemctl enable -q flip-fee0; systemctl restart flip-fee0
sleep 3; systemctl --no-pager --lines=0 status flip-fee0 | head -3
echo "log: tail -f /var/log/flip/fee0.jsonl"
