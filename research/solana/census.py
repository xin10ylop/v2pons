#!/usr/bin/env python3
"""census.py DAYS OUT.json: Solana pump-and-pull census on Raydium's two creator-funded pool programs (read-only; Helius when
HELIUS_API_KEY is set in the environment, else the public RPC).

Pool creations are listed from the programs' creation-fee accounts (only a pool creation pays them): AMM v4 7YttLkHD..., CPMM DNXgeM9E....
Per pool: the creator (fee payer), the SOL side's liquidity (the vault's post-balance of wrapped SOL), the token mint, the LP mint, the
pool and vault accounts, the time. Per creator: its signature count (fresh or not) and its funder (the sender of the SOL in its oldest
transaction). Per pool: the LP mint's later signatures (a deposit or withdraw: the pull), and the SOL vault's balance now."""
import json, sys, time, collections, urllib.request, urllib.error, concurrent.futures as cf, threading

import os
HELIUS = os.environ.get("HELIUS_API_KEY", "").strip()                            # set in the cloud environment's secrets; never printed
U = [f"https://mainnet.helius-rpc.com/?api-key={HELIUS}"] if HELIUS else ["https://solana-rpc.publicnode.com", "https://api.mainnet-beta.solana.com"]
WSOL = "So11111111111111111111111111111111111111112"
PROG = {"cpmm": ("CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1R", "DNXgeM9EiiaAbaWvwjHj9fQQLAX5ZsfHyvmYUNRAdNC8"),
        "ammv4": ("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eqaYcHQqtj2G5")}
# instruction account positions: CPMM initialize (pool_state 3, token_0_mint 4, token_1_mint 5, lp_mint 6, vault_0 10, vault_1 11);
# AMM v4 initialize2 (amm 4, lp_mint 7, coin_mint 8, pc_mint 9, coin vault 10, pc vault 11)
POS = {"cpmm": {"pool": 3, "m0": 4, "m1": 5, "lp": 6, "v0": 10, "v1": 11}, "ammv4": {"pool": 4, "lp": 7, "m0": 8, "m1": 9, "v0": 10, "v1": 11}}
_lock = threading.Lock(); _n = [0]; _next = [0.0]; GAP = 0.11 if HELIUS else 0.16  # Helius's free plan takes about 10 a second; the public endpoints refuse more than 6
FAILED = collections.Counter()


def rpc(m, p):
    err = None
    for k in range(10):
        with _lock:
            _n[0] += 1; u = U[_n[0] % 2]; wait = _next[0] - time.time(); _next[0] = max(_next[0], time.time()) + GAP
        if wait > 0:
            time.sleep(wait)
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json"}), timeout=40))
            if "result" in r:
                return r["result"]
            err = r.get("error")
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (403, 429):
                time.sleep(5 * (k + 1)); continue
        except Exception as e:
            err = e
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{m}: {str(err)[:100]}")


def safe(fn, what):
    """fn, but a lookup that keeps failing skips its item (counted in FAILED) instead of ending the run"""
    def run(*a):
        try:
            return fn(*a)
        except Exception:
            FAILED[what] += 1
            return None
    return run


def sigs_since(addr, t0):
    out, before = [], None
    while True:
        p = {"limit": 1000}
        if before:
            p["before"] = before
        page = rpc("getSignaturesForAddress", [addr, p])
        out += [s for s in page if (s.get("blockTime") or 0) >= t0]
        if len(page) < 1000 or (page[-1].get("blockTime") or 0) < t0:
            return out
        before = page[-1]["signature"]


