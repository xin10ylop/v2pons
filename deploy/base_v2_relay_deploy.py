#!/usr/bin/env python3
"""base_v2_relay_deploy.py: put the FlipRelayV2 (contracts/FlipRelayV2.sol, unchanged) on Base from the V2 line's wallet (BASE_V2_WALLET, its
key in /etc/flip/base_v2.key: deploy/base_wallet.py create /etc/flip/base_v2.key /etc/flip/base_v2.env).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_relay_deploy.py --check        # every check and the cost; nothing is sent
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_relay_deploy.py --write-env    # the deployment (asks for a typed yes), BASE_V2_RELAY= written
    python3 deploy/base_v2_relay_deploy.py --check --wallet 0xADDRESS                      # the reads for any address, no key file (a look)

--check: the artifact (contracts/FlipRelayV2.json) was compiled from the source beside it (its sha256) and its runtime is what solc 0.8.26
compiles from that source now (base_v2_relay_sim.relay_runtime); the key file's address is BASE_V2_WALLET (/etc/flip/base_v2.env);
eth_chainId is 8453 on BASE_V2_RPC_URL and BASE_V2_READ_ALT_URL; the wallet's balance and nonce; eth_estimateGas of the creation (the bytecode
with the constructor's (router, weth): BASE_V2_ROUTER, BASE_V2_WETH) from the wallet; the L1 data fee's bound; the runtime the chain must
hold afterwards (the artifact's code with owner, router and weth filled into the immutables); the address the relay will get; what the
deployment costs at most and at today's base fee. BASE_V2_RELAY already set to a FlipRelayV2 of this wallet is said (no second one needed).
The deployment (no --check): the same checks, then it refuses while flip-base-v2 is active (sudo systemctl stop flip-base-v2 first: same
wallet, same nonce) or another process holds the key file's lock (base_wallet.py's docstring), asks for a typed yes, sends a type-2
transaction on chain 8453 (gas = the estimate x 1.3, maxFeePerGas = 2 x the base fee + the priority fee) to every BASE_V2_SEND_URLS, waits
for the receipt, checks the code on the chain byte for byte against the expected runtime, reads owner() (must be the wallet), router() and
weth() (must be the settings) back, and simulates a round trip through the deployed relay (base_v2_relay_sim.deployed_round_trip: the
relay's real code, no code override, nothing sent) on the newest pair of the line, a live one at the head, else the newest pulled one 30
blocks after its Mint; a call from another address must be refused NotOwner. --write-env writes BASE_V2_RELAY=<address> into
/etc/flip/base_v2.env (replacing any BASE_V2_RELAY= line); without it the line is printed. Then base_v2_ops.py deposit (RUNBOOK 4m step 7)."""
import argparse, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import base_v2_wallet as BV
import base_v2_relay_sim as BS
import base_v2_sim as S2
from eth_utils import keccak
BW = BV.BW
ETH_USD = float(BV.setting("BASE_V2_ETH_USD", "2570") or 2570)
CREATOR_NONCE = int(BV.setting("BASE_V2_CREATOR_NONCE", "2") or 2)


def artifact():
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelayV2.json"))); src = open(os.path.join(ROOT, "contracts", "FlipRelayV2.sol")).read()
    if hashlib.sha256(src.encode()).hexdigest() != art["source_sha256"]:
        sys.exit("contracts/FlipRelayV2.json was not compiled from contracts/FlipRelayV2.sol (sha256 differs): python3 contracts/compile.py FlipRelayV2 first")
    return art


def archive_url():
    return BV.setting("BASE_V2_ARCHIVE_URL") or S2.RPC


def line_pair(url, back):
    """the newest pair of the line (deploy/base_v2_sim.py's pick with the creator at BASE_V2_CREATOR_NONCE): a live one at the head, else the
    newest pulled one 30 blocks after its Mint: (the pair's record, the block tag), or (None, None)"""
    found = [p for p in S2.recent_pairs(url, back, 1.0) if p.get("nonce") == CREATOR_NONCE]
    live = [p for p in found if not p.get("burn")]
    p = (live or found)[-1] if found else None
    return p, (None if p is None else "latest" if not p.get("burn") else hex(p["bn"] + 30))


