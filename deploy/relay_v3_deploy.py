#!/usr/bin/env python3
"""relay_v3_deploy.py: put FlipRelayV3 (contracts/FlipRelayV3.sol) on Robinhood Chain from the flip wallet, owned by that wallet.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py [--write-env] [--force]

Stop the engine first (sudo systemctl stop flip-engine): it and this script would race for the same nonce; the script refuses to run while
the service is active. Reads PRIVATE_KEY, WALLET and RPC_URL from /etc/flip/engine.env (the key is never printed; WALLET, a public
address, is). Refuses while the env file's RELAY_V3 (an earlier deployment) still holds ETH or WETH, unless --force (empty it first:
relay_ops.py withdraw_v3, sweep_v3 WETH). Checks that the artifact was compiled from the source beside it, estimates the deployment's gas and cost, asks for a typed yes, deploys with the wallet as the owner
(the constructor's argument), waits for the receipt, checks the code on the chain byte for byte with the owner filled in, reads owner()
back, simulates one buy through the new relay on a live V3 pool (eth_call, the relay's ETH given by state override) against QuoterV2,
and prints (or writes, with --write-env) the RELAY_V3= line and the RELAY_V3_CODEHASH= line (the keccak of the deployed runtime, which
relay_ops.py's _v3 commands check the relay's code against). --write-env keeps the previous RELAY_V3 and RELAY_V3_CODEHASH lines as
comments ("# previous ..."), and writes the file through a fresh temporary file (O_EXCL, O_NOFOLLOW, mode 600, fsynced) renamed over it.
One transaction, the deployment; nothing else is sent."""
import argparse, hashlib, json, os, subprocess, sys, time
from eth_account import Account
from eth_utils import keccak
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay_sim, relay_v3_sim as v3
ENV = "/etc/flip/engine.env"; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); word = relay_sim.word


def env():
    d = {}
    for line in open(ENV):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); d[k.strip()] = v.split(" #", 1)[0].strip()
    return d


