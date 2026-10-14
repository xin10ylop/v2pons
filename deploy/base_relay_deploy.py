#!/usr/bin/env python3
"""base_relay_deploy.py: put the FlipRelay (contracts/FlipRelay.sol, unchanged) on Base from the Base line's wallet (BASE_WALLET, its key in
/etc/flip/base.key: deploy/base_wallet.py).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_relay_deploy.py --check        # every check and the cost; nothing is sent
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_relay_deploy.py --write-env    # the deployment (asks for a typed yes), BASE_RELAY= written
    python3 deploy/base_relay_deploy.py --check --wallet 0xADDRESS                      # the reads for any address, no key file (a look)

--check: the artifact (contracts/FlipRelay.json) was compiled from the source beside it (its sha256); the key file's address is BASE_WALLET
(/etc/flip/base.env); eth_chainId is 8453 on BASE_RPC_URL and BASE_READ_ALT_URL; the wallet's balance and nonce; eth_estimateGas of the
creation (the bytecode with Base's PoolManager as the constructor argument) from the wallet; the L1 data fee's bound; the runtime the chain
must hold afterwards (relay_runtime: the artifact's code with the PoolManager and the owner filled in); the address the relay will get; what
the deployment costs at most and at today's base fee. BASE_RELAY already set to a FlipRelay of this wallet is said (no second one needed).
The deployment (no --check): the same checks, then it refuses while flip-base is active (sudo systemctl stop flip-base first: same wallet,
same nonce) or another process holds the key file's lock (base_wallet.py's docstring), asks for a typed yes, sends a type-2 transaction on
chain 8453 (gas = the estimate x 1.3, maxFeePerGas = 2 x the base fee + the priority fee) to every BASE_SEND_URLS, waits for the receipt,
checks the code on the chain byte for byte against the expected runtime, reads owner() (must be the wallet) and pm() (must be the
PoolManager) back, and simulates a buy through the new relay (eth_call, nothing sent) on the operator's open pool, or, when none is open
(it pulls each about 4 minutes after its launch), on a live ETH-paired pool without a hook, which it names. --write-env writes
BASE_RELAY=<address> into /etc/flip/base.env (replacing any BASE_RELAY= line); without it the line is printed. Then: base_relay_sim.py,
and base_ops.py deposit (RUNBOOK 4l steps 4-5)."""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import base_wallet as BW
import base_relay_sim as BS
import relay_sim as RS
from eth_utils import keccak

PM = BS.PM
ETH_USD = float(BW.setting("BASE_ETH_USD", "2570") or 2570)


def artifact():
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelay.json"))); src = open(os.path.join(ROOT, "contracts", "FlipRelay.sol")).read()
    if hashlib.sha256(src.encode()).hexdigest() != art["source_sha256"]:
        sys.exit("contracts/FlipRelay.json was not compiled from contracts/FlipRelay.sol (sha256 differs): python3 contracts/compile.py first")
    return art


def relay_ok(relay, wallet, expected):
    """(code matches, owner() is the wallet, pm() is the PoolManager) for the address"""
    code = BW.rpc("eth_getCode", [relay, "latest"])
    if not code or len(code) <= 2:
        return False, False, False
    owner = BW.rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"]); pm = BW.rpc("eth_call", [{"to": relay, "data": "0x8970cdff"}, "latest"])
    return code.lower() == expected.lower(), ("0x" + owner[-40:]).lower() == wallet, ("0x" + pm[-40:]).lower() == PM


def main():
    ap = argparse.ArgumentParser(description="deploy FlipRelay on Base (RUNBOOK 4l step 4)")
    ap.add_argument("--check", action="store_true", help="every check and the cost; nothing sent")
    ap.add_argument("--write-env", action="store_true", help="write BASE_RELAY= into /etc/flip/base.env after the deployment")
    ap.add_argument("--wallet", help="with --check only: the reads for this address, no key file")
    ap.add_argument("--again", action="store_true", help="deploy although BASE_RELAY already holds a FlipRelay of this wallet")
    a = ap.parse_args()
    if a.wallet and not a.check:
        sys.exit("--wallet goes with --check only: a deployment is signed with the key file's wallet")
    active = BW.service_active()
    if active and not a.check:
        sys.exit(f"flip-base is running: sudo systemctl stop {BW.SERVICE} first (same wallet, same nonce), and start it again after")
    try:
        return run(a, active)
    finally:
        BW.release_key()


