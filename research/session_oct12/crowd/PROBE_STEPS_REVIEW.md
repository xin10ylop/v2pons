# The v3crowd probe steps: two Opus reviews (Oct 12, about 17:00 UTC)

Not yet approved by the owner. Recommendation of the engine review: start the v3crowd probe after the C-1 probe ends (attribution: the two lines probably share an operator, and both probes trade from one wallet). The two reviewers' corrected step sets below must be merged and re-checked against the box's state before use.

## Reviewer 1 (commands)

### Problems

- **HIGH** Steps 4, 5 and 6 ("means stop"; "refuses, and changes nothing"), with the engine stopped since step 3: No step says to start the engine again after a stop or a refusal from step 3 onwards. Followed literally, any stop leaves flip-engine down, which halts the owner-approved C-1 probe with no end date. Ways to get there:
- step 4 refuses, or prints UNEXPECTED / DO NOT USE / MISMATCH / reverted;
- the deposit fails;
- step 6's assert refuses.
Restarting is safe at every one of these points: v3crowd is dry until step 6 writes. With --write-env, a RELAY_V3 line written after a simulated-buy MISMATCH or reverted is harmless while every V3 family is dry, because checks() makes no family live.

  Fix: Add this rule above the steps:
  
  Steps 3 to 7 run with the engine stopped, so the C-1 probe pauses for those minutes. If any step from 3 to 7 says stop or refuses, start the engine again at once: `sudo systemctl start flip-engine`. v3crowd stays dry until step 6 succeeds, so c1 resumes exactly as before.
  
  In step 4, also say: "stop means: start the engine again".

- **MED** Step 2: /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py ("It must end `all as expected`"): I ran it read-only in my copy at about 16:52 UTC Oct 12 against the public RPC. It ended `SOMETHING IS NOT AS EXPECTED: do not deploy this build` with exit 1, so the draft would stop the probe here.

The relay itself is fine. The p356, selfbuyer, crowd and weth-token1 legs were exact against QuoterV2, and every failure path was ok.

The only BAD lines were the `[pulled]` pick: pool 0xe8bdb14d5cdb5b65bbfdadafea2bea190a747315, another launcher's 1% pool (`other 0xb7351ba8 0xc82028d7 804 B`). It is not pulled:
- liquidity is 0 at its tick, but the pool holds 316M tokens;
- the token refuses any transfer with custom error 0x8574adcf;
- so both cut-short buys revert with `Error(TF)` instead of `TooLittleOut`.

The simulator takes "liquidity 0 and quote 0" to mean pulled, so this false alarm can come back on any run. On the crowd's own pulled pools the cut-short check passes. Given 0x3034636949d6e6c158ecbcbe4190d8374f14a954 and 0x826e2a8ac86025f079a0e39c64f6c3ed89838251, it printed `pulled: the cut-short buy ok` for both (exit 2, no live pool given).

  Fix: Keep the default run. Add:
  
  If it ends `SOMETHING IS NOT AS EXPECTED` and the only BAD lines are the two under `[pulled]` reading `Error(TF)`:
  1. Check that the `crowd` summary line says `failure paths all ok`.
  2. Run the simulation on v3crowd's own recent pools:
  
  sudo python3 ~/v2pons/deploy/englog.py 6 | grep '"ev":"trade_done"' | grep '"fam":"v3crowd"' | grep -o '"pid":"0x[0-9a-f]\{40\}"' | cut -d'"' -f4 | awk '!s[$0]++' | tail -3 | xargs -r /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py
  
  Each summary line must say `pulled: the cut-short buy ok`, or `failure paths all ok` for a live pool. Exit 2 is fine there. Any other BAD means stop.

- **MED** Step 1, the code guard (git diff --quiet 695b25e HEAD -- ...): The guard misses two files and one kind of change:
- deploy/relay_sim.py: its rpc() is what posts the signed deployment, deposit and withdrawal (eth_sendRawTransaction), and relay_v3_deploy.py, relay_v3_sim.py and relay_ops.py all import it.
- contracts/RoundTripHarnessV3.sol: step 2's verdict rests on this harness.
- Uncommitted edits on the box: `HEAD` compares commits only, while the scripts run from the working tree.

All twelve files are identical to 695b25e in this repo, both at HEAD and in the working tree.

  Fix: cd ~/v2pons && git pull -q --ff-only && git log --oneline -1 && { git diff --quiet 695b25e -- src/flip_engine.py src/v4math.py deploy/englog.py deploy/results.py tests/test_engine.py contracts/FlipRelayV3.sol contracts/FlipRelayV3.json contracts/RoundTripHarnessV3.sol deploy/relay_v3_deploy.py deploy/relay_v3_sim.py deploy/relay_ops.py deploy/relay_sim.py || { echo 'engine or relay code differs from the reviewed 695b25e: stop here'; false; }; } && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c '^ok'

- **MED** Step 6 "Leave these unchanged: ... FRONT_DAILY_STOP_USD (5)"; step 8 "-5 or below"; step 9 "front's day at -$5": $5 is only the code default (flip_engine.py line 203, used when the setting is unset). HANDOFF says the box ran FRONT_DAILY_STOP_USD 100 and FRONT_NONBOT_HALT 8 from Oct 11 16:44, and RUNBOOK 4j repeats "8 on the box".

Nothing in the steps prints the value the engine actually uses. If it is 100:
- c1's -$5 day does not idle v3crowd;
- the stated -$5 stop does not exist.

An owner who "restores" 5 would also change c1's own daily stop.

The start line already carries `front_daily_stop_usd`, `front_nonbot_halt`, `v3_daily_stop_usd`, `v3_gas`, `v3_pnl_today_usd` and `today_restored.front_pnl_today_usd`.

  Fix: In step 6, the snippet prints the env file's values (empty means the code default):
  
  print("in the env file (empty = the code default):", {k: val(k) for k in ("V3_SELL_CHECK", "FRONT_DAILY_STOP_USD", "FRONT_NONBOT_HALT", "V3_DAILY_STOP_USD", "V3_STAKE_CAP_ETH", "V3_GAS", "FRONT_MAX_PER_DAY")})
  
  In step 7, the start-line check prints:
  
  print("stops: FRONT_DAILY_STOP_USD", s.get("front_daily_stop_usd"), "front today $", (s.get("today_restored") or {}).get("front_pnl_today_usd"), "| V3_DAILY_STOP_USD", s.get("v3_daily_stop_usd"), "V3 today $", s.get("v3_pnl_today_usd"), "| FRONT_NONBOT_HALT", s.get("front_nonbot_halt"))
  
  Phrase both stop rules with the printed values: "front's day at minus FRONT_DAILY_STOP_USD" and "a V3 day at minus V3_DAILY_STOP_USD".

- **MED** Step 3: sudo python3 ~/v2pons/deploy/results.py | head -4 && sudo systemctl stop flip-engine: The "check no trade is open" cannot happen. The `&&` stops the engine as soon as results.py prints, with no pause to read it, and results.py's first four lines do not show an open position anyway.

What actually protects a c1 position is the engine's own safe stop: on_stop/stop_tick waits up to STOP_WAIT_S (40 s) for the open trade and the pull checks. Nothing checks that it ended idle.

If it exits with `"idle":false`, c1's presigned sell may not have gone out. The deployment would then take the next pending nonce, and the tokens would stay in the v4 relay.

  Fix: sudo systemctl stop flip-engine; systemctl is-active flip-engine; sudo python3 ~/v2pons/deploy/englog.py 1 | grep -E '"ev":"(stopping|stopped)"' | tail -2 | cut -c1-200
  
  It must print `inactive`, and its last line must be `{"ev":"stopped","idle":true,...}`.
  
  `"idle":false`: run `sudo python3 ~/v2pons/deploy/results.py | head -30`, settle that trade by hand, and start the engine again before going on.

