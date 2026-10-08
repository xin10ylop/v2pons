#!/bin/bash
# flip_setup.sh: the flip engine on the Ohio box, beside the Pons engine and touching nothing of it: its own venv (/opt/flip-venv),
# its own settings (/etc/flip/engine.env, mode 600), its own log (/var/log/flip/engine.jsonl, rotated daily) and its own service
# (flip-engine). Idempotent: run it again after a git pull to pick up a changed unit. Starts the service in DRY_RUN=1.
#
#     cd ~/v2pons && sudo bash deploy/flip_setup.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
apt-get install -y -q python3-venv >/dev/null 2>&1 || true
[ -x /opt/flip-venv/bin/python3 ] || python3 -m venv /opt/flip-venv
/opt/flip-venv/bin/pip install -q --upgrade pip >/dev/null
/opt/flip-venv/bin/pip install -q websockets rlp eth-account eth-utils coincurve
mkdir -p /etc/flip /var/log/flip; chmod 700 /etc/flip
if [ ! -f /etc/flip/engine.env ]; then
cat > /etc/flip/engine.env <<'EOF'
# flip engine settings (src/flip_engine.py reads every line; comments only on their own lines)
DRY_RUN=1
LOG_PATH=/var/log/flip/engine.jsonl
FEED_URL=wss://feed.mainnet.chain.robinhood.com
SEQ_URL=https://sequencer.mainnet.chain.robinhood.com
RPC_URL=https://rpc.mainnet.chain.robinhood.com
# the operator's launcher contract(s), comma-separated
LAUNCHERS=0x3194e32622c5d860a0572c74edda99dcfd8fc827
POOL_MANAGER=0x8366a39cc670b4001a1121b8f6a443a643e40951
# the new wallet (gas only) and the relay it owns (the stake); set by relay_deploy.py --write-env
WALLET=
RELAY=
PRIVATE_KEY=
# the trade: $3 at $2570/ETH
STAKE_ETH=0.0012
ETH_USD=2570
MIN_TRIGGER_ETH=0.0002
FEE_MIN_PPM=0
FEE_MAX_PPM=9999
MIN_LIQUIDITY=1e21
TRIGGER_MAX_BLOCKS=150
BUY_SLIP=0.10
BUY_DEADLINE_S=3
HOLD_BLOCKS=7
SELL_LEAD_BLOCKS=2
SELL_FALLBACK_S=1.2
MAX_TRADES_PER_DAY=10
DAILY_STOP_USD=15
EOF
chmod 600 /etc/flip/engine.env
fi
cat > /etc/logrotate.d/flip-engine <<'EOF'
/var/log/flip/engine.jsonl { daily rotate 30 missingok notifempty compress delaycompress copytruncate }
EOF
cat > /etc/systemd/system/flip-engine.service <<EOF
[Unit]
Description=flip engine (v2pons)
After=network-online.target
Wants=network-online.target

[Service]
EnvironmentFile=/etc/flip/engine.env
WorkingDirectory=$REPO
ExecStart=/opt/flip-venv/bin/python3 $REPO/src/flip_engine.py
Restart=always
RestartSec=3
Nice=-5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable flip-engine >/dev/null 2>&1 || true
systemctl restart flip-engine
sleep 6
echo "flip-engine: $(systemctl is-active flip-engine); last start line:"
grep -h '"ev":"start"' /var/log/flip/engine.jsonl 2>/dev/null | tail -1 || echo "(no start line yet: journalctl -u flip-engine -n 20)"