def simulated_buy(relay, wallet, amt=10 ** 14):
    """one buy through the deployed relay on the newest live, not sell-locked V3 WETH pool of the last 3 hours, against QuoterV2 on the same block"""
    recs, head, bps = v3.recent_pools(3)
    for r in reversed(recs[-40:]):
        tok = v3.token_of(r)
        if not (v3.liquidity(r["pool"]) and v3.quote(v3.WETH, tok, amt, r["fee"], "latest")) or v3.sell_lock(r):
            continue
        blk = hex(int(relay_sim.rpc("eth_blockNumber", []), 16) - 2); ts = int(relay_sim.rpc("eth_getBlockByNumber", [blk, False])["timestamp"], 16)
        ok, res = v3.call(relay, "0x" + v3.S_BUY + word(tok) + word(r["fee"]) + word(amt) + word(0) + word(ts + 600), blk, frm=wallet, ov={relay: {"balance": hex(10 ** 16)}})
        q = v3.quote(v3.WETH, tok, amt, r["fee"], blk)
        if not ok:
            return f"the simulated buy on pool {r['pool']} reverted ({res}): do not use the relay before this is understood"
        got = relay_sim.W(res, 0)
        return (f"simulated buy of {amt / 1e18:g} ETH through the relay on pool {r['pool']} (fee {r['fee'] / 1e4:g}%, {r['family']}): {got} tokens, "
                f"QuoterV2 {q}: {'equal, ok' if got == q else 'MISMATCH: do not use the relay'}")
    return "no live V3 WETH pool in the last 3 hours to simulate a buy on; run deploy/relay_v3_sim.py 0xPOOL later"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write-env", action="store_true"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    if subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"]).returncode == 0:
        sys.exit("the flip engine is running: sudo systemctl stop flip-engine first (same wallet, same nonce)")
    e = env(); key = e.get("PRIVATE_KEY"); wallet = e.get("WALLET", "").lower(); relay_sim.RPC = e.get("RPC_URL") or relay_sim.RPC
    if not key or not wallet:
        sys.exit(f"PRIVATE_KEY or WALLET missing in {ENV}")
    acct = Account.from_key(key)
    if acct.address.lower() != wallet:
        sys.exit(f"the key in {ENV} is not WALLET's ({wallet})")
    old = e.get("RELAY_V3", "").lower()
    if old:
        eth = int(relay_sim.rpc("eth_getBalance", [old, "latest"]), 16)
        weth = int(relay_sim.rpc("eth_call", [{"to": v3.WETH, "data": "0x70a08231" + word(old)}, "latest"]), 16)
        print(f"{ENV} already has RELAY_V3={old}: {eth / 1e18:.6f} ETH, {weth / 1e18:.6f} WETH; a new deployment is a second, separate relay")
        if (eth or weth) and not a.force:
            sys.exit("that relay still holds ETH or WETH: empty it first (relay_ops.py withdraw_v3, relay_ops.py sweep_v3 WETH) or pass --force")
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelayV3.json"))); src = open(os.path.join(ROOT, "contracts", "FlipRelayV3.sol")).read()
    if hashlib.sha256(src.encode()).hexdigest() != art["source_sha256"]:
        sys.exit("contracts/FlipRelayV3.json was not compiled from contracts/FlipRelayV3.sol: python3 contracts/compile.py FlipRelayV3 first")
    rpc = relay_sim.rpc; data = art["bytecode"] + word(wallet)
    if int(rpc("eth_chainId", []), 16) != 4663:
        sys.exit("the RPC is not Robinhood Chain (chain id 4663)")
    bal = int(rpc("eth_getBalance", [wallet, "latest"]), 16); gp = int(rpc("eth_gasPrice", []), 16); nonce = int(rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    gas = int(rpc("eth_estimateGas", [{"from": wallet, "data": data}]), 16); gas_lim = int(gas * 1.3); cost = gas_lim * gp * 2
    print(f"wallet {wallet}: {bal / 1e18:.6f} ETH, nonce {nonce}")
    print(f"FlipRelayV3 (source sha256 {art['source_sha256'][:12]}, runtime {len(art['deployedBytecode']) // 2 - 1} bytes), owner = the wallet: "
          f"about {gas} gas at {gp / 1e9:.4f} gwei; at most {cost / 1e18:.6f} ETH (limit {gas_lim}, twice the gas price)")
    if bal < cost:
        sys.exit("not enough ETH for the deployment")
    if input("deploy FlipRelayV3 now? type yes: ").strip().lower() != "yes":
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
    code = rpc("eth_getCode", [relay, "latest"]); expected = v3.relay_v3_runtime(wallet)
    owner = rpc("eth_call", [{"to": relay, "data": "0x8da5cb5b"}, "latest"])
    ok_code = code.lower() == expected.lower(); ok_owner = ("0x" + owner[-40:]).lower() == wallet
    print(f"code on the chain {len(code) // 2 - 1} bytes {'matches the artifact byte for byte' if ok_code else 'UNEXPECTED: DO NOT USE'}; "
          f"owner() {'== wallet ok' if ok_owner else 'is 0x' + owner[-40:] + ': DO NOT USE'}")
    if not (ok_code and ok_owner):
        sys.exit(1)
    try:
        print(simulated_buy(relay, wallet))
    except Exception as ex:
        print(f"the simulated buy did not run ({str(ex)[:160]}); try deploy/relay_v3_sim.py later")
    new = [f"RELAY_V3={relay}", "RELAY_V3_CODEHASH=0x" + keccak(bytes.fromhex(code[2:])).hex()]
    if a.write_env:
        write_env(new)
        print("\n" + "\n".join(new) + f"\nwritten to {ENV}. Next: relay_ops.py deposit_v3 <eth>, then relay_ops.py status")
    else:
        print(f"\nadd to {ENV} (sudo nano, mode 600 kept), then relay_ops.py deposit_v3 <eth>:\n" + "\n".join(new))


def write_env(new):
    """the env file with the previous RELAY_V3 and RELAY_V3_CODEHASH lines kept as comments and the new ones appended, through a fresh
    temporary file (a stale one unlinked; O_EXCL and O_NOFOLLOW, mode 600), flushed and fsynced, renamed over the file, then the
    directory fsynced"""
    keys = ("RELAY_V3=", "RELAY_V3_CODEHASH=")
    lines = ["# previous " + l if l.startswith(keys) else l for l in open(ENV).read().splitlines()] + new
    tmp = ENV + ".tmp"
    try:
        os.unlink(tmp)
    except FileNotFoundError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, ENV)
    dfd = os.open(os.path.dirname(ENV) or ".", os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


if __name__ == "__main__":
    main()