def parse(kind, sig):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    if not tx or tx["meta"]["err"]:
        return None
    keys = [k["pubkey"] for k in tx["transaction"]["message"]["accountKeys"]]
    prog = PROG[kind][0]
    ix = next((i for i in tx["transaction"]["message"]["instructions"] if i.get("programId") == prog and "accounts" in i), None)
    if ix is None:
        for inner in tx["meta"].get("innerInstructions") or []:
            ix = next((i for i in inner["instructions"] if i.get("programId") == prog and "accounts" in i), None)
            if ix:
                break
    if ix is None:
        return None
    acc = ix["accounts"]; P = POS[kind]
    if len(acc) <= max(P.values()):
        return None
    rec = {"kind": kind, "sig": sig, "t": tx["blockTime"], "slot": tx["slot"], "creator": keys[0]}
    rec.update({k: acc[v] for k, v in P.items()})
    post = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances") or []}
    for side in ("v0", "v1"):
        idx = keys.index(rec[side]) if rec[side] in keys else None
        b = post.get(idx)
        if b:
            rec[side + "_mint"] = b["mint"]; rec[side + "_amt"] = float(b["uiTokenAmount"]["uiAmount"] or 0)
    sol_side = "v0" if rec.get("v0_mint") == WSOL else "v1" if rec.get("v1_mint") == WSOL else None
    rec["sol"] = rec.get(sol_side + "_amt") if sol_side else None
    rec["sol_vault"] = rec.get(sol_side) if sol_side else None
    rec["token"] = (rec.get("v1_mint") if sol_side == "v0" else rec.get("v0_mint")) if sol_side else None
    return rec


def creator_profile(c):
    sigs = rpc("getSignaturesForAddress", [c, {"limit": 1000}])
    prof = {"n": len(sigs), "first_t": sigs[-1].get("blockTime") if sigs else None, "funder": None, "funded_sol": None}
    if sigs:
        tx = rpc("getTransaction", [sigs[-1]["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        if tx:
            for ins in tx["transaction"]["message"]["instructions"] + [i for inner in tx["meta"].get("innerInstructions") or [] for i in inner["instructions"]]:
                pi = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
                if pi and pi.get("type") == "transfer" and pi.get("info", {}).get("destination") == c and "lamports" in pi["info"]:
                    prof["funder"] = pi["info"]["source"]; prof["funded_sol"] = pi["info"]["lamports"] / 1e9
                    break
    return c, prof


def pull_info(rec):
    sigs = rpc("getSignaturesForAddress", [rec["lp"], {"limit": 50}])
    later = sorted(s["blockTime"] for s in sigs if not s["err"] and (s.get("blockTime") or 0) > rec["t"])
    now = None
    if rec.get("sol_vault"):
        try:
            now = float(rpc("getTokenAccountBalance", [rec["sol_vault"]])["value"]["uiAmount"] or 0)
        except Exception:
            now = None
    return rec["sig"], {"lp_later": later[:10], "sol_now": now}


def main(days, out):
    t0 = int(time.time() - days * 86400); recs = []
    for kind, (prog, fee) in PROG.items():
        sigs = [s["signature"] for s in sigs_since(fee, t0) if not s["err"]]
        print(f"{kind}: {len(sigs)} creations in {days} days", flush=True)
        with cf.ThreadPoolExecutor(3) as ex:
            for n, r in enumerate(ex.map(lambda s: safe(parse, "parse")(kind, s), sigs)):
                if r:
                    recs.append(r)
                if n % 200 == 0:
                    print(f"  {kind} parsed {n}/{len(sigs)}", flush=True)
    sol = [r for r in recs if r.get("sol")]
    print(f"pools with a SOL side: {len(sol)} of {len(recs)}", flush=True)
    creators = sorted({r["creator"] for r in sol}); prof = {}
    with cf.ThreadPoolExecutor(3) as ex:
        for n, cp in enumerate(ex.map(safe(creator_profile, "creator"), creators)):
            if cp:
                prof[cp[0]] = cp[1]
            if n % 200 == 0:
                print(f"  creators {n}/{len(creators)}", flush=True)
    pulls = {}
    with cf.ThreadPoolExecutor(3) as ex:
        for n, sp in enumerate(ex.map(safe(pull_info, "pull"), sol)):
            if sp:
                pulls[sp[0]] = sp[1]
            if n % 200 == 0:
                print(f"  pulls {n}/{len(sol)}", flush=True)
    for r in sol:
        r.update(prof.get(r["creator"], {})); r.update(pulls.get(r["sig"], {}))
    json.dump({"t0": t0, "days": days, "pools": recs, "failed": dict(FAILED)}, open(out, "w"))
    print("lookups that kept failing (items skipped):", dict(FAILED) or "none", flush=True)
    print("done ->", out, flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