def simulate(relay, wallet):
    """the round trip through the deployed relay on the newest pair of the line: True (ok), False (did not pass), None (no pair found)"""
    url = archive_url()
    try:
        p, blk = line_pair(url, 3000)
        if p is None:
            p, blk = line_pair(url, 30000)
    except Exception as e:
        print(f"the pairs of the line were not read from {BW.host(url)} ({type(e).__name__}): the round trip was not simulated; base_v2_relay_sim.py --relay {relay} later"); return None
    if p is None:
        print(f"no pair of the line in the last 30,000 blocks on {BW.host(url)}: the round trip was not simulated; base_v2_relay_sim.py --relay {relay} later"); return None
    stake = min(float(BV.setting("BASE_V2_STAKE_ETH", "0.02") or 0.02), float(BV.setting("BASE_V2_STAKE_CAP_ETH", "0.02") or 0.02)); stake_wei = int(stake * 1e18)
    r = BS.deployed_round_trip(url, relay, wallet, p["pair"], stake_wei, blk)
    where = f"{p['pair']} ({p['eth']:.2f} ETH, creator nonce {p['nonce']}, {'open' if not p.get('burn') else 'pulled at +%d' % (p['burn'] - p['bn'])}) at {blk}"
    if "error" in r:
        print(f"the round trip through the deployed relay on {where} REVERTED: {r['error']}"); return False
    ratio = r["eth_out"] / stake_wei; ok = ratio >= 0.97 and r["owner_check"].startswith("refused")
    print(f"round trip through the deployed relay on {where}: buy {stake:g} ETH -> {r['tokens']} tokens; sell -> {r['eth_out'] / 1e18:.6f} ETH "
          f"({100 * ratio:.2f}% of the stake{': ok' if ratio >= 0.97 else ': WORSE THAN -3%'}); owner check: {r['owner_check']}; via {BW.host(url)}")
    return ok


def main():
    ap = argparse.ArgumentParser(description="deploy FlipRelayV2 on Base (RUNBOOK 4m step 6)")
    ap.add_argument("--check", action="store_true", help="every check and the cost; nothing sent")
    ap.add_argument("--write-env", action="store_true", help="write BASE_V2_RELAY= into /etc/flip/base_v2.env after the deployment")
    ap.add_argument("--wallet", help="with --check only: the reads for this address, no key file")
    ap.add_argument("--again", action="store_true", help="deploy although BASE_V2_RELAY already holds a FlipRelayV2 of this wallet")
    a = ap.parse_args()
    if a.wallet and not a.check:
        sys.exit("--wallet goes with --check only: a deployment is signed with the key file's wallet")
    active = BW.service_active()
    if active and not a.check:
        sys.exit(f"{BV.SERVICE} is running: sudo systemctl stop {BV.SERVICE} first (same wallet, same nonce), and start it again after")
    try:
        return run(a, active)
    finally:
        BW.release_key()


