#!/usr/bin/env python3
"""ammprobe.py OUT.json [WINDOWS]: is there an account that only pool creations touch on PumpSwap (pAMMBay6...) or Meteora DAMM v2
(cpamdpZC...), the way Raydium's creation-fee accounts work? (read-only; HELIUS_API_KEY)

Samples each program's history (Helius getTransactionsForAddress, full transactions, WINDOWS one-page windows of 100 spread over the
last 2 days), decodes each program instruction's anchor discriminator, and splits the transactions into pool creations
(PumpSwap create_pool; DAMM v2 initialize_pool / initialize_customizable_pool / initialize_pool_with_dynamic_config) and swaps.
PumpSwap creations are rare in the stream, so pump.fun's migrations (from its withdraw authority 39azUYFW...) are added as examples.
Per creation: the caller (top-level program: a direct creation, pump.fun's migration, Meteora DBC's migration, another launchpad),
the creation instruction's accounts. Then every account that appears in creations is counted in the sampled swaps: an account in
every direct creation and in no swap would be a creation marker. Prints the table and writes OUT.json."""
import json, os, sys, time, hashlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P

G = lambda n: hashlib.sha256(f"global:{n}".encode()).digest()[:8]
NAMES = {P.PUMPSWAP: ["create_pool", "buy", "sell", "buy_exact_quote_in", "deposit", "withdraw", "collect_coin_creator_fee", "buy_v2", "sell_v2",
                      "buy_exact_quote_in_v2"],
         P.DAMM2: ["initialize_pool", "initialize_customizable_pool", "initialize_pool_with_dynamic_config", "swap", "swap2", "add_liquidity",
                   "remove_liquidity", "remove_all_liquidity", "create_position", "claim_position_fee", "lock_position", "permanent_lock_position",
                   "close_position"]}
CREATE = {"create_pool", "initialize_pool", "initialize_customizable_pool", "initialize_pool_with_dynamic_config"}
SWAP = {"buy", "sell", "buy_exact_quote_in", "buy_v2", "sell_v2", "buy_exact_quote_in_v2", "swap", "swap2"}
CALLERS = {"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump.fun migration", "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN": "Meteora DBC migration"}


def classify(tx, prog):
    D = {G(n): n for n in NAMES[prog]}
    ks = P.keys(tx); m = tx["transaction"]["message"]; tops = [ks[i["programIdIndex"]] for i in m["instructions"]]
    found = []
    for top, depth, pr, accs, data in P.ixs(tx, ks):
        if pr != prog:
            continue
        raw = P.b58d(data)
        if raw[:8] == P.EV_TAG:
            continue
        found.append((D.get(raw[:8], raw[:8].hex()), depth, accs, tops[top]))
    return ks, found


def main(out, windows):
    now = int(time.time()); res = {}
    for prog in (P.PUMPSWAP, P.DAMM2):
        cre, swaps, names = [], [], collections.Counter()
        for k in range(windows):
            txs, _ = P.gtfa(prog, lte=now - 300 - k * (172800 // windows), asc=False, max_pages=1)
            for tx in txs:
                ks, found = classify(tx, prog)
                for n in {f[0] for f in found}:
                    names[n] += 1
                c = [f for f in found if f[0] in CREATE]
                if c:
                    cre.append({"sig": tx["transaction"]["signatures"][0], "t": tx["blockTime"], "payer": ks[0], "ix": c[0][0], "depth": c[0][1],
                                "caller": CALLERS.get(c[0][3], "direct" if c[0][3] == prog else c[0][3]), "accs": c[0][2]})
                elif any(f[0] in SWAP for f in found):
                    swaps.append(set(ks))
        if prog == P.PUMPSWAP:                                        # migration examples: pump.fun's withdraw authority
            txs, _ = P.gtfa("39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg", asc=False, max_pages=1, limit=40)
            for tx in txs:
                ks, found = classify(tx, prog)
                c = [f for f in found if f[0] in CREATE]
                if c:
                    cre.append({"sig": tx["transaction"]["signatures"][0], "t": tx["blockTime"], "payer": ks[0], "ix": c[0][0], "depth": c[0][1],
                                "caller": CALLERS.get(c[0][3], "direct" if c[0][3] == prog else c[0][3]), "accs": c[0][2]})
        acc_in_cre = collections.Counter(a for c in cre for a in set(c["accs"]))
        rows = []
        for a, n in acc_in_cre.most_common():
            if n < 2:
                continue                                                  # a pool's own accounts appear once
            rows.append({"account": a, "creations": n, "of": len(cre), "swaps": sum(1 for s in swaps if a in s), "of_swaps": len(swaps)})
        res[prog] = {"instruction_mix": dict(names), "creations": cre, "n_swaps": len(swaps), "static_accounts": rows,
                     "callers": dict(collections.Counter(c["caller"] for c in cre))}
        print(f"\n{prog}: {sum(names.values())} program instructions sampled; mix {names.most_common(12)}")
        print(f"  creations {len(cre)} by caller {res[prog]['callers']}; swaps sampled {len(swaps)}")
        for r in rows:
            print(f"  {r['account']:45s} in {r['creations']}/{r['of']} creations, {r['swaps']}/{r['of_swaps']} swaps")
    P.jsave(out, res)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60)