- **MED** Step 10, Off: "Run RUNBOOK 4j's step-2 snippet with `v3crowd dry`": RUNBOOK 4j's snippet runs `shutil.copy2(P, P + ".bak")`, which overwrites /etc/flip/engine.env.bak. PROBE_COMMANDS.md names that file as the C-1 probe's backup ("The old c1 settings are in /etc/flip/engine.env.bak"), so turning v3crowd off destroys C-1's record.

It also restarts the engine, and the next line stops and starts it again.

  Fix: Use a dedicated snippet. It does the following, in order:
  - sets only v3crowd's dry_run to true, with the same refusals as step 6;
  - keeps its own backup, engine.env.bak.v3crowd-off;
  - stops the engine and withdraws the V3 relay's ETH;
  - always starts the engine again.
  
  Its first line (the full snippet is in final_steps):
  
  cd ~/v2pons && sudo python3 - <<'PY' && sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw_v3; sudo systemctl start flip-engine && sleep 8 && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status

- **MED** Step 9, "The engine stops the probe by itself on:": The list leaves out the one v3crowd outcome that stops C-1 as well. In _settle_v3, a filled buy whose sell has no receipt calls halt(..., scope="front") with no family. That writes /var/log/flip/HALTED.front, which halts every front line, c1 included. REPORT_W2 section 10 lists this case; the steps drop it.

  Fix: Add:
  
  - Front as a whole: a filled buy whose sell has no receipt writes HALTED.front, and that stops c1 too. Once the cause is understood, resume c1 alone (v3crowd stays halted):
  
  echo "v3crowd: front halted by a V3 sell with no receipt" | sudo tee /var/log/flip/HALTED.front.v3crowd >/dev/null && sudo rm /var/log/flip/HALTED.front && sudo systemctl restart flip-engine

- **MED** The whole draft's layout (commands indented 4 spaces under "1.".."10." list items): Neither way of copying the commands works:
- Rendered: inside a numbered list item, 4 spaces is not a code block. pandoc -f commonmark rendered no code block at all: the lines are joined, `sed -i -e '$a\'` becomes `'$a'` (a GNU sed error), and the heredoc and the Python are merged into one paragraph.
- Raw text: every line keeps 4 leading spaces, so `    PY` never ends the heredoc and Python raises IndentationError.

  Fix: Use `## N.` headings for the steps, and put each command in a fenced block (``` ... ```) with its text at column 0. All 12 blocks in final_steps render as code (pandoc counted 12 <pre>) and pass `bash -n`.

- **LOW** Step 6: set_kv V3_SELL_CHECK 0 runs before the Python guard; the snippet's temporary file: Three small faults:
- Tested on a synthetic env without RELAY_V3, the Python refused with "... nothing changed", but V3_SELL_CHECK=0 had already been appended.
- On success, engine.env.bak.v3crowd is not the file as it was before step 6: it already holds V3_SELL_CHECK=0.
- open(tmp, "w") creates the copy of the env file, private key included, with the umask's mode (644) until copymode runs.

  Fix: Drop the set_kv and sed lines. One guarded Python snippet (full text in final_steps, step 6):
  - refuses unless RELAY_V3 and RELAY_V3_CODEHASH are present and V3_SELL_CHECK is set at most once;
  - makes the backup before any change;
  - sets or appends V3_SELL_CHECK=0 in the same write as the family edit;
  - writes through os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600) after unlinking a stale .tmp.
  
  Tested: refusal leaves the file byte-identical; success changes only v3crowd's three fields plus V3_SELL_CHECK=0; both files are mode 600; a rerun refuses; a duplicate V3_SELL_CHECK refuses.

- **LOW** Step 8: englog.py 1 | grep '"ev":"flow"' | tail -1, run right after step 7: The engine logs `flow` only every 600 blocks, about once a minute. Run 8 s after the start, the last flow line within the hour comes from the run before the stop, so `relay_v3_eth` shows None and the V3 numbers are stale. With no flow line in the window, the one-liner crashes with JSONDecodeError (tested).

  Fix: Drop step 8. The corrected step 7 start-line check already prints front's day (today_restored.front_pnl_today_usd), the V3 day (v3_pnl_today_usd), the relay's ETH (relay_v3_eth) and both stops, all from the new run's start line.

- **LOW** Step 4 acceptance list: relay_v3_deploy.py catches an exception in the simulated buy, prints `the simulated buy did not run (...)` and goes on to write the env lines. The draft lists only `no live V3 WETH pool` as acceptable, so a passing RPC hiccup would stop the procedure, with the engine left down. The code was already checked byte for byte with its owner, and step 2 covers the buy.

  Fix: These are acceptable when step 2 passed:
  - `no live V3 WETH pool`;
  - `the simulated buy did not run`.
  
  `UNEXPECTED`, `DO NOT USE`, `MISMATCH`, `reverted` or any refusal means stop: start the engine again.

### Checked

What I read:
- The draft /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/v3crowd_steps.md, exactly as written.
- REPORT_W2.md and its settings, research/session_oct12/c1/short/PROBE_COMMANDS.md, RUNBOOK 4j, HANDOFF 7.3, 16.11 and 16.22, and docs/RELAY_V3.md.
- The code at 66c0a31. The twelve guarded files are identical to 695b25e at HEAD and in the working tree.
- In flip_engine.py: the settings parsing, front_families, checks/relay_v3_check, start_families, main's start line, the flow line, _fire, _settle_v3, halt, the halt-file loading, restore_today and on_stop/stop_tick.
- The scripts relay_v3_deploy.py, relay_ops.py, relay_v3_sim.py, relay_sim.py, englog.py and results.py, and FlipRelayV3.sol (receive, and withdraw(0) = all).

What I ran, only in my copy /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/v3rev.tAy8:
1. tests/test_engine.py: 76 ok. A copy that keeps the engine log produced 19 live v3crowd trade_done lines.
2. The draft's probe check on those lines: it is correct (settled 19, filled 16, pulled before our sell 2, pulled by launch+90 3, launch-relative offsets right). Empty input does not crash it.
3. relay_v3_sim.py, after confirming it only reads: it signs nothing, never calls eth_sendRawTransaction and never opens the env file. Against the public RPC it exited 1 because of its pulled-pool pick. I checked that pool by eth_call: not pulled; its token refuses every transfer with 0x8574adcf. Given v3crowd's own pulled pools instead, both were `cut-short buy ok`.
4. Draft step 6 on a box-like synthetic env (c1 at its probe settings, p356, FRONT_DAILY_STOP_USD 100, FRONT_NONBOT_HALT 8):
   - on success it changes only v3crowd's three fields plus V3_SELL_CHECK;
   - when it refuses, V3_SELL_CHECK=0 has already been appended;
   - the engine parses the result after systemd-style quote stripping: v3crowd live True with stake 0.002; c1 unchanged (hold 30, max_blocks 100, nonbot 0, dry_run False).
5. A real start line, from main() with stubbed RPC and the edited env: the draft's step 7 one-liner works on it. Step 8's flow one-liner crashes when no flow line is in the window.
6. The corrected snippets (step 6, the start-line check, Off): refusal, success, rerun and duplicate-key cases; modes 600; the backups. All 12 final blocks pass `bash -n` and render as code in CommonMark. The draft's list-indented blocks render as paragraphs.

What the scripts do, checked against the code:
- The deploy refuses while the engine is active, on a wrong key, on an old RELAY_V3 that still holds money, on an artifact whose source hash differs, or on the wrong chain.
- It prints the two env lines before writing them, comments out the previous ones, and writes mode 600.
- RELAY_V3_CODEHASH is the keccak of the code on chain. The engine compares it in lower case with 0x optional, and relay_ops's _v3 commands check it along with owner().
- deposit_v3 0.005 is exactly 5e15 wei.

