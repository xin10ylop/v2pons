#!/usr/bin/env python3
"""rh_v2_probe.py: the $20 live test of the volume bot's V2 1 ETH tier on Robinhood Chain (research/chase/REPORT_OCT20.md section 3).
The question it answers: does the operator pull the pair when an outside wallet buys on this tier, as it does on its 30-50 ETH tiers?

One pair per run. It watches the V2 factory for the next pair created by a fresh wallet (nonce 2) through the router's addLiquidityETH
with 0.9-1.1 ETH, waits WAIT blocks (default 300 = 30 s, after the fleet's first buys so the operator's watcher is awake), runs the exit
test on the pair (a simulated buy and sell, nothing sent), buys STAKE ETH (default 0.005, hard cap 0.01) through the router, then holds
until creation + SELL_AT blocks (default 1800 = 3 min) or until the pool's liquidity is pulled, and sells everything. Every step is one
JSON line on stdout and in LOG (ev: pair, wait, guard, buy_sent, buy, pull, sell_sent, sell, done, skip, error). The reaction is read
from the Burn on the pair: a pull inside 700 blocks of our buy is the operator reacting to us (the base rate of a pull in any given
700-block window on this tier is about 20%, so three runs are needed for an answer).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/rh_v2_probe.py                 # dry: everything but sign and send
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/rh_v2_probe.py --live           # sends; needs WALLET and PRIVATE_KEY in ENV_FILE
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/rh_v2_probe.py --live --stake 0.005 --wait 300 --sell-at 1800

Settings: ENV_FILE (/etc/flip/engine.env: WALLET=0x…, PRIVATE_KEY=0x…, read only with --live, never printed), RPC_URL. The wallet needs the
stake plus about 0.0005 ETH of gas. Stop after the first run whose pull came inside 700 blocks of the buy: that is the answer."""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from eth_utils import keccak, to_checksum_address
import base_v2_sim as S                                  # the exit test (chain-agnostic: router, WETH and RPC are set below)

CHAIN_ID = 4663
RPC = os.environ.get("RPC_URL", "https://rpc.mainnet.chain.robinhood.com")
ROUTER = "0x89e5db8b5aa49aa85ac63f691524311aeb649eba"      # the V2 router the line's creators and fleet use (addLiquidityETH / swapExactETHForTokens)
FACTORY = "0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
SEL_ADD = "0xf305d719"; SEL_BUY = "7ff36ab5"; SEL_APPROVE = "095ea7b3"; SEL_SELL = "791ac947"   # swapExactETHForTokens, approve, swapExactTokensForETHSupportingFeeOnTransferTokens
T_PC = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex(); T_BURN = "0x" + keccak(text="Burn(address,uint256,uint256,address)").hex()
T_SYNC = "0x" + keccak(text="Sync(uint112,uint112)").hex()
STAKE_CAP = 0.01; TIER = (0.9, 1.1); REACTION_WINDOW = 700
word = S.word; W = S.W
LOG = os.environ.get("PROBE_LOG", "/var/log/flip/rh_v2_probe.jsonl")


def log(ev, **kw):
    line = json.dumps({"ev": ev, "t": round(time.time(), 3), **kw}); print(line, flush=True)
    try:
        with open(LOG, "a") as f: f.write(line + "\n")
    except OSError:
        pass


def rpc(m, p):
    r = S.rpc(RPC, m, p)
    if isinstance(r, dict) and "error" in r: raise RuntimeError("%s: %s" % (m, str(r["error"])[:160]))
    return r


def head(): return int(rpc("eth_blockNumber", []), 16)


def reserves(pair):
    r = rpc("eth_call", [{"to": pair, "data": "0x0902f1ac"}, "latest"]); return W(r, 0), W(r, 1)


def quote_out(amount_in, r_in, r_out): return amount_in * 997 * r_out // (r_in * 1000 + amount_in * 997)


