#!/usr/bin/env python3
"""pumpwave.py fetch|links OUTDIR [N_PER_OPERATOR] [OPERATOR_IDS_FILE]: pump.fun launches' first 15 minutes (read-only; HELIUS_API_KEY).

fetch: per operator in OUTDIR/operators.json (pumpops.py), N launches spread evenly over its launches in the window (all of them when
  it has fewer), or only the operators listed in OPERATOR_IDS_FILE (one id a line). Per launch: every successful transaction on the
  bonding curve from the creation to +15 min (getTransactionsForAddress ascending, 100 a call, up to 4000), decoded to pump.fun's
  TradeEvents (trader, buy/sell, SOL in or out of the curve, tokens, fees, the virtual and real reserves after the trade), with the
  transaction's slot, index in the slot, fee payer, fee and Jito tip, and SOL the fee payer moved to other wallets in it; and the
  creation's Mayhem-mode flag.
  Cached in OUTDIR/trades/<mint>.json (resumable).
links: the wallets each operator's launches need checked: the first funder (oldest transaction's SOL sender) of every buyer in the
  creation slot and the next 3 slots, of every wallet that buys in 2+ of the operator's sampled launches, and of the 5 largest
  buyers in the first 2 minutes of each launch; and the launch's creator's and the operator's funders' SOL sent to other wallets
  from 30 min before to 15 min after each sampled launch. Cached in OUTDIR/wallets.json and OUTDIR/outflows/<operator>.json.
grad: whether each read launch's bonding curve has completed (graduated) by now: OUTDIR/grad.json."""
import json, os, sys, time, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P

WIN = 900


def sample(ls, n):
    if len(ls) <= n:
        return ls
    return [ls[round(i * (len(ls) - 1) / (n - 1))] for i in range(n)]


def launch_trades(L):
    txs, complete = P.gtfa(L["curve"], gte=L["t"], lte=L["t"] + WIN, asc=True, max_pages=40)
    rows = []; mayhem = None
    for tx in txs:
        ks = P.keys(tx)
        try:
            evs = P.pump_events(tx, ks)
        except Exception:
            continue
        tr = [e for e in evs if e["ev"] == "trade" and e["mint"] == L["mint"]]
        done = any(e["ev"] == "complete" and e["mint"] == L["mint"] for e in evs)
        for e in evs:
            if e["ev"] == "create" and e["mint"] == L["mint"]:
                mayhem = e.get("mayhem")
        if not tr and not done:
            continue
        xf = [(t, l) for f, t, l in P.system_transfers(tx, ks) if f == ks[0] and l >= 10_000_000 and t not in P.JITO_TIP]
        rows.append({"slot": tx["slot"], "idx": tx.get("transactionIndex"), "t": tx["blockTime"], "sig": tx["transaction"]["signatures"][0],
                     "payer": ks[0], "txfee": tx["meta"]["fee"], "tip": P.tip(tx, ks), "xf": xf, "complete": done,
                     "ev": [[e["user"], int(e["buy"]), e["sol"], e["tok"], e["fee"] + e["cfee"], e["fee_bps"] + e["cfee_bps"], e["vS"], e["vT"], e["rT"]]
                            for e in tr]})
    rows.sort(key=lambda r: (r["slot"], r["idx"] if r["idx"] is not None else 0))
    return {"mint": L["mint"], "curve": L["curve"], "t": L["t"], "slot": L["slot"], "n_tx": len(txs), "complete_fetch": complete, "mayhem": mayhem,
            "truncated": not complete, "rows": rows}


def fetch(outdir, n_per, only=None):
    ops = P.jload(outdir + "/operators.json")
    os.makedirs(outdir + "/trades", exist_ok=True)
    if only:
        ids = {x.strip() for x in open(only) if x.strip()}
        ops = [o for o in ops if o["id"] in ids]
    ops = [o for o in ops if o["n"] >= int(os.environ.get("MIN_N", "0"))]       # MIN_N: only operators with this many launches
    todo = []
    for o in ops:
        for L in sample(o["launches"], n_per):
            if not os.path.exists(f"{outdir}/trades/{L['mint']}.json"):
                todo.append(L)
    print(f"{len(ops)} operators, {len(todo)} launches to read", flush=True)
    t = time.time()

    def one(L):
        try:
            P.jsave(f"{outdir}/trades/{L['mint']}.json", launch_trades(L)); return True
        except Exception as e:
            print(f"  failed {L['mint'][:10]}: {str(e)[:80]}", flush=True); return False
    with cf.ThreadPoolExecutor(int(os.environ.get("THREADS", "6"))) as ex:
        for n, _ in enumerate(ex.map(one, todo)):
            if n % 200 == 0:
                print(f"  {n}/{len(todo)} {time.time() - t:.0f} s {dict(P.STATS)}", flush=True)
    print(f"fetch done {time.time() - t:.0f} s {dict(P.STATS)}", flush=True)