C-1's state:
- No step edits c1's object (asserted, and byte-identical in the test), removes HALTED.front.c1, or changes FRONT_DAILY_STOP_USD or FRONT_NONBOT_HALT.
- A v3crowd loss counts only in the V3 day, and v3crowd's pull, sold-none and streak halts write its own file.
- What does touch c1:
  - the downtime in steps 3 to 7;
  - the front-wide halt on a V3 sell with no receipt;
  - the draft's Off, which overwrites C-1's engine.env.bak (fixed);
  - slot sharing: c1 fires skip "position open" while a v3crowd trade holds the slot (about 8 s plus receipts), and V3 fires wait for c1's pull check. That is about 1.5% of the time at 133 launches a day, and changes no setting or halt.

Nothing was sent, and no real key was used. The repository is unchanged (git status clean).

### Corrected steps (as proposed)

Preconditions:
- The owner has approved this probe.
- The line is launching. My read at 16:34 UTC found launches at 16:28 and 16:32 after the 13:44 pause.
- All commands are on the box. Paste each fenced block exactly as it is.

Steps 3 to 7 run with the engine stopped, so the C-1 probe pauses for those minutes (the deployment waits up to 2 minutes for its receipt). **If any step from 3 to 7 says stop or refuses, start the engine again at once: `sudo systemctl start flip-engine`.** v3crowd stays dry until step 6 succeeds, so c1 resumes exactly as before. A `RELAY_V3` line already written by step 4 is harmless while every V3 family is dry.

## 1. Pull and check the code (must print 76)

The guard compares the working tree, not only HEAD, and pins the relay's RPC layer (`deploy/relay_sim.py`) and the simulator's harness too.

```
cd ~/v2pons && git pull -q --ff-only && git log --oneline -1 && { git diff --quiet 695b25e -- src/flip_engine.py src/v4math.py deploy/englog.py deploy/results.py tests/test_engine.py contracts/FlipRelayV3.sol contracts/FlipRelayV3.json contracts/RoundTripHarnessV3.sol deploy/relay_v3_deploy.py deploy/relay_v3_sim.py deploy/relay_ops.py deploy/relay_sim.py || { echo 'engine or relay code differs from the reviewed 695b25e: stop here'; false; }; } && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c '^ok'
```

## 2. Simulate the relay (read-only: eth_call only, nothing is signed or sent)

```
/opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py
```

It must end `all as expected`. Exit 2 (no live pool found) means: rerun with `--hours 48`.

If it ends `SOMETHING IS NOT AS EXPECTED: do not deploy this build` and the only `BAD` lines are the two under `[pulled]` that read `Error(TF)`, the pool it picked is not pulled. It belongs to another launcher, and its token refuses transfers. This happened at Oct 12 16:52 UTC on pool 0xe8bdb14d (the `other 0xb7351ba8 ... 804 B` line). In that case:
- check that the `crowd` summary line says `failure paths all ok`;
- run the simulation on v3crowd's own recent pools:

```
sudo python3 ~/v2pons/deploy/englog.py 6 | grep '"ev":"trade_done"' | grep '"fam":"v3crowd"' | grep -o '"pid":"0x[0-9a-f]\{40\}"' | cut -d'"' -f4 | awk '!s[$0]++' | tail -3 | xargs -r /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py
```

Each of its summary lines must say `pulled: the cut-short buy ok`, or `failure paths all ok` for a live pool. Exit 2 is fine there. Any other `BAD` means stop.

## 3. Stop the engine and check that it stopped idle

```
sudo systemctl stop flip-engine; systemctl is-active flip-engine; sudo python3 ~/v2pons/deploy/englog.py 1 | grep -E '"ev":"(stopping|stopped)"' | tail -2 | cut -c1-200
```

It must print `inactive`, and its last line must be `{"ev":"stopped","idle":true,...}`. The stop waits up to 40 s for an open trade, c1's included.

`"idle":false` means a trade was still open when the engine exited. Run `sudo python3 ~/v2pons/deploy/results.py | head -30`, settle that trade by hand, and start the engine again before going on.

## 4. Deploy the V3 relay (type `yes` when asked)

```
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py --write-env
```

It must print:
- `matches the artifact byte for byte`;
- `owner() == wallet ok`;
- `equal, ok` on the simulated buy;
- the two lines `RELAY_V3=0x...` and `RELAY_V3_CODEHASH=0x...`, then `written to /etc/flip/engine.env`.

These are acceptable when step 2 passed:
- `no live V3 WETH pool`;
- `the simulated buy did not run`.

`UNEXPECTED`, `DO NOT USE`, `MISMATCH`, `reverted` or any refusal means stop: start the engine again. After a `MISMATCH` or `reverted` on the simulated buy, the two lines are already in the env file; that is harmless while v3crowd is dry.

## 5. Fund the relay with 0.005 ETH

```
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.005
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
```

The deposit must print a hash and `ok`. The status must show `V3 relay 0x...: 0.005000 ETH, owner 0x... == wallet`.

## 6. Set v3crowd live (the engine still stopped)

The snippet checks everything first, and changes nothing on any mismatch. Then it makes one write:
- v3crowd: `stake_eth` 0.002, `nonbot_halt` 30, `dry_run` false;
- `V3_SELL_CHECK=0`.

The file as it was just before is kept as `/etc/flip/engine.env.bak.v3crowd`, not as `engine.env.bak`, which holds C-1's backup.

```
cd ~/v2pons && sudo python3 - <<'PY'
import json, os, re, shutil
P = "/etc/flip/engine.env"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
lines = open(P).read().splitlines()
val = lambda k: ([l.split("=", 1)[1].split(" #", 1)[0].strip().strip("'\"") for l in lines if l.startswith(k + "=")] or [""])[-1]
assert re.fullmatch("0x[0-9a-fA-F]{40}", val("RELAY_V3")) and re.fullmatch("0x[0-9a-fA-F]{64}", val("RELAY_V3_CODEHASH")), "RELAY_V3 / RELAY_V3_CODEHASH missing in " + P + " (step 4 writes them): nothing changed"
sc = [k for k, l in enumerate(lines) if l.startswith("V3_SELL_CHECK=")]
assert len(sc) <= 1, "V3_SELL_CHECK is set more than once in " + P + ": nothing changed"
at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
    v = v[1:-1]
fams = json.loads(v); old = json.loads(v)
mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "v3crowd"] if isinstance(fams, list) else []
assert len(mine) == 1, "v3crowd is not in FRONT_FAMILIES exactly once: nothing changed"
f = mine[0]
assert f.get("dex") == "v3" and str(f.get("target", "")).lower() == NPM and int(f.get("calldata_len", 0)) == 836 and int(f.get("fee", 0)) == 100, "v3crowd is not the PositionManager 836-byte fee-100 family: nothing changed"
assert int(f.get("hold_blocks", 0)) == 78 and int(f.get("exit_after_blocks", 0)) == 18, "v3crowd's cap and clock are not 78 and 18 as replayed: nothing changed"
assert f.get("dry_run", True) is not False, "v3crowd is already live: nothing changed"
f["stake_eth"] = 0.002; f["nonbot_halt"] = 30; f["dry_run"] = False
assert [g for g in fams if g is not f] == [g for g in old if g.get("name") != "v3crowd"], "another family would change: nothing changed"
shutil.copy2(P, P + ".bak.v3crowd")
lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
if sc:
    lines[sc[0]] = "V3_SELL_CHECK=0"
else:
    lines.append("V3_SELL_CHECK=0")
tmp = P + ".tmp"
if os.path.lexists(tmp):
    os.unlink(tmp)
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w") as out:
    out.write("\n".join(lines) + "\n"); out.flush(); os.fsync(out.fileno())
os.replace(tmp, P)
c1 = ([g for g in fams if g.get("name") == "c1"] or [{}])[0]
print("v3crowd now:", json.dumps({k: f.get(k) for k in ("stake_eth", "nonbot_halt", "dry_run", "hold_blocks", "exit_after_blocks", "take_profit")}))
print("c1, unchanged:", json.dumps({k: c1.get(k) for k in ("dry_run", "hold_blocks", "take_profit", "stake_eth", "nonbot_halt", "pin")}), "max_blocks", (c1.get("trigger") or {}).get("max_blocks"))
print("families:", [(g.get("name"), g.get("dex", "v4"), "dry" if g.get("dry_run") else "LIVE") for g in fams])
print("in the env file (empty = the code default):", {k: val(k) for k in ("V3_SELL_CHECK", "FRONT_DAILY_STOP_USD", "FRONT_NONBOT_HALT", "V3_DAILY_STOP_USD", "V3_STAKE_CAP_ETH", "V3_GAS", "FRONT_MAX_PER_DAY")})
PY
```

