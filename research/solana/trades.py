#!/usr/bin/env python3
"""trades.py census7.json OUT.json SELECT...: every trade on the selected pools from Helius's parsed transaction history (HELIUS_API_KEY).
SELECT: creator:<addr>, funder:<addr> or sol:<amount>. Per transaction touching the pool account: time, signature, fee payer, Helius's
type, and the pool's two vaults' balance changes (the SOL vault's change: + a buy, - a sell or the pull), so the reserves and the price
can be replayed from the creation's vault amounts."""
import json, os, sys, time, urllib.request, urllib.error

KEY = os.environ["HELIUS_API_KEY"].strip()


def history(addr, t_min):
    out, before = [], None
    for _ in range(60):
        url = f"https://api.helius.xyz/v0/addresses/{addr}/transactions?api-key={KEY}&limit=100" + (f"&before={before}" if before else "")
        for k in range(6):
            try:
                page = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research"}), timeout=60)); break
            except urllib.error.HTTPError as e:
                time.sleep(3 * (k + 1)) if e.code in (429, 403, 500, 502, 503) else (_ for _ in ()).throw(RuntimeError(f"HTTP {e.code}"))
            except Exception:
                time.sleep(2 * (k + 1))
        else:
            raise RuntimeError("history: no answer")
        if not page:
            break
        out += page; before = page[-1]["signature"]
        if page[-1].get("timestamp", 0) < t_min or len(page) < 100:
            break
        time.sleep(0.12)
    return out


def main(census, out, selects):
    pools = [p for p in json.load(open(census))["pools"] if p.get("sol")]
    chosen = []
    for s in selects:
        k, v = s.split(":", 1)
        chosen += [p for p in pools if (k == "creator" and p["creator"] == v) or (k == "funder" and p.get("funder") == v)
                   or (k == "sol" and abs(p["sol"] - float(v)) < 1e-9)]
    chosen = list({p["sig"]: p for p in chosen}.values())
    print(f"{len(chosen)} pools selected", flush=True)
    res = []
    for n, p in enumerate(chosen):
        txs = history(p["pool"], p["t"] - 60)
        rows = []
        for t in txs:
            if t.get("timestamp", 0) < p["t"] - 5:
                continue
            d = {}
            for a in t.get("accountData") or []:
                for c in a.get("tokenBalanceChanges") or []:
                    if c.get("tokenAccount") in (p["v0"], p["v1"]):
                        amt = int(c["rawTokenAmount"]["tokenAmount"]) / 10 ** c["rawTokenAmount"]["decimals"]
                        d[c["tokenAccount"]] = d.get(c["tokenAccount"], 0) + amt
            sol_d = d.get(p["sol_vault"], 0.0); tok_vault = p["v1"] if p["sol_vault"] == p["v0"] else p["v0"]; tok_d = d.get(tok_vault, 0.0)
            rows.append({"t": t["timestamp"], "slot": t.get("slot"), "sig": t["signature"], "payer": t.get("feePayer"), "type": t.get("type"),
                         "source": t.get("source"), "sol_d": sol_d, "tok_d": tok_d, "err": bool(t.get("transactionError"))})
        rows.sort(key=lambda r: (r["slot"] or 0, r["t"]))
        tok0 = p.get("v1_amt") if p["sol_vault"] == p["v0"] else p.get("v0_amt")
        res.append({"pool": p["pool"], "creator": p["creator"], "funder": p.get("funder"), "t": p["t"], "slot": p["slot"], "sol0": p["sol"], "tok0": tok0,
                    "token": p["token"], "rows": rows})
        print(f"  {n + 1}/{len(chosen)} {p['pool'][:10]}: {len(rows)} transactions", flush=True)
    json.dump(res, open(out, "w")); print("done ->", out, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
