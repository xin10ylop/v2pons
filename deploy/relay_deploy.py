#!/usr/bin/env python3
"""relay_deploy.py: put the FlipRelay (contracts/FlipRelay.sol) on Robinhood Chain from the flip wallet.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_deploy.py [--yes] [--write-env]

Stop the engine first (sudo systemctl stop flip-engine): it and this script would race for the same nonce; the script refuses to
run while the service is active. Reads PRIVATE_KEY, WALLET and RPC_URL from /etc/flip/engine.env, checks that the artifact was
compiled from the source beside it, estimates the gas, asks for a yes, deploys with the PoolManager as the constructor argument,
waits for the receipt, checks the code byte for byte with the immutables filled in, reads owner() and pm() back, runs one
simulated buy through the new relay on the operator's latest unpulled pool, and prints (or writes) the RELAY= line."""
import argparse, hashlib, json, os, subprocess, sys, time, urllib.request
from eth_account import Account
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import relay_sim, v4math
ENV = "/etc/flip/engine.env"; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PM = relay_sim.PM
word = relay_sim.word


def env():
    d = {}
    for line in open(ENV):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); d[k.strip()] = v.split(" #", 1)[0].strip()
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--yes", action="store_true"); ap.add_argument("--write-env", action="store_true"); a = ap.parse_args()
    if subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"]).returncode == 0:
        sys.exit("the flip engine is running: sudo systemctl stop flip-engine first (same wallet, same nonce)")
    e = env(); key = e.get("PRIVATE_KEY"); wallet = e.get("WALLET", "").lower(); relay_sim.RPC = e.get("RPC_URL") or relay_sim.RPC
    if not key or not wallet:
        sys.exit(f"PRIVATE_KEY or WALLET missing in {ENV}")
    acct = Account.from_key(key)
    if acct.address.lower() != wallet:
        sys.exit(f"the key in {ENV} is for {acct.address}, WALLET says {wallet}")
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelay.json"))); src = open(os.path.join(ROOT, "contracts", "FlipRelay.sol")).read()
    if hashlib.sha256(src.encode()).hexdigest() != art["source_sha256"]:
        sys.exit("contracts/FlipRelay.json was not compiled from contracts/FlipRelay.sol: python3 contracts/compile.py first")
    rpc = relay_sim.rpc; data = art["bytecode"] + word(PM)
    bal = int(rpc("eth_getBalance", [wallet, "latest"]), 16); gp = int(rpc("eth_gasPrice", []), 16); nonce = int(rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    gas = int(rpc("eth_estimateGas", [{"from": wallet, "data": data}]), 16); gas_lim = int(gas * 1.3); cost = gas_lim * gp * 2 / 1e18
    print(f"wallet {wallet}: {bal / 1e18:.5f} ETH; deploy needs about {gas} gas at {gp / 1e9:.4f} gwei: at most {cost:.6f} ETH")
    if bal < gas_lim * gp * 2:
        sys.exit("not enough ETH for the deployment")
    if not a.yes and input("deploy the FlipRelay now? (yes/no) ").strip().lower() != "yes":
        sys.exit("not deployed")
    tx = {"data": data, "value": 0, "gas": gas_lim, "gasPrice": gp * 2, "nonce": nonce, "chainId": 4663}
    h = rpc("eth_sendRawTransaction", ["0x" + bytes(acct.sign_transaction(tx).raw_transaction).hex()]); print("sent", h); rec = None; t0 = time.time()
    while time.time() - t0 < 120 and rec is None:
        time.sleep(1.5); rec = rpc("eth_getTransactionReceipt", [h])
    if rec is None:
        sys.exit("no receipt after two minutes: check the hash on the explorer before trying again")
    if rec.get("status") != "0x1":
        sys.exit(f"the deployment reverted (block {int(rec['blockNumber'], 16)}); nothing to use")
    relay = rec["contractAddress"].lower(); print(f"deployed at {relay} in block {int(rec['blockNumber'], 16)}, gas used {int(rec['gasUsed'], 16)}")
    code = rpc("eth_getCode", [relay, "latest"]); expected = relay_sim.relay_runtime(wallet)
    owner = rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"]); pm = rpc("eth_call", [{"to": relay, "data": "0x8970cdff"}, "latest"])
    ok_code = code.lower() == expected.lower(); ok_owner = ("0x" + owner[-40:]).lower() == wallet; ok_pm = ("0x" + pm[-40:]).lower() == PM
    print(f"code on the chain {len(code) // 2 - 1} bytes {'matches the artifact' if ok_code else 'UNEXPECTED'}; owner() {'== wallet ok' if ok_owner else 'is 0x' + owner[-40:] + ': DO NOT USE'}; pm() {'ok' if ok_pm else 'WRONG'}")
    if not (ok_code and ok_owner and ok_pm):
        sys.exit(1)
    try:
        pid = relay_sim.latest_operator_pool(); key, sqrt_p, liq, b0, n = relay_sim.pool_state(pid); amt = 10 ** 14
        data_buy = "0x5ed06f60" + word(key["currency0"]) + word(key["currency1"]) + word(key["fee"]) + word(key["tickSpacing"]) + word(key["hooks"]) + word(amt) + word(0) + word(0)
        r = rpc("eth_call", [{"from": wallet, "to": relay, "data": data_buy}, "latest", {relay: {"balance": hex(10 ** 16)}}], tries=2)
        got = int(r, 16); exp = v4math.buy_out_int(sqrt_p, liq, amt, key["fee"])
        rel = (got - exp) / exp if exp else float("inf")
        verdict = "ok" if abs(rel) < 1e-9 else "MISMATCH: do not use the relay"
        print(f"simulated buy through the relay on pool {pid[:14]} (fee {key['fee'] / 1e4:g}%): {got:.6g} tokens, v4math predicted {exp:.6g} ({rel:+.1e} relative: {verdict})")
    except (Exception, SystemExit) as ex:                                          # (no pool to try it on is SystemExit: the RELAY= line must still be written)
        print(f"the simulated buy did not go through ({str(ex)[:160]}); the pool may have been pulled; try deploy/relay_sim.py <poolId>")
    if a.write_env:
        lines = [l for l in open(ENV).read().splitlines() if not l.startswith("RELAY=")] + [f"RELAY={relay}"]
        tmp = ENV + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); os.chmod(tmp, 0o600); os.replace(tmp, ENV)
        print(f"\nRELAY={relay} written to {ENV}. Next: deploy/relay_ops.py deposit <eth> (the stake), then sudo systemctl start flip-engine")
    else:
        print(f"\nadd to {ENV}, then deposit the stake and start the engine:\nRELAY={relay}")


if __name__ == "__main__":
    main()