It must print:
- `v3crowd now: {"stake_eth": 0.002, "nonbot_halt": 30, "dry_run": false, "hold_blocks": 78, "exit_after_blocks": 18, ...}`;
- `c1, unchanged:` with C-1's probe settings, `dry_run false`, `hold_blocks 30`, `take_profit 9`, `stake_eth 0.002`, `nonbot_halt 0`, `pin true` and `max_blocks 100`;
- the families, with v3crowd and c1 LIVE and the others as before;
- the env values. An empty value is the code default: `FRONT_DAILY_STOP_USD` 5, `FRONT_NONBOT_HALT` 5, `V3_DAILY_STOP_USD` 10, `V3_STAKE_CAP_ETH` 0.004, `V3_GAS` 500000. HANDOFF says the box has had `FRONT_DAILY_STOP_USD` 100 and `FRONT_NONBOT_HALT` 8 since Oct 11 16:44. Leave them all as they are.

## 7. Start the engine and check the start line

```
sudo systemctl start flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json, time; s = json.loads(sys.stdin.read()); print("start", round(time.time() - s["t"]), "s ago | relay_v3:", s.get("relay_v3"), "verified:", s.get("relay_v3_live"), "checked:", s.get("relay_v3_codehash_set"), "owner:", s.get("relay_v3_owner"), "wallet:", s.get("wallet"), "eth:", s.get("relay_v3_eth"), "cap:", s.get("v3_stake_cap_eth"), "gas:", s.get("v3_gas"), "sell check:", s.get("v3_sell_check")); print("stops: FRONT_DAILY_STOP_USD", s.get("front_daily_stop_usd"), "front today $", (s.get("today_restored") or {}).get("front_pnl_today_usd"), "| V3_DAILY_STOP_USD", s.get("v3_daily_stop_usd"), "V3 today $", s.get("v3_pnl_today_usd"), "| FRONT_NONBOT_HALT", s.get("front_nonbot_halt")); print("family error:", s.get("front_family_error"), "warnings:", s.get("front_family_warnings"), "| halted:", s.get("halted"), "front:", s.get("front_halted"), "families:", s.get("fam_halted")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"], "live", f.get("live"), "stake", f.get("live_stake_eth", f.get("stake_eth")), "hold", f["hold_blocks"], "exit", f.get("exit_after_blocks"), "tp", f.get("take_profit")) for f in s["front_families"]]'
sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"alarm"' | tail -3 | cut -c1-300
```

It must show:
- start a few seconds ago;
- `verified: True` and `checked: True`;
- the owner equal to the wallet, eth about 0.005, `cap: 0.004`, `gas: 500000`, `sell check: False`;
- `family error: None` and `warnings: None`;
- `halted: None` and `front: None`;
- families: `{}`, or c1 alone if it was halted before;
- `v3crowd v3 dry_run False live True stake 0.002 hold 78 exit 18 tp 9.0`;
- `c1 v4 dry_run False live None stake 0.002 hold 30 exit None tp 9.0`, as before;
- every other family as before.

The `stops:` line gives the values the engine uses:
- If `front today $` is at or below minus `FRONT_DAILY_STOP_USD`, the live V3 fires skip with "daily stop" until 00:00 UTC. That is expected; do not raise the stop.
- A v3crowd loss counts only in the V3 day, never in front's, so it never stops c1.

If anything else shows, turn it off (step 9).

## 8. At each look

Run `sudo python3 ~/v2pons/deploy/results.py | head -30` and this probe check:

```
sudo python3 ~/v2pons/deploy/englog.py 200 | grep '"ev":"trade_done"' | grep '"fam":"v3crowd"' | python3 -c 'import sys, json; d = [json.loads(l) for l in sys.stdin]; d = [e for e in d if e.get("ev") == "trade_done" and e.get("dex") == "v3" and e.get("dry") is False]; f = [e for e in d if isinstance(e.get("buy"), dict) and e["buy"].get("eth_in")]; L = lambda e, k: None if e.get(k) is None or e.get("buy_offset") is None else e["trig_seq"] + e["buy_offset"] + e[k] - e["launch_seq"]; near = [e for e in f if L(e, "pull_after_buy_blocks") is not None and L(e, "pull_after_buy_blocks") <= 90]; crowd = sum(1 for e in f if str(e.get("sell_why", "")).startswith("the crowd")); late = sum(1 for e in f if (e.get("buy_offset") or 0) > 3); pnl = sum(e.get("pnl_usd") or 0 for e in d); print("v3crowd probe: settled", len(d), "| filled", len(f), "| crowd-clock exits", crowd, "| buy landed after +3:", late, "| pull check failed:", sum(1 for e in d if e.get("pull_check")), "| pulled before our sell:", sum(1 for e in f if e.get("pulled_before_sell")), "| pulled by launch+90:", len(near), "| $ after gas %+.2f" % pnl, "| streak", (f[-1].get("nonbot_streak") if f else None)); [print("  pull at launch+%s, our sell landed at launch+%s, before our sell: %s, %s" % (L(e, "pull_after_buy_blocks"), L(e, "sell_after_buy_blocks"), e.get("pulled_before_sell"), str(e.get("sell_why"))[:40])) for e in near]'
```

The engine stops the probe by itself on:
- a pull at or before our sell (`HALTED.front.v3crowd`);
- a sell that sold none of the buy (the same file);
- 30 filled trades in a row under +2% (the same file);
- a V3 day at minus `V3_DAILY_STOP_USD`, or front's day at minus `FRONT_DAILY_STOP_USD` (the values in step 7's `stops:` line). Fires are skipped until 00:00 UTC.

**Front as a whole:** a filled buy whose sell has no receipt writes `HALTED.front`, and that stops c1 too. Once the cause is understood, resume c1 alone (v3crowd stays halted):

```
echo "v3crowd: front halted by a V3 sell with no receipt" | sudo tee /var/log/flip/HALTED.front.v3crowd >/dev/null && sudo rm /var/log/flip/HALTED.front && sudo systemctl restart flip-engine
```

Stop it by hand when:
- "pulled by launch+90" is above 0;
- crowd-clock exits are 1 or fewer at 30 filled trades, or 3 or fewer at 50 (the baseline is 18%);
- "buy landed after +3" reaches 2;
- filled reaches 100: stop and review.

If "pull check failed" is above 0, check that pool's first Burn by hand.

To stop by hand (the restart waits for an open trade; c1 is not touched):

```
echo "v3crowd probe stopped by hand" | sudo tee /var/log/flip/HALTED.front.v3crowd >/dev/null && sudo systemctl restart flip-engine
```

## 9. Off

This sets v3crowd dry, with its own backup `engine.env.bak.v3crowd-off`. Do not use RUNBOOK 4j's snippet here: it overwrites `/etc/flip/engine.env.bak`, which holds C-1's backup. Then it stops the engine, withdraws all the V3 relay's ETH to the wallet, starts the engine and shows the balances. The engine is started again even if the withdrawal fails. Run step 7's check afterwards; it must show `v3crowd v3 dry_run True live False`, with c1 as before.

