#!/usr/bin/env python3
"""What happened on the chain in the front pools the engine armed in the last N hours: by default those it did NOT trade because their
fingerprint was new (the bot changed a launch parameter), with "all" every armed front pool (the last 20).
    sudo python3 deploy/pool_story.py 2            # new-fingerprint front launches of the last 2 hours
    sudo python3 deploy/pool_story.py 2 all        # every front launch armed in the last 2 hours (at most 20)
Per pool: the launch block and fingerprint, then every swap in the next 150 blocks (offset after the launch, buy/sell, ETH, the contract
the transaction called for the first 12 swaps, the Swap's router after that; "bot" = the volume bot's router 0x1cbaf24d) and every
liquidity change (add / PULL), and a one-line summary. Read-only. The RPC URL comes from
$RPC_URL or the engine's env file and is never printed."""
import glob, gzip, json, os, sys, time, urllib.request

ENV = os.environ.get("FLIP_ENV", "/etc/flip/engine.env"); LOG = os.environ.get("FLIP_LOG", "/var/log/flip/engine.jsonl")
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; BOT = "1cbaf24d53fe930fce8eff149fa797d2611da149"
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
SPAN = 150


def env():
    d = {}
    try:
        for line in open(ENV):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); d[k.strip()] = v.split(" #", 1)[0].strip().strip("'\"")
    except Exception:
        pass
    return d


RPC = os.environ.get("RPC_URL") or env().get("RPC_URL") or "https://rpc.mainnet.chain.robinhood.com"


def rpc(method, params, tries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=20))
            if "error" in r:
                raise RuntimeError(str(r["error"])[:160])
            return r["result"]
        except Exception as e:
            err = e
            if i < tries - 1:
                time.sleep(1.5 * (i + 1))
    code = getattr(err, "code", "")
    raise RuntimeError(f"rpc {method} failed: {type(err).__name__} {code}".strip())              # never the URL (it carries the provider's key) nor the provider's text


def events(hours):
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("t", 0) >= t_lo:
                    yield e
        except FileNotFoundError:
            pass


W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x


def story(pid, launch, head):
    to = min(launch + SPAN, head - 5)
    sw = rpc("eth_getLogs", [{"fromBlock": hex(launch), "toBlock": hex(to), "address": PM, "topics": [T_SWAP, pid]}])
    ml = rpc("eth_getLogs", [{"fromBlock": hex(launch), "toBlock": hex(to), "address": PM, "topics": [T_ML, pid]}])
    rows = []
    for n, l in enumerate(sw):
        a0 = sgn(W(l["data"], 0)); bn = int(l["blockNumber"], 16); who = l["topics"][2][-40:]      # the Swap's sender is the router the swapper used
        if n < 12:                                                                                  # the first swaps: the contract the transaction called (the bot's own router shows here)
            try:
                tx = rpc("eth_getTransactionByHash", [l["transactionHash"]], tries=2); who = (tx.get("to") or "")[2:].lower() or who
            except Exception:
                pass
        rows.append((bn, int(l["transactionIndex"], 16), int(l["logIndex"], 16), "buy " if a0 < 0 else "sell", abs(a0) / 1e18, who))
    for l in ml:
        dl = sgn(W(l["data"], 2)); bn = int(l["blockNumber"], 16)
        if dl != 0:
            rows.append((bn, int(l["transactionIndex"], 16), int(l["logIndex"], 16), "PULL" if dl < 0 else "add ", dl / 1e18, l["topics"][2][-40:]))
    rows.sort(); rows = [(bn, ti, kind, amt, who) for bn, ti, li, kind, amt, who in rows]
    return rows, to - launch


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2; every = len(sys.argv) > 2 and sys.argv[2] == "all"
    armed = [e for e in events(hours) if e.get("ev") == "armed" and e.get("entry") == "front" and (every or str(e.get("fingerprint", "")).startswith("new"))][-20:]
    if not armed:
        print("no", "armed front pool" if every else "new-fingerprint front launch", f"in the last {hours:g} h"); return
    try:
        head = int(rpc("eth_blockNumber", []), 16)
    except Exception as ex:
        print("the RPC does not answer:", str(ex)[:80]); return
    print(f"{len(armed)} pools (the last 20 at most), head {head}; offsets are blocks after the launch block; L = liquidity units")
    summary = []
    for e in armed:
        pid, launch = e["pid"], e["seq"]
        print(f"\n{time.strftime('%H:%M:%S', time.gmtime(e['t']))} UTC  launch {launch}  fam {e.get('fam')}  fee {e.get('fee')} ts {e.get('tick_spacing')}  "
              f"fingerprint: {e.get('fingerprint')}  eligible {e.get('eligible')}  {e.get('why', '')}")
        try:
            rows, span = story(pid, launch, head)
        except Exception as ex:
            print("   chain query failed:", str(ex)[:120]); continue
        bot_buy = pull = None; before = 0.0; n_before = 0
        for bn, ti, kind, amt, who in rows:
            tag = "bot" if who == BOT else who[:8]
            print(f"   +{bn - launch:<4} {kind} {amt:10.5f} {'ETH' if kind in ('buy ', 'sell') else 'L  '}  {tag}")
            if kind == "buy " and who == BOT and bot_buy is None: bot_buy = bn - launch
            if kind == "buy " and who != BOT and bot_buy is None: before += amt; n_before += 1
            if kind == "PULL" and pull is None: pull = bn - launch
        s = f"bot buy +{bot_buy}" if bot_buy is not None else f"no bot buy in {span}"
        s += f", pull +{pull}" if pull is not None else f", no pull in {span}"
        s += f", {n_before} other buy(s) {before:.4f} ETH before it (the bot's own dust at +3..+6 counts)" if n_before else ", no other buy before it"
        print("   =>", s); summary.append((launch, s))
    print("\nSUMMARY")
    for launch, s in summary:
        print(f"  {launch}  {s}")


if __name__ == "__main__":
    main()
