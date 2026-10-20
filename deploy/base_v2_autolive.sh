#!/bin/bash
# base_v2_autolive.sh: the switch from the dry run to the $5 stage, made by the box itself (docs/BASE_V2.md section 9, stage 0 -> 1).
# It watches the dry log; when the engine has made N correct dry decisions on the tradable tier (a `would_fire` with a guard verdict ok,
# aimed at the creation block + 1, ready in under 1,500 ms, and a dry `trade_done` behind it) with no alarm of the feeds and no halt
# since the start, it writes the stage-1 settings into the env file (live, 0.002 ETH stake and cap, one position, five trades a day)
# and restarts the service. It refuses to switch while the relay is not set, not funded, or the halt file exists. It never raises the
# stake: every stage above $5 is the owner's hand (RUNBOOK 4m).
#     sudo bash ~/v2pons/deploy/base_v2_autolive.sh            # runs until it switched (or forever if it never can); Ctrl-C stops it
#     sudo bash ~/v2pons/deploy/base_v2_autolive.sh --check    # one pass: prints the count and the reasons, switches nothing
set -u
ENV_FILE="${ENV_FILE:-/etc/flip/base_v2.env}"; LOG="${LOG:-/var/log/flip/base_v2.jsonl}"; SERVICE="${SERVICE:-flip-base-v2}"
NEED="${NEED:-3}"; STAKE="${STAKE:-0.002}"; HALT_FILE="${HALT_FILE:-/var/log/flip/HALTED.base_v2}"; RPC="${RPC:-https://mainnet.base.org}"
need_root() { [ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }; }
set_kv() { grep -q "^$1=" "$ENV_FILE" && sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE" || echo "$1=$2" >> "$ENV_FILE"; }
get_kv() { grep "^$1=" "$ENV_FILE" 2>/dev/null | tail -n 1 | cut -d= -f2- | sed 's/ #.*//' | tr -d ' '; }
balance_eth() { curl -s -m 15 -X POST -H 'content-type: application/json' --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"$1\",\"latest\"]}" "$RPC" | python3 -c "import sys,json; print(int(json.load(sys.stdin)['result'],16)/1e18)" 2>/dev/null || echo 0; }

count_pass() {
    # the decisions since the last start line: would_fire lines on the tradable tier with guard ok, aim == creation + 1, ready_ms < 1500,
    # each followed by a dry trade_done for the same pair; alarms about the feeds and halts since the start veto the switch
    python3 - "$LOG" "$NEED" <<'PY'
import sys, json
log, need = sys.argv[1], int(sys.argv[2])
ev = []
for l in open(log):
    try: ev.append(json.loads(l))
    except Exception: pass
starts = [i for i, e in enumerate(ev) if e.get("ev") == "start"]
ev = ev[starts[-1]:] if starts else ev
if not ev or not ev[0].get("dry", True): print("0 the engine is not in a dry run (or has no start line)"); sys.exit(0)
done = {e.get("pair") for e in ev if e.get("ev") == "trade_done" and e.get("dry")}
guards = {e.get("pair"): e for e in ev if e.get("ev") == "guard"}
fires = [e for e in ev if e.get("ev") == "would_fire"]
good, why = 0, []
for f in fires:
    g = guards.get(f.get("pair"), {}); ok = True
    if str(g.get("verdict", g.get("kind", ""))).lower() not in ("ok", "sellable"): ok = False; why.append("guard not ok on %s" % str(f.get("pair"))[:10])
    aim, block = f.get("aim"), f.get("creation")
    if aim is not None and block is not None and aim != block + 1: ok = False; why.append("aim %s not creation+1 on %s" % (aim, str(f.get("pair"))[:10]))
    if f.get("ready_ms") is not None and f["ready_ms"] >= 1500: ok = False; why.append("ready_ms %s on %s" % (f["ready_ms"], str(f.get("pair"))[:10]))
    if f.get("pair") not in done: ok = False; why.append("no dry trade_done yet on %s" % str(f.get("pair"))[:10])
    good += ok
halts = [e for e in ev if e.get("ev") == "halt"]; alarms = [e for e in ev if e.get("ev") == "alarm" and any(k in str(e.get("what", "")) for k in ("feed", "websocket", "flash", "poller"))]
if halts: why.append("a halt since the start: %s" % str(halts[-1].get("reason", halts[-1]))[:80])
if alarms: why.append("a feed alarm since the start: %s" % str(alarms[-1].get("what"))[:80])
print(good if not (halts or alarms) else 0, "; ".join(why[-4:]) if why else "clean")
PY
}

need_root
if [ "${1:-}" = "--check" ]; then r=$(count_pass); echo "correct dry decisions: ${r%% *} of $NEED needed; ${r#* }"; exit 0; fi
echo "watching $LOG for $NEED correct dry decisions on the tradable tier (Ctrl-C stops; nothing is switched before that)"
while true; do
    r=$(count_pass); n=${r%% *}
    if [ "$n" -ge "$NEED" ] 2>/dev/null; then
        relay=$(get_kv BASE_V2_RELAY)
        if [ -z "$relay" ]; then echo "$(date -u +%H:%M:%S) $n decisions but BASE_V2_RELAY is not set: deploy the relay first (RUNBOOK 4m)"; sleep 60; continue; fi
        if [ -e "$HALT_FILE" ]; then echo "$(date -u +%H:%M:%S) $n decisions but the halt file exists: not switching"; sleep 60; continue; fi
        bal=$(balance_eth "$relay")
        if ! python3 -c "import sys; sys.exit(0 if float('$bal') >= float('$STAKE') + 0.0005 else 1)"; then echo "$(date -u +%H:%M:%S) $n decisions but the relay holds $bal ETH, under the stake $STAKE + margin: deposit first"; sleep 60; continue; fi
        set_kv BASE_V2_DRY_RUN 0; set_kv BASE_V2_STAKE_ETH "$STAKE"; set_kv BASE_V2_STAKE_CAP_ETH "$STAKE"; set_kv BASE_V2_MAX_POSITIONS 1; set_kv BASE_V2_MAX_PER_DAY 5
        systemctl restart "$SERVICE" && sleep 20
        echo "$(date -u +%H:%M:%S) switched to the \$5 stage: live, stake $STAKE ETH, one position, five trades a day; service $(systemctl is-active "$SERVICE")"
        grep '"ev":"start"' "$LOG" | tail -n 1 | cut -c1-200
        exit 0
    fi
    echo "$(date -u +%H:%M:%S) correct dry decisions: $n of $NEED; ${r#* }"
    sleep 30
done