```
cd ~/v2pons && sudo python3 - <<'PY' && sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw_v3; sudo systemctl start flip-engine && sleep 8 && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
import json, os, shutil
P = "/etc/flip/engine.env"
lines = open(P).read().splitlines()
at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
    v = v[1:-1]
fams = json.loads(v); old = json.loads(v)
mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "v3crowd"] if isinstance(fams, list) else []
assert len(mine) == 1 and mine[0].get("dex") == "v3", "v3crowd is not one V3 family of FRONT_FAMILIES: nothing changed"
f = mine[0]
assert f.get("dry_run") is False, "v3crowd is already dry: nothing changed"
f["dry_run"] = True
assert [g for g in fams if g is not f] == [g for g in old if g.get("name") != "v3crowd"], "another family would change: nothing changed"
shutil.copy2(P, P + ".bak.v3crowd-off")
lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
tmp = P + ".tmp"
if os.path.lexists(tmp):
    os.unlink(tmp)
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w") as out:
    out.write("\n".join(lines) + "\n"); out.flush(); os.fsync(out.fileno())
os.replace(tmp, P)
print("families:", [(g.get("name"), g.get("dex", "v4"), "dry" if g.get("dry_run") else "LIVE") for g in fams])
PY
```

`/etc/flip/engine.env.bak.v3crowd` is the file as it was just before step 6. Do not copy it back while the C-1 probe runs: that would also undo any c1 change made since.

## Reviewer 2 (engine and money)

### Problems

- **HIGH** Preconditions / timing (the whole plan) vs the running C-1 probe: The draft starts v3crowd while the owner-approved C-1 probe is live, from the same wallet. The two lines probably share an operator: C-1's router 0xd6d35b56 bought 0.86 ETH in 2 v3crowd pools (REPORT_W2 3, Risk 1). That operator has already reacted to our wallet: 4 of 5 of our live c1 trades were pulled at about 36 blocks. Every transaction of both probes comes from one EOA, and that same EOA creates the V3 relay. If both run together, each probe changes what the other measures. A fast c1 pull could be a reaction to our v3crowd extraction, and a v3crowd pull inside +78 could be a reaction to c1. Neither probe could then answer its own question. The losses are also correlated: one adaptation could cost about $5 on each line in the same hour. The engine itself does not force them apart: the slot costs only about 1% of attempts and the halts are separate. The reason to wait is attribution.

  Fix: Run the v3crowd probe after C-1's probe ends: c1 halted on a pull, or 100 attempts and stopped by hand (about 2 days at 54 triggers a day). Use C-1's result first: if that operator pulled within 30 blocks, a 78-block hold on a line it probably runs is unlikely to survive, so review before spending. If the owner still wants both now, use the corrected steps below and the step 9 'only if C-1 is still running' rule. That rule stops v3crowd by hand when C-1 shows any pull by buy+40 or halts on a pull. The step 0 overlap line measures the real slot overlap of the two lines.

- **MED** Step 6 'Leave these unchanged ... FRONT_DAILY_STOP_USD (5)', step 8, step 9 'front's day at -$5', REPORT_W2 8 and Risk 7: Code default: FRONT_DAILY_STOP_USD is 5, but only when the env file does not set it (flip_engine.py:203). The docs say the box set 100 (and FRONT_NONBOT_HALT 8) from Oct 11 16:44 (HANDOFF 1458), and REPORT_C1S_JUDGE:280 says 'it is 100 on the box'. Front's stop counts c1 and v2.433 trades only; live V3 trades go to their own day (_restore_from 1002-1005, _settle_v3 2176). It is checked before every live V3 fire (_fire 1646). At 100, front's stop is no brake on either probe: v3crowd's day is bounded by V3_DAILY_STOP_USD 10 and the pull halt, and the draft's '-5' rule in steps 8 and 9 is wrong. At 5 with front's day at -$5.00 (as REPORT_W2 says for c1), c1 itself skips every fire for 'daily stop' too. The approved C-1 probe would then be idle now, which nobody would notice. Neither the draft nor results.py prints the real value.

  Fix: Print the real values before anything changes (new step 0) and at the start (step 7). They are the start line's front_daily_stop_usd, front_nonbot_halt, v3_daily_stop_usd and today_restored.front_pnl_today_usd, plus the env lines (commands in final_steps). In steps 6, 8 and 9, replace '$5' with 'the FRONT_DAILY_STOP_USD that step 0 printed'. If front's day is at or under minus that value, c1 and v3crowd both skip until 00:00 UTC.

- **MED** Step 10 (Off): 'Run RUNBOOK 4j's step-2 snippet with v3crowd dry': RUNBOOK 4j's snippet runs shutil.copy2(P, P + '.bak'), which overwrites /etc/flip/engine.env.bak. That file is the C-1 probe's only restore point: PROBE_COMMANDS.md says the old c1 settings are there and that any later RUNBOOK snippet overwrites it. v3crowd reaches 100 fills in about a day, before C-1's roughly 2 days, so turning v3crowd off would destroy C-1's backup. The snippet also restarts the engine just before step 10 stops it again. V3_SELL_CHECK is left at 0, so any crowd V3 family set live later would trade unchecked.

  Fix: Use a dedicated Off snippet that writes engine.env.bak.v3crowd-off, sets v3crowd dry_run true and V3_SELL_CHECK=1, then withdraws, and always starts the engine again so C-1 goes on (exact text in final_steps, step 10). Do not restore engine.env.bak wholesale while v3crowd is live: it predates RELAY_V3.

- **MED** Steps 3-6 (order of operations): The order stop, deploy, fund, edit, start is safe for the nonce stream: relay_v3_deploy.py and relay_ops.py both refuse while flip-engine is active, and the engine reads the pending nonce at start. But steps 4-6 say only 'stop' on MISMATCH, a revert, a failed deposit or a refused edit. None of them says to start the engine again, so the live C-1 probe stays down without anyone noticing. Starting again is safe: with RELAY_V3 written but v3crowd and p356 still saying dry_run true, nothing V3 trades live (parser lines 480/490 and 539/551; v3_live 2933).

  Fix: Add to step 3: from here to step 7 C-1 is paused. If you stop at any of steps 4-6, run `sudo systemctl start flip-engine` so C-1 goes on; the RELAY_V3 lines change nothing while v3crowd says dry_run true.

- **LOW** Step 9, 'The engine stops the probe by itself on': The list misses the cross-probe halts. A c1 trade whose buy filled and whose sell sold none writes HALTED.front, front-wide, which stops v3crowd too (_settle 2015-2017). A V3 sell with no receipt writes HALTED.front, which stops c1 (_settle_v3 2159-2160). The base v2.433 line's pull and streak halts are front-wide as well (is_base_fam 932); that line has no launches now. In the other direction, c1's pull halt (HALTED.front.c1) and v3crowd's pull, sold-none and streak halts (HALTED.front.v3crowd) stop that family alone. A c1 pull check (front_settling, about 3.5 s) holds V3 fires (_fire 1673); a V3 pull check holds only V3 fires (1675). The '-$5' item is also wrong (see the MED item on FRONT_DAILY_STOP_USD).

  Fix: Replace the list with the one in final_steps step 9.

- **LOW** Step 6, `set_kv V3_SELL_CHECK 0` before the guarded snippet: V3_SELL_CHECK=0 is written before any of the snippet's checks, so 'the snippet refuses, and changes nothing' is not true. The backup engine.env.bak.v3crowd already holds V3_SELL_CHECK=0, plus the RELAY_V3 lines from step 4. The effect is small: V3_SELL_CHECK only matters for a crowd V3 family with dry_run false. p356 is still sell-checked whatever its value (1511, 1659).

  Fix: Drop the set_kv lines and set V3_SELL_CHECK=0 inside the snippet, after every check passes (final_steps step 6).

