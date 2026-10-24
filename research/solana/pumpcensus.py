#!/usr/bin/env python3
"""pumpcensus.py DAYS OUTDIR: every pump.fun token creation over the last DAYS days (read-only; HELIUS_API_KEY).

Creations are listed from pump.fun's mint authority TSLvdd1p... (only a create touches it) with Helius's getTransactionsForAddress,
full transactions, ascending, in 1-hour chunks read by parallel threads (resumable: OUTDIR/creations/<chunk start>.json).
Per creation (decoded from pump.fun's CreateEvent and TradeEvents in the transaction itself): signature, slot, index in the slot,
time, fee payer (the creator), the event's user and creator, mint, bonding curve, name/symbol, the curve's virtual quote reserve at
creation (30 SOL = a SOL-quoted curve; anything else is quoted in another token), the mayhem-mode flag, the buys inside the creation
transaction (the dev buy: SOL into the curve, tokens, fees), the transaction fee and Jito tip, and SOL the fee payer sent to other
wallets in the same transaction (bundle wallets funded in the creation)."""
import json, os, sys, time, threading, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P

CHUNK = 3600
SOL_V0 = 30_000_000_000


def record(tx):
    ks = P.keys(tx); evs = P.pump_events(tx, ks)
    cr = [e for e in evs if e["ev"] == "create"]
    if not cr:
        return []
    payer = ks[0]; nsig = tx["transaction"]["message"]["header"]["numRequiredSignatures"]
    out = []
    xfers = [(t, l) for f, t, l in P.system_transfers(tx, ks) if f == payer and l >= 1_000_000 and t not in P.JITO_TIP]
    tipv = P.tip(tx, ks)
    for c in cr:
        trades = [e for e in evs if e["ev"] == "trade" and e["mint"] == c["mint"]]
        out.append({"sig": tx["transaction"]["signatures"][0], "slot": tx["slot"], "idx": tx.get("transactionIndex"), "t": tx["blockTime"],
                    "payer": payer, "nsig": nsig, "signers": ks[:nsig], "user": c["user"], "creator": c.get("creator"), "mint": c["mint"],
                    "curve": c["curve"], "name": c["name"], "symbol": c["symbol"], "vS0": c.get("vS"), "vT0": c.get("vT"),
                    "sol_curve": c.get("vS") == SOL_V0,
                    "buys": [{"user": e["user"], "sol": e["sol"], "tok": e["tok"], "fee": e["fee"] + e["cfee"], "fee_bps": e["fee_bps"],
                              "cfee_bps": e["cfee_bps"], "buy": e["buy"], "vS": e["vS"], "vT": e["vT"], "ix": e.get("ix")} for e in trades],
                    "txfee": tx["meta"]["fee"], "tip": tipv, "xfers": xfers})
    return out


def chunk(outdir, a, b):
    path = f"{outdir}/creations/{a}.json"
    if os.path.exists(path):
        return a, len(P.jload(path, {}).get("recs", [])), True
    txs, complete = P.gtfa(P.PUMP_MINT_AUTH, gte=a, lt=b, asc=True, max_pages=200)
    recs, nobad = [], 0
    for tx in txs:
        try:
            recs += record(tx)
        except Exception:
            nobad += 1
    P.jsave(path, {"a": a, "b": b, "n_tx": len(txs), "complete": complete, "undecoded": nobad, "recs": recs})
    return a, len(recs), False


def main(days, outdir):
    os.makedirs(outdir + "/creations", exist_ok=True)
    meta = P.jload(outdir + "/window.json")
    if not meta:
        t1 = int(time.time()) // CHUNK * CHUNK; meta = {"t0": t1 - int(days * 86400), "t1": t1}; P.jsave(outdir + "/window.json", meta)
    starts = list(range(meta["t0"], meta["t1"], CHUNK))
    print(f"window {time.strftime('%Y-%m-%d %H:%M', time.gmtime(meta['t0']))} .. {time.strftime('%Y-%m-%d %H:%M', time.gmtime(meta['t1']))} UTC, "
          f"{len(starts)} chunks", flush=True)
    t = time.time(); tot = 0
    with cf.ThreadPoolExecutor(int(os.environ.get("THREADS", "6"))) as ex:
        for n, (a, k, cached) in enumerate(ex.map(lambda a: chunk(outdir, a, a + CHUNK), starts)):
            tot += k
            if n % 6 == 0 or n == len(starts) - 1:
                print(f"  chunk {n + 1}/{len(starts)} {time.strftime('%m-%d %H:%M', time.gmtime(a))}: {k} creations{' (cached)' if cached else ''}; "
                      f"total {tot}; {time.time() - t:.0f} s {dict(P.STATS)}", flush=True)
    print(f"done: {tot} creations, {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
