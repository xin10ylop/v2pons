#!/usr/bin/env python3
"""trace_bsc.py OUT.json SEED... : the 2.433 operator's money on BNB Chain from seed addresses, through NodeReal's nr_getAssetTransfers
(native transfers, external and internal; the key from research/chase/report.sh). Breadth first: every address's transfers in and out of
at least MIN BNB since SINCE; an address with more than 5,000 transactions (an exchange or a router) or with code is noted, not expanded.
Per address: nonce, code, balance, first and last transfer, the biggest in and out; per edge: from, to, BNB, time, hash."""
import json, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = re.search(r"nodereal\.io/v1/([0-9a-f]{32})", open(os.path.join(HERE, "report.sh")).read()).group(1)
U = f"https://bsc-mainnet.nodereal.io/v1/{KEY}"
MIN = float(os.environ.get("MIN_BNB", "0.5")); SINCE = int(os.environ.get("SINCE", "1792368000"))   # 2026-10-19 00:00 UTC
DEPTH = int(os.environ.get("DEPTH", "3")); MAXADDR = int(os.environ.get("MAXADDR", "120"))


def rpc(m, p):
    for k in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json"}), timeout=40))
            if "result" in r:
                return r["result"]
            err = r.get("error")
        except Exception as e:
            err = e
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{m}: {str(err)[:120]}")


def transfers(addr, side, pages=5):
    out, key = [], None
    for _ in range(pages):
        q = {"category": ["external", "internal"], side: addr, "maxCount": "0x3e8", "order": "desc"}
        if key:
            q["pageKey"] = key
        r = rpc("nr_getAssetTransfers", [q])
        for t in r.get("transfers") or []:
            if t.get("asset") != "BNB":
                continue
            v = int(t["value"], 16) / 1e18
            out.append({"from": t["from"].lower(), "to": t["to"].lower(), "bnb": v, "t": t.get("blockTimeStamp"), "block": int(t["blockNum"], 16), "hash": t["hash"]})
        key = r.get("pageKey")
        if not key or (out and out[-1]["t"] and out[-1]["t"] < SINCE):
            break
    return out


def main(out, seeds):
    seen, queue, edges, info = set(), [(s.lower(), 0) for s in seeds], [], {}
    while queue and len(seen) < MAXADDR:
        a, depth = queue.pop(0)
        if a in seen:
            continue
        seen.add(a)
        nonce = int(rpc("eth_getTransactionCount", [a, "latest"]), 16); code = len(rpc("eth_getCode", [a, "latest"])) > 2
        bal = int(rpc("eth_getBalance", [a, "latest"]), 16) / 1e18
        rec = {"nonce": nonce, "code": code, "bnb": round(bal, 4), "depth": depth}
        if nonce > 5000 or code:
            rec["stop"] = "contract" if code else "busy (exchange or bot)"; info[a] = rec; continue
        tin, tout = transfers(a, "toAddress"), transfers(a, "fromAddress")
        rec.update(first=min((x["t"] for x in tin + tout if x["t"]), default=None), last=max((x["t"] for x in tin + tout if x["t"]), default=None),
                   n_in=len(tin), n_out=len(tout))
        info[a] = rec
        for x in tin + tout:
            if x["bnb"] >= MIN and (x["t"] or 0) >= SINCE:
                edges.append(x)
                nxt = x["to"] if x["from"] == a else x["from"]
                if depth < DEPTH and nxt not in seen:
                    queue.append((nxt, depth + 1))
        print(f"{a[:10]} d{depth} nonce {nonce} bal {bal:.3f} | in {len(tin)} out {len(tout)} | last "
              f"{time.strftime('%m-%d %H:%M', time.gmtime(rec['last'])) if rec['last'] else '-'}", flush=True)
    json.dump({"since": SINCE, "min_bnb": MIN, "addresses": info, "edges": edges}, open(out, "w"))
    print(f"done -> {out}: {len(info)} addresses, {len(edges)} edges >= {MIN} BNB since {time.strftime('%m-%d', time.gmtime(SINCE))}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