- **LOW** Step 6 snippet; best placed before step 4: Once RELAY_V3 is set, a V3 or launch-rule family whose object says "dry_run":false is no longer forced dry (launch_family 480/490, listed_family 539/551). Without RELAY_V3 such an object only raises a start alarm. RUNBOOK 4g put p356 in as dry_run true and the brief says p356 is dry, but nothing checks the file before step 4 writes RELAY_V3.

  Fix: Step 0 prints each family's dry_run as written in the file. Step 6 refuses when another V3 family says false (assert in final_steps).

- **LOW** Step 8 (flow line right after step 7): The flow line is written only every 600 blocks, about 62 s (2718). Eight seconds after the start, `tail -1` returns the flow line of the run before the stop: relay_v3_eth None, and front's day as it was then.

  Fix: `sleep 75` first and print the line's age (final_steps step 8). Front's day and the stops also appear in the step 7 start line.

- **LOW** Step 6 and Off snippets: tmp = P + '.tmp'; open(tmp, 'w'): The temporary copy of the env file, which holds PRIVATE_KEY, is created with root's default umask (0644) and gets mode 600 only at copymode. relay_v3_deploy.py's write_env uses 600 from the start.

  Fix: Add `os.umask(0o077)` as the snippet's second line (final_steps).

### Checked

Recommendation: run the v3crowd probe after C-1's probe ends, not alongside it. The engine handles both probes safely (separate family halts, the V3 day kept apart, a sequential nonce stream). The reason to wait is attribution: the two lines are probably run by one operator, and both probes trade from the same wallet.

Read the draft exactly (/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/v3crowd_steps.md), REPORT_W2 and REPORT_W2_DETAIL, research/session_oct12/c1/short/PROBE_COMMANDS.md, REPORT_C1S_JUDGE, RUNBOOK 4g and 4j, HANDOFF 16.18, 16.22 and line 1458, and src/flip_engine.py for each claim. No engine or relay code changed after 695b25e (git diff is empty to 66c0a31). The tests print 76 ok in my mktemp copy (/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/v3c.dG0M).

relay_v3_sim.py is read-only by construction: it only does eth_call, estimateGas, getLogs, getCode and blockNumber, and neither it nor relay_sim.py contains sendRawTransaction. I did not run it; this review did not need it. Nothing was edited in the repository, no key was handled, nothing was sent.

**The slot, from the code.** There is one slot, state["position"]. A live position of either family skips the other's live fire as "position open" (_fire 1638-1641). Only a dry front position is ever dropped for a live fire.
- c1 fires only on its first trigger buy, so a blocked trigger loses that pool (on_wave_call: first_buy is set once).
- v3crowd retries for fire_max 2 blocks (ingest 2694-2699).
- A c1 trade then keeps every front fire waiting during its pull check (front_settling, 1673), and that includes V3. A V3 pull check (v3_settling, 1675) waits only V3 fires, as test H1 confirms.

**What each loses, at 9.7 blocks/s.**
- A v3crowd trade holds the slot about 8.5 s (sell at launch+78, landing +80, then the receipts). At 115-133 launches a day that is 1.1-1.3% of the day, about 0.6-0.7 of c1's roughly 54 triggers a day, or about 1-1.4 of C-1's 100 attempts.
- A c1 trade blocks V3 for about 7 s: about 3.6 s in the slot plus about 3.5 s of pull check (PULL_WATCH_S 3). That is about 0.45% of the day, about 0.5 v3crowd launches a day, or about 0.5 per 100 fills.
- These figures assume the two lines' launches are independent. Step 0's overlap line measures the real overlap from the box's log.

**The nonce stream.** It is safe. Fires are sequential. A c1 fire during a V3 pull check takes nonce+2, and _settle_v3 keeps the larger of the chain's and the engine's count when the trade is released (2181-2183). fee_loop reads the V3 relay's balance only while no trade or pull check is open.

**Halts.**
- c1's pull halt writes HALTED.front.c1 (c1 is listed, not the base line).
- v3crowd's pull, sold-none and streak halts are its own.
- These are front-wide: a sold-none on any v4 trade (_settle 2015-2017), a V3 sell with no receipt (2159-2160), and the base v2.433 line's halts.

**The day.** A live V3 trade checks front's stop, then its own (1644-1651). V3 trades count only in the V3 day (restore 1002-1005, settle 2176). The coupling runs one way, from c1 and v2.433 to V3. At the box's documented 100 it is nil.

**The streak halt.** It is per family. v3crowd sets 30; c1 sets 0 (off). FRONT_NONBOT_HALT applies only to families that set none: v2.433, v3.0, and p356, which cannot set one.

**V3_SELL_CHECK=0.** It changes only crowd V3 families that say dry_run false, which today means v3crowd. p356 is still sell-checked whenever it is live (1511, 1659), and it is dry_run true. With RELAY_V3 set, the parser stops forcing V3 families dry (480/490, 539/551). I confirmed with the engine's parser on a synthetic copy of the box's list:
- v3crowd v3_live True, stake 0.002, nonbot_halt 30;
- p356 v3_live False;
- c1 nonbot_halt 0;
- v2.433 is the base family.

**The stake and funding.** The stake is min(0.002, 0.004 cap) = 0.002. 0.005 ETH in the relay leaves 0.003 after a -100% trade, and the pull or sold-none halt stops the family after one stake. Two full losses leave it under the stake, and fires then skip. The wallet keeps about 0.0086 ETH for gas, enough for about 1.5e-3 ETH a day for both probes.

**Order of operations.** Stop, deploy, fund, edit, start is safe: relay_v3_deploy.py and relay_ops.py refuse while the service is active, and the stop waits for v3_settling (2250).