def run(a, active):
    art = artifact(); router, weth = BV.router(), BV.weth()
    print(f"artifact: contracts/FlipRelayV2.json compiled from contracts/FlipRelayV2.sol (sha256 {art['source_sha256'][:16]}…), solc {art.get('solc')}, "
          f"evm {art.get('evm')}: ok")
    if a.wallet:
        wallet = BW.address_arg(a.wallet, "--wallet"); acct = None
        print(f"wallet {wallet} (given; no key file read: a look only)")
    else:
        acct = BW.wallet_account(); wallet = acct.address.lower()
        print(f"the key file {BV.KEY_FILE} is BASE_V2_WALLET {wallet}: ok")
    hosts = BW.rpc_urls(); BW.check_chain()
    print(f"chain id {BW.CHAIN_ID} (Base) at {', '.join(BW.host(u) for u in hosts)}: ok; sends go to {', '.join(BW.host(u) for u in BW.send_urls())}")
    expected = BV.relay_runtime(wallet, router, weth)
    compiled_now, _ = BS.relay_runtime(wallet, router, weth)                  # solc 0.8.26 from the source now, the immutables filled the same way
    if compiled_now.lower() != expected.lower():
        sys.exit("the artifact's runtime differs from what solc 0.8.26 compiles from contracts/FlipRelayV2.sol now: python3 contracts/compile.py FlipRelayV2, and paste this")
    print(f"the runtime the chain must hold: {len(expected) // 2 - 1:,} bytes (owner {wallet}, router {router}, weth {weth} filled in; solc agrees), keccak "
          f"0x{keccak(bytes.fromhex(expected[2:])).hex()[:16]}…")
    old = (BV.setting("BASE_V2_RELAY") or "").lower()
    if old:
        checks = BV.relay_check(old, wallet, expected)
        if all(checks):
            print(f"BASE_V2_RELAY {old} is already a FlipRelayV2 of this wallet (code, owner, router, weth ok): no second deployment is needed"
                  + ("" if a.again else "; --again deploys another anyway"))
            if not a.check and not a.again:
                sys.exit(0)
        else:
            print(f"BASE_V2_RELAY {old} in {BV.ENV_FILE} is NOT a FlipRelayV2 of this wallet ({BV.relay_words(*checks)}): the deployment replaces the line (with --write-env)")
    data = art["bytecode"] + S2.word(router) + S2.word(weth)
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
        print(f"NOT ENOUGH ETH: the wallet needs at least {(gas_lim * mx + 2 * l1) / 1e18:.8f} ETH for the deployment (RUNBOOK 4m step 5: about 0.03 ETH for the stages)")
    if a.check:
        if active:
            print(f"({BV.SERVICE} is active: the deployment itself refuses until sudo systemctl stop {BV.SERVICE})")
        print("--check: nothing sent." + ("" if short else " The deployment is the same command with --write-env in place of --check."))
        sys.exit(1 if short else 0)
    if short:
        sys.exit("nothing sent")
    BV.guard(any_mode=True)
    if BW.ask(f"deploy the FlipRelayV2 on Base from {wallet} now (at most {worst / 1e18:.8f} ETH)? type yes: ").strip().lower() != "yes":
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
    for i in range(10):                                                       # a load-balanced node may be a block behind the one that mined it
        checks = BV.relay_check(relay, wallet, expected)
        if all(checks):
            break
        print(f"(the node has not shown the relay's code yet: asked again, {i + 1} of 10)"); time.sleep(2)
    oc, oo, orr, ow = checks
    print(f"code on the chain {'matches the artifact (owner, router and weth filled in)' if oc else 'UNEXPECTED'}; owner() "
          f"{'== wallet: ok' if oo else 'is not the wallet: DO NOT USE'}; router() {'== BASE_V2_ROUTER: ok' if orr else 'WRONG: DO NOT USE'}; "
          f"weth() {'== BASE_V2_WETH: ok' if ow else 'WRONG: DO NOT USE'}")
    if not all(checks):
        sys.exit(f"the relay at {relay} did not check out within 20 s: nothing written. Do not deploy again; check it later with\n"
                 f"  sudo sed -i 's|^BASE_V2_RELAY=.*|BASE_V2_RELAY={relay}|' {BV.ENV_FILE} && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_ops.py status\n"
                 f"(status reads its code, owner(), router() and weth() again; use it only when all four are ok)")
    sim = simulate(relay, wallet)
    if sim is False:
        print("the round trip did not pass: do not deposit yet; run base_v2_relay_sim.py --relay and paste both outputs")
    if a.write_env:
        BW.set_env(BV.ENV_FILE, "BASE_V2_RELAY", relay)
        print(f"\nBASE_V2_RELAY={relay} written to {BV.ENV_FILE}. Next: base_v2_ops.py deposit (RUNBOOK 4m step 7)")
    else:
        print(f"\nadd this line to {BV.ENV_FILE} (do not run the deployment again: it would deploy a second relay):\nBASE_V2_RELAY={relay}")


if __name__ == "__main__":
    main()
