#!/usr/bin/env python3
"""Stage 6 (sample): the launch wallet's funding, read from full blocks (eth_getBlockByNumber, full transactions) scanned backwards from the
launch block. No traces: a funding is a transaction with to == wallet and value > 0 (direct) or a transaction whose calldata contains the
wallet's address (a contract call that forwarded ETH, e.g. a multisend; its from = the funder, its to = the contract, value = the whole call's
value). For a wallet whose launch nonce is n > 0 the scan first looks for the wallet's own nonce-0 transaction and then for the funding before
it. Sample: for each of the top token-code and launcher (code hash|selector) families, 4 consecutive launches whose wallet had nonce <= 3,
plus a random sample of other pools; MAXBACK blocks at most per wallet; blocks are cached (cache/fblocks.jsonl) and shared."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *
MAXBACK = int(os.environ.get("MAXBACK", "1200")); CH = 40; NONCE_MAX = 3
TOPF = int(os.environ.get("TOPF", "70")); PER_FAM = 4; NRAND = int(os.environ.get("NRAND", "120"))
HOP2_NONCE = int(os.environ.get("HOP2_NONCE", "20"))


def families():
    P = base_pools(); T = {x["hash"]: x for x in jl_iter("tx_launch.jsonl")}
    C = {x["addr"]: x for x in jl_iter("codes.jsonl")}; R = {x["hash"]: x for x in jl_iter("rcpt.jsonl")}
    rows = []
    for p in P:
        t = T.get(p["launch_tx"])
        if not t or p["quote_pair"]: continue
        tgt = t["to"] or (R.get(p["launch_tx"]) or {}).get("contract")
        tk = (C.get(p["token"]) or {}).get("sk"); lc = (C.get(tgt) or {}).get("h") if tgt else None
        rows.append({"pool": p["pool"], "lb": p["launch_block"], "ti": p["ti"], "wallet": t["from"], "nonce": t["nonce"], "tok": tk,
                     "lk": f"{lc or tgt}|{t['selector']}"})
    return rows


def pick(rows):
    random.seed(7); out = []
    for key in ("tok", "lk"):
        by = collections.defaultdict(list)
        for r in rows:
            if r[key]: by[r[key]].append(r)
        for k in sorted(by, key=lambda k: -len(by[k]))[:TOPF]:
            c = [r for r in sorted(by[k], key=lambda r: r["lb"]) if r["nonce"] <= NONCE_MAX]
            if not c: continue
            j = len(c) // 2; out += c[j:j + PER_FAM // 2] + c[-(PER_FAM // 2):]
    rest = [r for r in rows if r["nonce"] <= NONCE_MAX]
    out += random.sample(rest, min(NRAND, len(rest)))
    seen = set(); res = []
    for r in out:
        if r["wallet"] in seen: continue
        seen.add(r["wallet"]); res.append(r)
    return res


BL = {}
def load_blocks():
    for b in jl_iter("fblocks.jsonl"): BL[b["bn"]] = b["txs"]


def get_blocks(bns):
    need = [b for b in bns if b not in BL]
    for i in range(0, len(need), CH):
        ch = need[i:i + CH]
        r = batch([("eth_getBlockByNumber", [hex(b), True]) for b in ch], size=CH)
        rows = []
        for b, x in zip(ch, r):
            if not x: continue
            txs = [[t["hash"], t["from"].lower(), (t.get("to") or "").lower() or None, int(t["value"], 16), int(t["nonce"], 16), t.get("input") or "0x",
                    int(t.get("type") or "0x0", 16), int(t["transactionIndex"], 16)] for t in x["transactions"] if int(t.get("type") or "0x0", 16) != 0x6a]
            BL[b] = txs; rows.append({"bn": b, "ts": int(x["timestamp"], 16), "txs": txs})
        jl_append("fblocks.jsonl", rows)


def scan(w, lb, ti, nonce):
    """-> the fundings of wallet w (launched at block lb, tx index ti, with nonce `nonce`) found in [lb - MAXBACK + 1, lb]"""
    hexw = w[2:]; n0 = (lb, ti) if nonce == 0 else None; found = []; b = lb; low = lb - MAXBACK + 1; stop_at = None
    while b >= low:
        lo = max(low, b - CH + 1)
        get_blocks(list(range(b, lo - 1, -1)))
        for bn in range(b, lo - 1, -1):
            for t in BL.get(bn, []):
                h, f, to, v, nn, inp, ty, idx = t
                if bn == lb and idx >= ti: continue
                if f == w:
                    if nn == 0: n0 = (bn, idx)
                    continue
                if to == w and v > 0:
                    found.append({"bn": bn, "i": idx, "tx": h, "funder": f, "via": None, "value_wei": v, "kind": "direct", "funder_nonce": nn, "type": ty})
                elif hexw in inp[10:]:
                    found.append({"bn": bn, "i": idx, "tx": h, "funder": f, "via": to, "value_wei": v, "kind": "calldata", "funder_nonce": nn,
                                  "selector": inp[2:10], "calldata_len": (len(inp) - 2) // 2, "type": ty})
        pre = [x for x in found if n0 and (x["bn"], x["i"]) < n0]
        if pre and stop_at is None: stop_at = min(x["bn"] for x in pre) - CH
        b = lo - 1
        if stop_at is not None and b < stop_at: break
    found.sort(key=lambda x: (x["bn"], x["i"]))
    pre = [x for x in found if n0 and (x["bn"], x["i"]) < n0]
    first = pre[0] if pre else None
    before_launch = [x for x in found if (x["bn"], x["i"]) < (lb, ti)]
    return {"wallet": w, "launch_block": lb, "launch_nonce": nonce, "nonce0_block": n0[0] if n0 else None, "scan_from": lb, "scan_to": b + 1,
            "status": "found" if first else ("nonce0_not_found" if n0 is None else "no_funding_in_range"),
            "first": first, "first_blocks_before_launch": (lb - first["bn"]) if first else None,
            "latest_before_launch": before_launch[-1] if before_launch else None, "n_fundings": len(found), "fundings": found[:8]}


if __name__ == "__main__":
    t0 = time.time(); load_blocks()
    rows = families(); S = pick(rows)
    done = {x["wallet"] for x in jl_iter("funding.jsonl")}
    log("rows", len(rows), "sample wallets", len(S), "done", len(done), "blocks cached", len(BL))
    for k, r in enumerate(S):
        if r["wallet"] in done: continue
        res = scan(r["wallet"], r["lb"], r["ti"], r["nonce"]); res["pool"] = r["pool"]; res["tok"] = r["tok"]; res["lk"] = r["lk"]
        jl_append("funding.jsonl", [res])
        if k % 20 == 0: log("funding", k, "/", len(S), "blocks", len(BL), f"{time.time() - t0:.0f}s", STATS)
    # hop 2: a funder that was itself fresh (nonce <= HOP2_NONCE at the funding) -> its own first funding
    done2 = {x["wallet"] for x in jl_iter("funding_hop2.jsonl")}
    hop = {}
    for x in jl_iter("funding.jsonl"):
        f = x.get("first")
        if f and f["funder_nonce"] <= HOP2_NONCE and f["funder"] not in done2: hop[f["funder"]] = f
    log("hop2 funders", len(hop))
    for k, (w, f) in enumerate(hop.items()):
        res = scan(w, f["bn"], f["i"], f["funder_nonce"]); res["child_funding_tx"] = f["tx"]
        jl_append("funding_hop2.jsonl", [res])
        if k % 20 == 0: log("hop2", k, "/", len(hop), "blocks", len(BL), f"{time.time() - t0:.0f}s", STATS)
    timing("f6_funding", time.time() - t0, {"wallets": len(S), "blocks": len(BL)})
    log("STATS", STATS)