**Tested.** I ran the corrected snippets (step 0, step 6, step 7's print, step 10, and the overlap line) on a synthetic env file and synthetic log lines. They worked, they refuse cleanly, and the Off command's heredoc chain starts the engine again even when the edit is refused.

### Corrected steps (as proposed)

v3crowd $5 probe: box commands (corrected; the owner has not approved this probe yet)

When: after C-1's probe ends (c1 halted on a pull, or 100 attempts and stopped by hand). Read C-1's result first. If that operator pulled at or under 30 blocks, review before spending: the two lines probably share an operator, and every trade of both probes comes from the same wallet. If the owner runs both at once anyway, the same steps apply, plus the 'only if C-1 is still running' rule in step 9.

Preconditions:
- The line is launching (the overlap line in step 0 counts v3crowd launches over 48 h).
- No open trade in results.py.
- All commands run on the box.

0. Read only, nothing changes. Print the real stops, each family's dry_run as written in the file, front's day, and how often the two lines overlap:

    sudo grep -E '^(FRONT_DAILY_STOP_USD|FRONT_NONBOT_HALT|V3_STAKE_CAP_ETH|V3_DAILY_STOP_USD|V3_GAS|V3_SELL_CHECK|RELAY_V3|RELAY_V3_CODEHASH|PULL_WATCH_S)=' /etc/flip/engine.env; sudo python3 -c 'import json; l = [x for x in open("/etc/flip/engine.env").read().splitlines() if x.startswith("FRONT_FAMILIES=")]; v = l[-1].split("=", 1)[1].strip(); v = v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\x27\"" else v; print("FRONT_FAMILIES in the file:", [(f.get("name"), f.get("dex", "v4"), "launch-rule" if "launch" in f else "", "dry_run", f.get("dry_run")) for f in json.loads(v)])'
    sudo python3 ~/v2pons/deploy/englog.py 48 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json, time; s = json.loads(sys.stdin.read()); r = s.get("today_restored") or {}; print("last start", round((time.time() - s["t"]) / 60), "min ago | FRONT_DAILY_STOP_USD", s.get("front_daily_stop_usd"), "| FRONT_NONBOT_HALT", s.get("front_nonbot_halt"), "| V3_DAILY_STOP_USD", s.get("v3_daily_stop_usd"), "| halted", s.get("halted"), s.get("front_halted"), s.get("fam_halted"))'
    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"flow"' | tail -1 | python3 -c 'import sys, json, time; f = json.loads(sys.stdin.read()); print("flow", round(time.time() - f["t"]), "s ago | front day $", f.get("front_pnl_today_usd"), "| v3 today", f.get("v3_today"), "$", f.get("v3_pnl_today_usd"), "| halted", f.get("halted"), f.get("front_halted"), f.get("fam_halted"))'
    sudo python3 ~/v2pons/deploy/englog.py 48 | grep -E '"fam":"(c1|v3crowd)"' | python3 -c 'import sys, json, bisect; ev = [json.loads(l) for l in sys.stdin]; v3 = sorted(e["seq"] for e in ev if e.get("ev") == "armed" and e.get("fam") == "v3crowd" and e.get("eligible")); c1 = sorted(e["seq"] for e in ev if e.get("ev") == "first_buy" and e.get("fam") == "c1" and e.get("trigger") and e.get("offset", 999) <= 100); n = lambda xs, a, b: bisect.bisect_right(xs, b) - bisect.bisect_left(xs, a); print("last 48 h: v3crowd launches", len(v3), "| c1 triggers by +100", len(c1), "| c1 triggers inside a v3crowd hold (launch to +85):", sum(n(c1, s, s + 85) for s in v3), "| v3crowd launches inside a c1 hold and pull check (trigger to +75):", sum(n(v3, s, s + 75) for s in c1))'

   It must show:
   - every V3 family (v3crowd, p356) with dry_run True in the file. A V3 family that says False would trade live as soon as RELAY_V3 is set: stop.
   - FRONT_DAILY_STOP_USD as the engine reads it. The code's default is 5; HANDOFF says the box set 100.
   - front's day above minus that value. At or under it, c1 and v3crowd both skip with "daily stop" until 00:00 UTC.
   - the two overlap counts. Expect about 1% of each line if the two lines are independent; much more means their launches are linked in time.

1. Pull and check the code. It must print `76`:

    cd ~/v2pons && git pull -q --ff-only && git log --oneline -1 && { git diff --quiet 695b25e HEAD -- src/flip_engine.py src/v4math.py deploy/englog.py deploy/results.py tests/test_engine.py contracts/FlipRelayV3.sol contracts/FlipRelayV3.json deploy/relay_v3_deploy.py deploy/relay_v3_sim.py deploy/relay_ops.py || { echo 'engine or relay code changed after the reviewed 695b25e: stop here'; false; }; } && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c '^ok'

2. Simulate the relay; nothing is sent. It must end `all as expected`. Exit 2 means no live pool was found: rerun with `--hours 48`.

    /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py

3. Stop the engine. Run results.py first and check no trade is open:

    sudo python3 ~/v2pons/deploy/results.py | head -4 && sudo systemctl stop flip-engine

   From here until step 7 the engine is stopped, so C-1's probe is paused. If you stop at any of steps 4-6, start the engine again so C-1 goes on. The RELAY_V3 lines change nothing while v3crowd says dry_run true:

    sudo systemctl start flip-engine

4. Deploy the V3 relay. Type `yes` when asked.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py --write-env

   It must print:
   - `matches the artifact byte for byte`;
   - `owner() == wallet ok`;
   - `equal, ok` on the simulated buy;
   - the two lines `RELAY_V3=0x...` and `RELAY_V3_CODEHASH=0x...`.

   `MISMATCH`, `reverted` or `DO NOT USE` means stop, then start the engine again (step 3). `no live V3 WETH pool` is acceptable if step 2 passed.

5. Fund the relay with 0.005 ETH. That covers the 0.002 stake after one loss.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.005
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status

6. Edit the env file with the engine still stopped. The snippet refuses on any mismatch and then changes nothing, V3_SELL_CHECK included. It keeps the old file as engine.env.bak.v3crowd, which leaves C-1's engine.env.bak alone.

    cd ~/v2pons && sudo python3 - <<'PY'
    import json, os, re, shutil
    os.umask(0o077)
    P = "/etc/flip/engine.env"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
    lines = open(P).read().splitlines()
    val = lambda k: ([l.split("=", 1)[1].split(" #", 1)[0].strip().strip("'\"") for l in lines if l.startswith(k + "=")] or [""])[-1]
    assert re.fullmatch("0x[0-9a-fA-F]{40}", val("RELAY_V3")) and re.fullmatch("0x[0-9a-fA-F]{64}", val("RELAY_V3_CODEHASH")), "RELAY_V3 / RELAY_V3_CODEHASH missing in " + P + " (step 4 writes them): nothing changed"
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v); old = json.loads(v)
    mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "v3crowd"] if isinstance(fams, list) else []
    assert len(mine) == 1, "v3crowd is not in FRONT_FAMILIES exactly once: nothing changed"
    f = mine[0]
    assert f.get("dex") == "v3" and str(f.get("target", "")).lower() == NPM and int(f.get("calldata_len", 0)) == 836 and int(f.get("fee", 0)) == 100, "v3crowd is not the PositionManager 836-byte fee-100 family: nothing changed"
    assert int(f.get("hold_blocks", 0)) == 78 and int(f.get("exit_after_blocks", 0)) == 18, "v3crowd's cap and clock are not 78 and 18 as replayed: nothing changed"
    assert f.get("dry_run", True) is not False, "v3crowd is already live: nothing changed"
    other = [g.get("name") for g in fams if g is not f and isinstance(g, dict) and (g.get("dex") == "v3" or "launch" in g) and g.get("dry_run", True) is False]
    assert not other, "with RELAY_V3 set these V3 families would trade live too: " + str(other) + ": nothing changed"
    f["stake_eth"] = 0.002; f["nonbot_halt"] = 30; f["dry_run"] = False
    assert [g for g in fams if g is not f] == [g for g in old if g.get("name") != "v3crowd"], "another family would change: nothing changed"
    shutil.copy2(P, P + ".bak.v3crowd")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
    sc = [k for k, l in enumerate(lines) if l.startswith("V3_SELL_CHECK=")]
    for k in sc:
        lines[k] = "V3_SELL_CHECK=0"
    if not sc:
        lines.append("V3_SELL_CHECK=0")
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("v3crowd now:", json.dumps({k: f.get(k) for k in ("stake_eth", "nonbot_halt", "dry_run", "hold_blocks", "exit_after_blocks", "take_profit")}), "| V3_SELL_CHECK=0")
    print("families:", [(g.get("name"), g.get("dex", "v4"), "dry" if g.get("dry_run") else "LIVE") for g in fams])
    print("as set in the file (unset = the code's default):", {k: val(k) or "unset" for k in ("FRONT_DAILY_STOP_USD", "FRONT_NONBOT_HALT", "V3_STAKE_CAP_ETH", "V3_DAILY_STOP_USD", "V3_GAS")})
    PY

   Expected result:
   - RELAY_V3 and RELAY_V3_CODEHASH, written by step 4;
   - V3_SELL_CHECK=0;
   - v3crowd with stake_eth 0.002, nonbot_halt 30 and dry_run false;
   - p356 and v3.0 dry, c1 as before.

   On a refusal, start the engine again (step 3).

   Leave these unchanged:
   - V3_STAKE_CAP_ETH (0.004), V3_DAILY_STOP_USD (10) and V3_GAS (500000);
   - FRONT_DAILY_STOP_USD and FRONT_NONBOT_HALT, at the values step 0 printed.

   At 100, front's stop is no brake on either probe. V3_DAILY_STOP_USD ($10) and the family's pull halt bound v3crowd's day. A V3 loss never counts in front's day, so it never stops c1.