def next_pair(seen_from):
    """the next pair of the tier: PairCreated with WETH whose creation tx is addLiquidityETH to the router from a nonce-2 wallet with 0.9-1.1 ETH"""
    last = seen_from
    while True:
        h = head()
        if h > last:
            for pos in (1, 2):
                ls = rpc("eth_getLogs", [{"address": FACTORY, "topics": [T_PC, "0x" + word(WETH), None] if pos == 1 else [T_PC, None, "0x" + word(WETH)], "fromBlock": hex(last + 1), "toBlock": hex(h)}])
                for l in ls:
                    tx = rpc("eth_getTransactionByHash", [l["transactionHash"]]); v = int(tx["value"], 16) / 1e18
                    if (tx.get("to") or "").lower() != ROUTER or tx["input"][:10] != SEL_ADD or int(tx["nonce"], 16) != 2 or not TIER[0] <= v <= TIER[1]: continue
                    pair = "0x" + l["data"][2:66][-40:]; token = "0x" + l["topics"][2 if pos == 1 else 1][-40:]
                    return {"pair": pair, "token": token, "weth_is0": pos == 1, "bn": int(l["blockNumber"], 16), "creator": tx["from"], "eth": v, "tx": l["transactionHash"]}
            last = h
        time.sleep(0.3)


def pulled(pair, since):
    ls = rpc("eth_getLogs", [{"address": pair, "topics": [T_BURN], "fromBlock": hex(since), "toBlock": "latest"}]); return int(ls[0]["blockNumber"], 16) if ls else None


def sign_and_send(acct, tx):
    from eth_account import Account
    raw = Account.sign_transaction(tx, acct.key).raw_transaction; h = rpc("eth_sendRawTransaction", ["0x" + raw.hex()]); return h