def run(a, active):
    art = artifact()
    print(f"artifact: contracts/FlipRelay.json compiled from contracts/FlipRelay.sol (sha256 {art['source_sha256'][:16]}…), solc {art.get('solc')}, "
          f"evm {art.get('evm')}: ok")
    if a.wallet:
        wallet = BW.address_arg(a.wallet, "--wallet"); acct = None
        print(f"wallet {wallet} (given; no key file read: a look only)")
    else:
        acct = BW.wallet_account(); wallet = acct.address.lower()
        print(f"the key file {BW.KEY_FILE} is BASE_WALLET {wallet}: ok")
    hosts = BW.rpc_urls(); BW.check_chain()
    print(f"chain id {BW.CHAIN_ID} (Base) at {', '.join(BW.host(u) for u in hosts)}: ok; sends go to {', '.join(BW.host(u) for u in BW.send_urls())}")
    expected = RS.relay_runtime(wallet)
    print(f"the runtime the chain must hold: {len(expected) // 2 - 1:,} bytes (owner {wallet}, PoolManager {PM} filled in), keccak "
          f"0x{keccak(bytes.fromhex(expected[2:])).hex()[:16]}…")
    old = (BW.setting("BASE_RELAY") or "").lower()
    if old:
        oc, oo, op = relay_ok(old, wallet, expected)
        if oc and oo and op:
            print(f"BASE_RELAY {old} is already a FlipRelay of this wallet (code, owner, pm ok): no second deployment is needed"
                  + ("" if a.again else "; --again deploys another anyway"))
            if not a.check and not a.again:
                sys.exit(0)
        else:
            print(f"BASE_RELAY {old} in {BW.ENV_FILE} is NOT a FlipRelay of this wallet (code {'ok' if oc else 'differs'}, owner {'ok' if oo else 'not the wallet'}, "
                  f"pm {'ok' if op else 'wrong'}): the deployment replaces the line (with --write-env)")
    data = art["bytecode"] + BS.word(PM)
    bal = BW.balance(wallet); nonce = int(BW.rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    base, prio, mx = BW.fees()
    gas = int(BW.rpc("eth_estimateGas", [{"from": wallet, "data": data}]), 16); gas_lim = int(gas * 1.3)
    l1 = BW.l1_fee_bound(len(data) // 2 + 120)
    worst = gas_lim * mx + l1; today = gas * (base + prio) + l1
    import rlp
    addr = "0x" + keccak(rlp.encode([bytes.fromhex(wallet[2:]), nonce]))[12:].hex()
    print(f"wallet {wallet}: {bal / 1e18:.6f} ETH (${bal / 1e18 * ETH_USD:.2f}), nonce {nonce}; the relay will be at {addr}")
    print(f"the deployment: {len(data) // 2 - 1:,} bytes of creation code, eth_estimateGas {gas:,} (limit {gas_lim:,}); base fee {base / 1e9:.4f} gwei, "
          f"priority {prio / 1e9:.4f}, maxFeePerGas {mx / 1e9:.4f}; L1 data fee at most {l1 / 1e18:.9f} ETH")
    print(f"cost: about {today / 1e18:.8f} ETH (${today / 1e18 * ETH_USD:.4f}) at today's base fee, at most {worst / 1e18:.8f} ETH "
          f"(${worst / 1e18 * ETH_USD:.4f})")
    short = bal < gas_lim * mx + 2 * l1
    if short:
        print(f"NOT ENOUGH ETH: the wallet needs at least {(gas_lim * mx + 2 * l1) / 1e18:.8f} ETH for the deployment (RUNBOOK 4l step 3: about 0.012 ETH)")
    if a.check:
        if active:
            print(f"(flip-base is active: the deployment itself refuses until sudo systemctl stop {BW.SERVICE})")
        print("--check: nothing sent." + ("" if short else " The deployment is the same command with --write-env in place of --check."))
        sys.exit(1 if short else 0)
    if short:
        sys.exit("nothing sent")
    BW.guard(any_mode=True)
    if BW.ask(f"deploy the FlipRelay on Base from {wallet} now (at most {worst / 1e18:.8f} ETH)? type yes: ").strip().lower() != "yes":
        sys.exit("not deployed")
    raw, h = BW.sign(acct, {"nonce": nonce, "maxFeePerGas": mx, "maxPriorityFeePerGas": prio, "gas": gas_lim, "value": 0, "data": data})
    BW.send_raw(raw, h)
    rec = BW.wait_receipt(h, 120)
    if rec is None:
        sys.exit("no receipt after two minutes: look at the hash on basescan before trying again (a second run would deploy a second relay)")
    if int(rec.get("status") or "0x0", 16) != 1:
        sys.exit(f"the deployment reverted (block {int(rec['blockNumber'], 16)}): nothing to use")
    relay = (rec.get("contractAddress") or "").lower()
    print(f"deployed at {relay} in block {int(rec['blockNumber'], 16)}   {BW.EXPLORER}/address/{relay}")
    ok_code, ok_owner, ok_pm = relay_ok(relay, wallet, expected)
    print(f"code on the chain {'matches the artifact (owner and PoolManager filled in)' if ok_code else 'UNEXPECTED'}; owner() "
          f"{'== wallet: ok' if ok_owner else 'is not the wallet: DO NOT USE'}; pm() {'== PoolManager: ok' if ok_pm else 'WRONG: DO NOT USE'}")
    if not (ok_code and ok_owner and ok_pm):
        sys.exit(1)
    sim = BS.buy_through(relay, wallet)
    if sim is False:
        print("the simulated buy did not pass: do not deposit yet; run base_relay_sim.py and paste both outputs")
    if a.write_env:
        BW.set_env(BW.ENV_FILE, "BASE_RELAY", relay)
        print(f"\nBASE_RELAY={relay} written to {BW.ENV_FILE}. Next: base_relay_sim.py, then base_ops.py deposit 0.004 (RUNBOOK 4l steps 4-5)")
    else:
        print(f"\nadd this line to {BW.ENV_FILE} (do not run the deployment again: it would deploy a second relay):\nBASE_RELAY={relay}")


if __name__ == "__main__":
    main()