7. Start the engine and check the start line:

    sudo systemctl start flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json, time; s = json.loads(sys.stdin.read()); r = s.get("today_restored") or {}; print("start", round(time.time() - s["t"]), "s ago | relay_v3:", s.get("relay_v3"), "verified:", s.get("relay_v3_live"), "checked:", s.get("relay_v3_codehash_set"), "owner:", s.get("relay_v3_owner"), "eth:", s.get("relay_v3_eth"), "cap:", s.get("v3_stake_cap_eth"), "sell check:", s.get("v3_sell_check"), "| family error:", s.get("front_family_error"), "| halted:", s.get("halted"), "front:", s.get("front_halted"), "families:", s.get("fam_halted")); print("FRONT_DAILY_STOP_USD", s.get("front_daily_stop_usd"), "| front day $", r.get("front_pnl_today_usd"), "| V3_DAILY_STOP_USD", s.get("v3_daily_stop_usd"), "| V3 day", s.get("v3_today"), "trades $", s.get("v3_pnl_today_usd"), "| FRONT_NONBOT_HALT", s.get("front_nonbot_halt"), "| streaks", s.get("front_nonbot_streak"), "| wallet ETH", s.get("wallet_eth")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"], "live", f.get("live"), "stake", f.get("live_stake_eth", f.get("stake_eth")), "hold", f["hold_blocks"], "exit", f.get("exit_after_blocks")) for f in s["front_families"]]'
    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"alarm"' | tail -3 | cut -c1-300

   It must show:
   - start a few seconds ago;
   - `verified: True` and `checked: True`;
   - owner = WALLET, eth about 0.005, `cap: 0.004`;
   - `sell check: False` and `family error: None`;
   - `halted: None` and `front: None`;
   - families: `{}`, or c1 alone if C-1's probe halted it;
   - FRONT_DAILY_STOP_USD as in step 0, with front's day above minus that value, and V3_DAILY_STOP_USD 10.0 with the V3 day at 0;
   - `v3crowd v3 dry_run False live True stake 0.002 hold 78 exit 18`;
   - p356 dry_run True live False, and every other family as before.

   If anything else shows, turn it off (step 10).

8. About a minute later, check the new run's flow line:

    sleep 75; sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"flow"' | tail -1 | python3 -c 'import sys, json, time; f = json.loads(sys.stdin.read()); print("flow", round(time.time() - f["t"]), "s ago | front day $", f.get("front_pnl_today_usd"), "| v3 today", f.get("v3_today"), "$", f.get("v3_pnl_today_usd"), "| V3 relay ETH", f.get("relay_v3_eth"))'

   The V3 relay ETH must be about 0.005; `None` means this is still the old run's line. If front's day is at or under minus the FRONT_DAILY_STOP_USD from step 7, the live V3 fires (and c1's) skip with "daily stop" until 00:00 UTC. That is expected; do not raise the stop.

9. At each look, run `sudo python3 ~/v2pons/deploy/results.py | head -30` and this probe check:

    sudo python3 ~/v2pons/deploy/englog.py 200 | grep '"ev":"trade_done"' | grep '"fam":"v3crowd"' | python3 -c 'import sys, json; d = [json.loads(l) for l in sys.stdin]; d = [e for e in d if e.get("ev") == "trade_done" and e.get("dex") == "v3" and e.get("dry") is False]; f = [e for e in d if isinstance(e.get("buy"), dict) and e["buy"].get("eth_in")]; L = lambda e, k: None if e.get(k) is None or e.get("buy_offset") is None else e["trig_seq"] + e["buy_offset"] + e[k] - e["launch_seq"]; near = [e for e in f if L(e, "pull_after_buy_blocks") is not None and L(e, "pull_after_buy_blocks") <= 90]; crowd = sum(1 for e in f if str(e.get("sell_why", "")).startswith("the crowd")); late = sum(1 for e in f if (e.get("buy_offset") or 0) > 3); pnl = sum(e.get("pnl_usd") or 0 for e in d); print("v3crowd probe: settled", len(d), "| filled", len(f), "| crowd-clock exits", crowd, "| buy landed after +3:", late, "| pull check failed:", sum(1 for e in d if e.get("pull_check")), "| pulled before our sell:", sum(1 for e in f if e.get("pulled_before_sell")), "| pulled by launch+90:", len(near), "| $ after gas %+.2f" % pnl, "| streak", (f[-1].get("nonbot_streak") if f else None)); [print("  pull at launch+%s, our sell landed at launch+%s, before our sell: %s, %s" % (L(e, "pull_after_buy_blocks"), L(e, "sell_after_buy_blocks"), e.get("pulled_before_sell"), str(e.get("sell_why"))[:40])) for e in near]'

   The engine stops v3crowd alone (HALTED.front.v3crowd; c1 goes on) on:
   - a pull at or before our sell;
   - a buy that filled with a sell that sold none of it;
   - 30 filled trades in a row under +2% (its own nonbot_halt; FRONT_NONBOT_HALT does not apply to it).

   The engine stops all of front, c1 included (HALTED.front), on:
   - a V3 buy that filled whose sell has no receipt;
   - a c1 buy that filled whose sell sold none;
   - a halt of the v2.433 base line.

   It skips v3crowd's fires with no halt on:
   - a V3 day at -$10 (V3_DAILY_STOP_USD);
   - front's day at minus the FRONT_DAILY_STOP_USD that step 7 printed;
   - the V3 relay holding under 0.002 ETH;
   - c1's pull check still running (about 3.5 s after each c1 trade). A V3 pull check never holds a c1 fire.

   A c1 pull halt (HALTED.front.c1) stops c1 alone.

   Stop it by hand when:
   - "pulled by launch+90" is above 0;
   - crowd-clock exits are 1 or fewer at 30 filled trades, or 3 or fewer at 50 (the baseline is 18%);
   - "buy landed after +3" reaches 2;
   - filled reaches 100: stop and review.

   Only if C-1's probe is still running: also stop v3crowd by hand when C-1's probe check shows "pulled at buy+40 or sooner" above 0, or c1 halts on a pull. The two lines probably share an operator and share our wallet. Read the two probes separately.

   If "pull check failed" is above 0, check that pool's first Burn by hand.

   To stop by hand:

    echo "v3crowd probe stopped by hand" | sudo tee /var/log/flip/HALTED.front.v3crowd >/dev/null && sudo systemctl restart flip-engine

   While v3crowd is live, do not restore /etc/flip/engine.env.bak (C-1's backup) wholesale: it predates RELAY_V3.

10. Off. This makes v3crowd dry, restores V3_SELL_CHECK=1 and withdraws the V3 relay's ETH. The engine starts again either way, so C-1 goes on. The backup goes to engine.env.bak.v3crowd-off, and C-1's engine.env.bak is untouched.

    sudo systemctl stop flip-engine && sudo python3 - <<'PY' && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw_v3; sudo systemctl start flip-engine
    import json, os, shutil
    os.umask(0o077)
    P = "/etc/flip/engine.env"
    lines = open(P).read().splitlines()
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v)
    mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "v3crowd" and f.get("dex") == "v3"]
    assert len(mine) == 1, "v3crowd is not one V3 family of FRONT_FAMILIES: nothing changed"
    mine[0]["dry_run"] = True
    shutil.copy2(P, P + ".bak.v3crowd-off")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
    lines = ["V3_SELL_CHECK=1" if l.startswith("V3_SELL_CHECK=") else l for l in lines]
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("families:", [(g.get("name"), g.get("dex", "v4"), "dry" if g.get("dry_run") else "LIVE") for g in fams], "| V3_SELL_CHECK=1")
    PY

   Then run step 7's check. It must show `v3crowd v3 dry_run True live False`, `sell check: True`, and c1 as before. Then run `relay_ops.py status`: the V3 relay should be at about 0 ETH.
