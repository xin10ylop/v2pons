# The C-1 $5 probe: box commands (owner-approved Oct 12; reviewed by two Opus reviewers, their fixes folded in)

Settings (REPORT_C1S_JUDGE.md): c1 hold_blocks 30, trigger max_blocks 100, take_profit 9 (off), stake 0.002 ETH, nonbot_halt 0, pin true.
Reviewed engine code: 695b25e (src/flip_engine.py, src/v4math.py, deploy/englog.py, deploy/results.py, tests/test_engine.py unchanged since).

## 1. Pull, check the engine code is the reviewed one, run the tests (expect 76)

    cd ~/v2pons && git pull -q --ff-only && git log --oneline -1 && { git diff --quiet 695b25e HEAD -- src/flip_engine.py src/v4math.py deploy/englog.py deploy/results.py tests/test_engine.py || { echo 'engine code changed after the reviewed 695b25e: stop here'; false; }; } && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c '^ok'

## 2. Edit only c1, lift its halt, restart (refuses, and restarts nothing, on any mismatch)

    git -C ~/v2pons merge-base --is-ancestor 695b25e HEAD && git -C ~/v2pons diff --quiet 695b25e HEAD -- src/flip_engine.py src/v4math.py && sudo python3 - <<'PY' && sudo rm -f /var/log/flip/HALTED.front.c1 && sudo systemctl restart flip-engine && sleep 8 && echo restarted
    import json, os, shutil
    P = "/etc/flip/engine.env"; HOLD, MAXB = 30, 100
    C1_ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
    lines = open(P).read().splitlines()
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v); old = json.loads(v)
    mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "c1"] if isinstance(fams, list) else []
    assert len(mine) == 1, "c1 is not in FRONT_FAMILIES exactly once: nothing changed"
    c1 = mine[0]; t = c1.get("trigger") or {}
    assert c1.get("dex", "v4") == "v4" and str(t.get("router", "")).lower() == C1_ROUTER, "c1 is not the C-1 trigger family: nothing changed"
    assert float(c1.get("stake_eth", 1)) <= 0.0025, "c1's stake_eth is above 0.0025 ETH (the probe is $5): nothing changed"
    assert c1.get("pin") is True and float(c1.get("take_profit", 0)) >= 9, "c1 is not pinned with the take-profit off: nothing changed"
    assert not (c1.get("hold_blocks") == HOLD and t.get("max_blocks") == MAXB), "c1 already has hold_blocks 30 and max_blocks 100: nothing changed"
    c1["hold_blocks"] = HOLD; t["max_blocks"] = MAXB; c1["nonbot_halt"] = 0
    assert [f for f in fams if f is not c1] == [f for f in old if f.get("name") != "c1"], "another family would change: nothing changed"
    shutil.copy2(P, P + ".bak")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("c1 now:", json.dumps({k: c1.get(k) for k in ("hold_blocks", "take_profit", "stake_eth", "dry_run", "pin", "nonbot_halt")}), "max_blocks", t["max_blocks"])
    print("families:", [(f.get("name"), f.get("dex", "v4"), "dry" if f.get("dry_run") else "LIVE") for f in fams])
    PY

## 3. The start line (expect: start a few seconds ago, the pulled code True, family error None, halted None, families halted {}, c1 dry_run False hold 30 tp 9.0 stake 0.002)

    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json, time; s = json.loads(sys.stdin.read()); print("start", round(time.time() - s["t"]), "s ago | release", s.get("release"), "| the pulled code:", "relay_v3_codehash_set" in s, "| family error:", s.get("front_family_error"), "| halted:", s.get("halted"), "| front halted:", s.get("front_halted"), "| families halted:", s.get("fam_halted")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"], "hold", f["hold_blocks"], "tp", f["take_profit"], "stake", f.get("stake_eth"), "trigger", f.get("trigger")) for f in s["front_families"]]'

A few minutes later, max_blocks 100 in the engine itself (must show "offset":101; 401 would mean the old 400):

    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"fam":"c1"' | grep "family's window" | tail -2 | cut -c1-200

## 4. The probe check (run at each look)

    sudo python3 ~/v2pons/deploy/englog.py 120 | grep '"fam":"c1"' | python3 -c 'import sys, json; ev = [json.loads(l) for l in sys.stdin]; fired = {(e["pid"], e["nonce"]) for e in ev if e["ev"] == "fire" and e.get("send_after") == 30}; done = [e for e in ev if e["ev"] == "trade_done" and not e.get("dry") and (e["pid"], e.get("nonce")) in fired]; near = [d for d in done if d.get("pull_after_buy_blocks") is not None and d["pull_after_buy_blocks"] <= 40]; print("c1 probe attempts:", len(fired), "| settled:", len(done), "| pull check failed:", sum(1 for d in done if d.get("pull_check")), "| pulled at buy+40 or sooner:", len(near)); [print("  pull at +%s, sold at +%s, before our sell: %s" % (d["pull_after_buy_blocks"], d.get("sell_after_buy_blocks"), d.get("pulled_before_sell"))) for d in near]'

Stop rules:
- the engine halts c1 by itself on a pull that lands before our sell (HALTED.front.c1);
- stop by hand when "pulled at buy+40 or sooner" is above 0, or attempts reach 100;
- if "pull check failed" is above 0, or settled is more than 1 behind attempts, look at that trade by hand.

The stop by hand:

    echo "c1 probe stopped by hand" | sudo tee /var/log/flip/HALTED.front.c1 >/dev/null && sudo systemctl restart flip-engine

The old c1 settings are in /etc/flip/engine.env.bak (written in step 2; any later RUNBOOK env snippet overwrites it).