def first_funder(addr):
    txs, _ = P.gtfa(addr, asc=True, limit=5, max_pages=1, status=None)
    out = {"first_t": txs[0]["blockTime"] if txs else None, "funder": None, "sol": None}
    for tx in txs:
        if (tx.get("meta") or {}).get("err"):
            continue
        ks = P.keys(tx)
        for f, t, l in P.system_transfers(tx, ks):
            if t == addr and f != addr:
                out.update(funder=f, sol=l / 1e9, t=tx["blockTime"]); return out
        if ks[0] != addr:
            out.update(funder=ks[0], t=tx["blockTime"]); return out
    return out


def links(outdir, only=None):
    ops = P.jload(outdir + "/operators.json")
    if only:
        ids = {x.strip() for x in open(only) if x.strip()}
        ops = [o for o in ops if o["id"] in ids]
    os.makedirs(outdir + "/outflows", exist_ok=True)
    wallets = P.jload(outdir + "/wallets.json", {})
    hubs = P.jload(outdir + "/hubs.json", {})
    need = set(); flows_todo = []
    for o in ops:
        tl = [(L, P.jload(f"{outdir}/trades/{L['mint']}.json")) for L in o["launches"]]
        tl = [(L, T) for L, T in tl if T]
        if not tl:
            continue
        seen = collections.Counter()
        for L, T in tl:
            ws = set(); early = collections.Counter()
            for r in T["rows"]:
                for u, b, sol, *_ in r["ev"]:
                    ws.add(u)
                    if b and r["slot"] <= L["slot"] + 3:
                        need.add(u)
                    if b and r["t"] <= L["t"] + 120:
                        early[u] += sol
            seen.update(ws)
            need |= {u for u, _ in early.most_common(5)}
        need |= {u for u, k in seen.items() if k >= 2}
        if not os.path.exists(f"{outdir}/outflows/{o['id']}.json"):
            flows_todo.append((o, [L for L, _ in tl]))
    need -= set(wallets)
    print(f"links: {len(need)} wallets to look up, {len(flows_todo)} operators' outflows", flush=True)
    t = time.time()

    def lw(a):
        try:
            return a, first_funder(a)
        except Exception:
            return a, None
    with cf.ThreadPoolExecutor(int(os.environ.get("THREADS", "6"))) as ex:
        for n, (a, r) in enumerate(ex.map(lw, sorted(need))):
            if r:
                wallets[a] = r
            if n % 500 == 0:
                print(f"  wallets {n}/{len(need)} {time.time() - t:.0f} s {dict(P.STATS)}", flush=True); P.jsave(outdir + "/wallets.json", wallets)
    P.jsave(outdir + "/wallets.json", wallets)

    def flows(item):
        o, ls = item
        sent = collections.defaultdict(list)
        fs = {f for f in o["funders"] if not hubs.get(f, {}).get("hub")}
        srcs = set(o["members"]) | fs
        for L in ls:
            for a in {L["payer"]} | fs:
                try:
                    txs, _ = P.gtfa(a, gte=L["t"] - 1800, lte=L["t"] + WIN, asc=True, max_pages=3)
                except Exception:
                    continue
                for tx in txs:
                    for f, to, l in P.system_transfers(tx):
                        if f == a and l >= 5_000_000 and to not in P.JITO_TIP:
                            sent[to].append([a, tx["blockTime"], l / 1e9])
        P.jsave(f"{outdir}/outflows/{o['id']}.json", {"sent": sent, "srcs": sorted(srcs)})
    with cf.ThreadPoolExecutor(int(os.environ.get("THREADS", "6"))) as ex:
        for n, _ in enumerate(ex.map(flows, flows_todo)):
            if n % 100 == 0:
                print(f"  outflows {n}/{len(flows_todo)} {time.time() - t:.0f} s {dict(P.STATS)}", flush=True)
    print(f"links done {time.time() - t:.0f} s", flush=True)


def grad(outdir):
    """the bonding curve's 'complete' flag now (byte 48 of the curve account: discriminator, 5 u64 reserves/supply, then the flag)"""
    import base64, glob
    curves = {}
    for fpath in glob.glob(outdir + "/trades/*.json"):
        T = P.jload(fpath)
        if T:
            curves[T["curve"]] = T["mint"]
    gp = outdir + "/grad.json"; out = P.jload(gp, {})
    todo = [c for c in curves if curves[c] not in out]
    for k in range(0, len(todo), 100):
        r = P.rpc("getMultipleAccounts", [todo[k:k + 100], {"encoding": "base64", "dataSlice": {"offset": 48, "length": 1}}])
        for c, v in zip(todo[k:k + 100], r["value"]):
            out[curves[c]] = bool(v and base64.b64decode(v["data"][0])[:1] == b"\x01")
    P.jsave(gp, out)
    print(f"graduated (curve complete) {sum(out.values())} of {len(out)}", flush=True)


if __name__ == "__main__":
    cmd, outdir = sys.argv[1], sys.argv[2]
    if cmd == "fetch":
        fetch(outdir, int(sys.argv[3]) if len(sys.argv) > 3 else 6, sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "grad":
        grad(outdir)
    elif cmd == "links":
        links(outdir, sys.argv[3] if len(sys.argv) > 3 else None)