def wait_receipt(h, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = S.rpc(RPC, "eth_getTransactionReceipt", [h])
        if isinstance(r, dict) and r.get("blockNumber"): return r
        time.sleep(0.2)
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--live", action="store_true"); ap.add_argument("--stake", type=float, default=0.005); ap.add_argument("--wait", type=int, default=300)
    ap.add_argument("--sell-at", type=int, default=1800); ap.add_argument("--env-file", default=os.environ.get("ENV_FILE", "/etc/flip/engine.env")); a = ap.parse_args()
    if a.stake > STAKE_CAP: sys.exit("the stake is capped at %s ETH for this probe" % STAKE_CAP)
    S.RPC, S.ROUTER, S.WETH, S.FACTORY = RPC, ROUTER, WETH, FACTORY
    acct = None; wallet = None
    if a.live:
        from eth_account import Account
        env = dict(l.strip().split("=", 1) for l in open(a.env_file) if "=" in l and not l.startswith("#")); acct = Account.from_key(env["PRIVATE_KEY"].strip()); wallet = acct.address
        if env.get("WALLET", "").lower() != wallet.lower(): sys.exit("WALLET in the env file is not the key's address")
        bal = int(rpc("eth_getBalance", [wallet, "latest"]), 16) / 1e18
        if bal < a.stake + 0.0005: sys.exit("the wallet holds %.5f ETH, under the stake %.4f + gas" % (bal, a.stake))
        if int(rpc("eth_chainId", []), 16) != CHAIN_ID: sys.exit("RPC_URL is not Robinhood Chain")
    log("start", live=a.live, stake=a.stake, wait=a.wait, sell_at=a.sell_at, wallet=wallet)
    p = next_pair(head()); log("pair", **p)
    target = p["bn"] + a.wait
    while head() < target:
        if pulled(p["pair"], p["bn"]): log("skip", why="pulled before our wait ended", pair=p["pair"]); return
        time.sleep(0.2)
    code, sels = S.harness_runtime(); kind, text, _ = S.verdict(RPC, p["pair"], int(a.stake * 1e18), "latest", code, sels); log("guard", kind=kind, text=text)
    if kind != "SELLABLE": log("skip", why="exit test failed: " + kind); return
    r0, r1 = reserves(p["pair"]); r_eth, r_tok = (r0, r1) if p["weth_is0"] else (r1, r0); stake_wei = int(a.stake * 1e18)
    min_out = quote_out(stake_wei, r_eth, r_tok) * 97 // 100; deadline = int(time.time()) + 30
    data = "0x" + SEL_BUY + word(min_out) + word(0x80) + word(to_checksum_address(wallet or S.CALLER)) + word(deadline) + word(2) + word(WETH) + word(p["token"])
    gas_price = int(int(rpc("eth_gasPrice", []), 16) * 1.5)
    if not a.live:
        log("buy_sent", dry=True, pair=p["pair"], stake=a.stake, min_out=min_out, at_block=head()); log("done", dry=True, note="dry run: no buy, no sell; run with --live to send"); return
    nonce = int(rpc("eth_getTransactionCount", [wallet, "pending"]), 16)
    tx = {"to": to_checksum_address(ROUTER), "value": stake_wei, "data": data, "gas": 250_000, "gasPrice": gas_price, "nonce": nonce, "chainId": CHAIN_ID}
    h = sign_and_send(acct, tx); log("buy_sent", hash=h, nonce=nonce, min_out=min_out, at_block=head())
    rec = wait_receipt(h)
    if not rec or rec.get("status") != "0x1": log("error", what="the buy did not land or reverted", hash=h, status=rec and rec.get("status")); return
    buy_bn = int(rec["blockNumber"], 16); log("buy", block=buy_bn, offset=buy_bn - p["bn"], gas_used=int(rec["gasUsed"], 16))
    bal_data = "0x70a08231" + word(wallet); tokens = W(rpc("eth_call", [{"to": p["token"], "data": bal_data}, "latest"]), 0)
    sell_block = p["bn"] + a.sell_at; pull_bn = None
    while head() < sell_block:
        pull_bn = pulled(p["pair"], buy_bn)
        if pull_bn: log("pull", block=pull_bn, after_our_buy=pull_bn - buy_bn, reacted=(pull_bn - buy_bn) <= REACTION_WINDOW); break
        time.sleep(0.3)
    # approve, then sell everything (the sell goes even after a pull: a partial pull leaves something)
    nonce += 1; tx = {"to": to_checksum_address(p["token"]), "value": 0, "data": "0x" + SEL_APPROVE + word(to_checksum_address(ROUTER)) + word(tokens), "gas": 80_000, "gasPrice": gas_price, "nonce": nonce, "chainId": CHAIN_ID}
    ha = sign_and_send(acct, tx); wait_receipt(ha)
    nonce += 1; deadline = int(time.time()) + 60
    data = "0x" + SEL_SELL + word(tokens) + word(0) + word(0xa0) + word(to_checksum_address(wallet)) + word(deadline) + word(2) + word(p["token"]) + word(WETH)
    tx = {"to": to_checksum_address(ROUTER), "value": 0, "data": data, "gas": 250_000, "gasPrice": gas_price, "nonce": nonce, "chainId": CHAIN_ID}
    hs = sign_and_send(acct, tx); log("sell_sent", hash=hs, at_block=head(), tokens=tokens)
    rs = wait_receipt(hs, 90); before = int(rpc("eth_getBalance", [wallet, hex(int(rs["blockNumber"], 16) - 1)]), 16) if rs else None
    after = int(rpc("eth_getBalance", [wallet, "latest"]), 16)
    eth_out = (after - before + int(rs["gasUsed"], 16) * gas_price) / 1e18 if rs and before is not None and rs.get("status") == "0x1" else 0.0
    log("sell", status=rs and rs.get("status"), block=rs and int(rs["blockNumber"], 16), eth_out=round(eth_out, 6))
    log("done", pair=p["pair"], stake=a.stake, eth_out=round(eth_out, 6), ret=round(eth_out / a.stake - 1, 4) if eth_out else -1.0, pull_after_buy=(pull_bn - buy_bn) if pull_bn else None,
        verdict=("REACTED: the pull came %d blocks after our buy" % (pull_bn - buy_bn)) if pull_bn and pull_bn - buy_bn <= REACTION_WINDOW else ("no reaction inside %d blocks" % REACTION_WINDOW))


if __name__ == "__main__":
    main()
