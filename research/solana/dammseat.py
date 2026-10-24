#!/usr/bin/env python3
"""dammseat.py plan|fetch|wallets|scan OUTDIR: the seat test on Meteora DAMM v2's 85-SOL pull lines (read-only; a standard Solana
JSON-RPC in TRITON_URL, never printed or written; Helius not used).

Budget guard: every HTTP request (retries included) is counted in OUTDIR/calls.json and the run stops at CALL_CAP (default 40000);
one limiter for all threads keeps the rate under 16 calls/s.

plan:    from dammcensus/dammstate/dammchain outputs (out/amm/damm7.json, damm7_chains.json): the lines (relay chains of creators, or
         single creators) with the most pulled 80+ SOL / 1B-token pools; PER_LINE pools of each (spread over its days), plus CONTRAST
         pools from creators with one or two such pools. Per pool: its signatures from creation onward (getSignaturesForAddress,
         newest first, paged back to the creation signature). Writes OUTDIR/plan.json with the transaction counts.
trim:    the budget rule: line pools with more than MAX_TX (4000) transactions to the pull are dropped, contrast pools above
         MAX_TX_CONTRAST (1000) are replaced by other small creators' pools.
fetch:   every successful transaction of each planned pool, from creation to the pull (+60 s; the pull time is the position's newest
         signature): getTransaction (json); per transaction the fee payer, signers, the SOL and token vault balance changes
         (pre/postTokenBalances), the DAMM v2 instructions in its logs, slot, index, time. OUTDIR/tx/<pool>.json.
meta:    each pool's Pool account (fee schedule, dynamic fee flag, price range, activation).
wallets: for the wallets that buy in the sample, by SOL bought (WALLET_CAP of them): one signature page (a wallet with 1000+
         signatures is a busy bot, not walked back) and, for the others, the oldest transaction: the sender of the first SOL into it.
         OUTDIR/wallets.json.
control: whether the top buyers' newest transaction is paid or co-signed by the operator's controllers or creators.
sweep:   a controller's newest transactions: the wallets it co-signs for or funds (CONTROLLER, MAX_TX).
whois:   the biggest net buyers' newest transactions and balance, and samples of two creators' transactions.
scan:    see dammscan.py (offline)."""
import json, os, sys, time, threading, collections, concurrent.futures as cf, urllib.request, urllib.error

URL = os.environ.get("TRITON_URL", "").strip()
CAP = int(os.environ.get("CALL_CAP", "40000"))
GAP = 1 / 16.0
WSOL = "So11111111111111111111111111111111111111112"
DAMM2 = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
_lock = threading.Lock(); _next = [0.0]; CALLS = {"n": 0}; _cpath = [None]


def load_calls(outdir):
    _cpath[0] = outdir + "/calls.json"
    if os.path.exists(_cpath[0]):
        CALLS["n"] = json.load(open(_cpath[0]))["calls"]


def save_calls():
    if _cpath[0]:
        json.dump({"calls": CALLS["n"], "updated": int(time.time())}, open(_cpath[0], "w"))


def rpc(m, p):
    for k in range(8):
        with _lock:
            if CALLS["n"] >= CAP:
                raise SystemExit(f"call cap {CAP} reached")
            w = _next[0] - time.time(); _next[0] = max(_next[0], time.time()) + GAP; CALLS["n"] += 1
            if CALLS["n"] % 200 == 0:
                save_calls()
        if w > 0:
            time.sleep(w)
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json"}), timeout=60))
            if "result" in r:
                return r["result"]
            err = (r.get("error") or {}); time.sleep(1 + k)
            if err.get("code") in (-32602, -32015):
                raise RuntimeError(f"{m}: rpc error {err.get('code')}")
        except urllib.error.HTTPError as e:              # never print the exception text (no URL in output)
            time.sleep(2 * (k + 1) if e.code in (429, 502, 503, 504) else 1)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(1 + k)
    raise RuntimeError(f"{m}: no answer")


B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58d(s):
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def jload(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def jsave(p, o):
    t = p + ".tmp"; json.dump(o, open(t, "w")); os.replace(t, p)


# ------------------------------------------------------------------ lines

def lines(census="out/amm/damm7.json", chains="out/amm/damm7_chains.json"):
    pools = [p for p in json.load(open(census))["pools"] if p["sol"] >= 80 and p["pulled"]]
    tokamt = lambda p: p.get("v1_amt") if p.get("v0_mint") == WSOL else p.get("v0_amt")
    pools = [p for p in pools if abs((tokamt(p) or 0) - 1e9) < 1]
    byc = collections.defaultdict(list)
    for p in pools:
        byc[p["creator"]].append(p)
    links = (jload(chains, {}) or {}).get("links", {})
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for c, l in links.items():
        if l.get("next"):
            parent[find(l["next"])] = find(c)
    grp = collections.defaultdict(list)
    for c in byc:
        grp[find(c)].append(c)
    out = []
    for root, cs in grp.items():
        ps = sorted((p for c in cs for p in byc[c]), key=lambda p: p["t"])
        cs = sorted(cs, key=lambda c: min(p["t"] for p in byc[c]))
        out.append({"id": ("chain:" if len(cs) > 1 else "creator:") + cs[0], "creators": cs, "pools": ps,
                    "relays": [links[c].get("via") for c in cs if links.get(c, {}).get("via")]})
    out.sort(key=lambda L: -len(L["pools"]))
    return out


def spread(ps, k):
    if len(ps) <= k:
        return ps
    return [ps[round(i * (len(ps) - 1) / (k - 1))] for i in range(k)]


def plan(outdir):
    per = int(os.environ.get("PER_LINE", "4")); nl = int(os.environ.get("N_LINES", "8")); ncon = int(os.environ.get("CONTRAST", "5"))
    L = lines()
    big = L[:nl]
    small = [l for l in L if len(l["pools"]) <= 2 and len(l["creators"]) == 1]
    pick = []
    for l in big:
        for p in spread(l["pools"], per):
            pick.append({"line": l["id"], "pool": p})
    for l in spread(small, ncon):
        pick.append({"line": "contrast:" + l["id"], "pool": l["pools"][0]})
    os.makedirs(outdir + "/sigs", exist_ok=True)

    def sigs(item):
        p = item["pool"]; path = f"{outdir}/sigs/{p['pool']}.json"
        got = jload(path)
        if got:
            return got
        out, before = [], None
        for _ in range(20):
            prm = {"limit": 1000}
            if before:
                prm["before"] = before
            page = rpc("getSignaturesForAddress", [p["pool"], prm])
            out += page
            if len(page) < 1000 or any(s["signature"] == p["sig"] for s in page):
                break
            before = page[-1]["signature"]
        out.reverse()
        k = next((i for i, s in enumerate(out) if s["signature"] == p["sig"]), None)
        rows = out[k:] if k is not None else out
        got = {"pool": p["pool"], "complete": k is not None, "sigs": [[s["signature"], s["slot"], s.get("blockTime"), bool(s["err"])] for s in rows]}
        jsave(path, got)
        return got
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(sigs, pick))
    save_calls()
    for it, r in zip(pick, res):
        it["n_sigs"] = len(r["sigs"]); it["n_ok"] = sum(1 for s in r["sigs"] if not s[3]); it["complete"] = r["complete"]
    jsave(outdir + "/plan.json", {"lines": [{k: v for k, v in l.items() if k != "pools"} | {"n_pools": len(l["pools"]),
                                                                                                "days": sorted({time.strftime('%m-%d', time.gmtime(p['t'])) for p in l["pools"]})}
                                            for l in big], "pick": pick})
    tot = sum(it["n_ok"] for it in pick)
    print(f"{len(pick)} pools planned ({len(big)} lines x {per}, {sum(1 for i in pick if i['line'].startswith('contrast'))} contrast); "
          f"successful transactions to read {tot}; calls so far {CALLS['n']}", flush=True)
    for l in big:
        its = [i for i in pick if i["line"] == l["id"]]
        print(f"  {l['id'][:60]:60s} creators {len(l['creators'])} pools {len(l['pools'])}: tx {[i['n_ok'] for i in its]} complete {[i['complete'] for i in its]}")
    print("  contrast:", [(i["pool"]["creator"][:8], i["n_ok"]) for i in pick if i["line"].startswith("contrast")])


def trim(outdir):
    """budget rule: drop line pools with more than MAX_TX transactions to the pull (+60 s), and contrast pools with more than
    MAX_TX_CONTRAST; replace contrast pools from other small creators (their position's newest signature gives the pull time)"""
    mx = int(os.environ.get("MAX_TX", "4000")); mxc = int(os.environ.get("MAX_TX_CONTRAST", "1000")); ncon = int(os.environ.get("CONTRAST", "5"))
    pl = jload(outdir + "/plan.json")
    keep = [it for it in pl["pick"] if (it["n_window"] <= (mxc if it["line"].startswith("contrast") else mx))]
    dropped = [(it["line"][:30], it["pool"]["pool"][:8], it["n_window"]) for it in pl["pick"] if it not in keep]
    have = {it["pool"]["pool"] for it in pl["pick"]}
    small = [l for l in lines() if len(l["pools"]) <= 2 and len(l["creators"]) == 1]
    cands = [l for l in spread(small, 40) if l["pools"][0]["pool"] not in have]
    for l in cands:
        if sum(1 for it in keep if it["line"].startswith("contrast")) >= ncon:
            break
        p = l["pools"][0]
        s = rpc("getSignaturesForAddress", [p["position"], {"limit": 20}])
        ts = sorted(x["blockTime"] for x in s if not x["err"] and x["blockTime"] >= p["t"])
        pull_t = ts[-1] if ts else None
        out, before = [], None
        for _ in range(3):
            prm = {"limit": 1000}
            if before:
                prm["before"] = before
            page = rpc("getSignaturesForAddress", [p["pool"], prm])
            out += page
            if len(page) < 1000 or any(x["signature"] == p["sig"] for x in page):
                break
            before = page[-1]["signature"]
        out.reverse()
        k = next((i for i, x in enumerate(out) if x["signature"] == p["sig"]), None)
        if k is None:
            continue
        rows = out[k:]
        nw = sum(1 for x in rows if not x["err"] and x.get("blockTime") and x["blockTime"] <= (pull_t or p["t"] + 3600) + 60)
        if nw > mxc:
            continue
        jsave(f"{outdir}/sigs/{p['pool']}.json", {"pool": p["pool"], "complete": True,
                                                   "sigs": [[x["signature"], x["slot"], x.get("blockTime"), bool(x["err"])] for x in rows]})
        keep.append({"line": "contrast:" + l["id"], "pool": p, "n_sigs": len(rows), "n_ok": nw, "complete": True, "pull_t": pull_t, "n_window": nw})
    pl["pick"] = keep; pl["trim"] = {"max_tx": mx, "max_tx_contrast": mxc, "dropped": dropped}
    jsave(outdir + "/plan.json", pl); save_calls()
    print(f"dropped {dropped}; kept {len(keep)} pools, {sum(it['n_window'] for it in keep)} transactions to read; calls so far {CALLS['n']}", flush=True)
    print("  contrast:", [(it["pool"]["creator"][:8], round(it["pool"]["sol"], 1), it["n_window"]) for it in keep if it["line"].startswith("contrast")])


# ------------------------------------------------------------------ fetch

def parse(tx, p):
    m = tx["transaction"]["message"]
    ks = list(m["accountKeys"]) + list((tx["meta"].get("loadedAddresses") or {}).get("writable", [])) + \
        list((tx["meta"].get("loadedAddresses") or {}).get("readonly", []))
    pre = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"]) for b in tx["meta"].get("preTokenBalances") or []}
    post = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"]) for b in tx["meta"].get("postTokenBalances") or []}
    tv = p["v1"] if p["sol_vault"] == p["v0"] else p["v0"]

    def d(acc):
        j = ks.index(acc) if acc in ks else None
        return (post.get(j, 0) - pre.get(j, 0)) if j is not None else 0
    nsig = m["header"]["numRequiredSignatures"]
    ixl = [l.split("Instruction: ")[1] for l in tx["meta"].get("logMessages") or [] if "Program log: Instruction: " in l]
    # SOL moved by the fee payer to other wallets inside the transaction (system transfers, lamports): funding links
    xf = []
    for g in [m["instructions"]] + [g["instructions"] for g in tx["meta"].get("innerInstructions") or []]:
        for ix in g:
            prog = ks[ix["programIdIndex"]]
            if prog == "11111111111111111111111111111111" and len(ix.get("accounts", [])) >= 2:
                raw = b58d(ix["data"])
                if len(raw) >= 12 and int.from_bytes(raw[:4], "little") == 2:
                    lam = int.from_bytes(raw[4:12], "little")
                    if lam >= 1_000_000:
                        xf.append((ks[ix["accounts"][0]], ks[ix["accounts"][1]], lam))
    return {"sig": tx["transaction"]["signatures"][0], "slot": tx["slot"], "t": tx["blockTime"], "payer": ks[0], "signers": ks[:nsig],
            "sol_d": d(p["sol_vault"]), "tok_d": d(tv), "fee": tx["meta"]["fee"], "ix": [x for x in ixl if x in DAMM_IX], "sys": xf[:8],
            "pb0": tx["meta"]["preBalances"][0], "pa0": tx["meta"]["postBalances"][0]}


DAMM_IX = {"Swap", "Swap2", "AddLiquidity", "RemoveLiquidity", "RemoveAllLiquidity", "ClosePosition", "ClaimPositionFee", "CreatePosition",
           "InitializeCustomizablePool", "InitializePool", "LockPosition", "PermanentLockPosition"}


def fetch(outdir):
    pl = jload(outdir + "/plan.json"); os.makedirs(outdir + "/tx", exist_ok=True)

    def one(it):
        p = it["pool"]; path = f"{outdir}/tx/{p['pool']}.json"
        if os.path.exists(path):
            return 0
        sg = jload(f"{outdir}/sigs/{p['pool']}.json")["sigs"]
        lim = (it.get("pull_t") or p["t"] + 3600) + 60
        rows, missing = [], []
        for s, slot, bt, err in sg:
            if err or (bt is not None and bt > lim):
                continue
            try:
                tx = rpc("getTransaction", [s, {"encoding": "json", "maxSupportedTransactionVersion": 1}])
            except RuntimeError:
                missing.append(s); continue
            if tx:
                r = parse(tx, p); r["i"] = len(rows); rows.append(r)
            else:
                missing.append(s)
        jsave(path, {"pool": p["pool"], "line": it["line"], "rows": rows, "n_sigs": len(sg), "missing": missing})
        return len(rows)
    t = time.time()
    with cf.ThreadPoolExecutor(12) as ex:
        for n, k in enumerate(ex.map(one, pl["pick"])):
            print(f"  pool {n + 1}/{len(pl['pick'])}: {k} tx; calls {CALLS['n']}; {time.time() - t:.0f} s", flush=True)
    save_calls()
    print(f"fetch done; calls {CALLS['n']}", flush=True)


def meta(outdir):
    """the Pool account of each planned pool (one call each): base fee (cliff numerator / 1e9, scheduler mode, periods, frequency,
    reduction), dynamic fee flag, price range (sqrt min / max, Q64.64), activation point and type, collect-fee mode"""
    import base64
    pl = jload(outdir + "/plan.json"); M = jload(outdir + "/meta.json", {})
    for it in pl["pick"]:
        p = it["pool"]
        if p["pool"] in M:
            continue
        a = rpc("getAccountInfo", [p["pool"], {"encoding": "base64"}])
        if not a or not a.get("value"):
            continue
        b = base64.b64decode(a["value"]["data"][0]); u = lambda o, n: int.from_bytes(b[o:o + n], "little")
        M[p["pool"]] = {"cliff": u(8, 8) / 1e9, "sched_mode": b[16], "n_period": u(22, 2), "period_freq": u(24, 8), "reduction": u(32, 8),
                        "dyn_init": b[56], "token_a": b58e(b[168:200]), "token_b": b58e(b[200:232]), "liquidity": u(360, 16),
                        "sqrt_min": u(424, 16), "sqrt_max": u(440, 16), "sqrt_price": u(456, 16), "activation": u(472, 8), "act_type": b[480],
                        "collect_fee_mode": b[484]}
    jsave(outdir + "/meta.json", M); save_calls()
    print(f"meta for {len(M)} pools; calls {CALLS['n']}", flush=True)


def b58e(bb):
    n = int.from_bytes(bb, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = B58[r] + s
    return "1" * (len(bb) - len(bb.lstrip(b"\x00"))) + s


# ------------------------------------------------------------------ wallets

def first_funder(a, pages=1):
    out = {"n": 0, "funder": None, "first_t": None, "complete": False}
    before, last = None, None
    for _ in range(pages):
        prm = {"limit": 1000}
        if before:
            prm["before"] = before
        s = rpc("getSignaturesForAddress", [a, prm])
        out["n"] += len(s)
        if s:
            last = s[-1]; before = last["signature"]
        if len(s) < 1000:
            out["complete"] = True; break
    if not last or not out["complete"]:
        return out
    out["first_t"] = last.get("blockTime")
    tx = rpc("getTransaction", [last["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if tx:
        for ins in tx["transaction"]["message"]["instructions"] + [i for g in tx["meta"].get("innerInstructions") or [] for i in g["instructions"]]:
            pi = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
            if pi and pi.get("type") in ("transfer", "createAccount") and pi.get("info", {}).get("destination", pi.get("info", {}).get("newAccount")) == a:
                out["funder"] = pi["info"].get("source"); out["sol"] = pi["info"].get("lamports", 0) / 1e9; break
        if not out["funder"]:
            ks = tx["transaction"]["message"]["accountKeys"]
            k0 = ks[0]["pubkey"] if isinstance(ks[0], dict) else ks[0]
            if k0 != a:
                out["funder"] = k0; out["via"] = "fee payer"
    return out


def wallets(outdir):
    pl = jload(outdir + "/plan.json"); W = jload(outdir + "/wallets.json", {})
    buyers = collections.Counter()                                  # ranked by SOL bought in the sample
    for it in pl["pick"]:
        T = jload(f"{outdir}/tx/{it['pool']['pool']}.json")
        if not T:
            continue
        for r in T["rows"]:
            if r["sol_d"] > 0 and r["tok_d"] < 0:
                buyers[r["payer"]] += r["sol_d"]
    cap = int(os.environ.get("WALLET_CAP", "3000"))
    need = [w for w, _ in buyers.most_common() if w not in W][:cap]
    print(f"{len(buyers)} buying wallets; {len(need)} to look up; calls so far {CALLS['n']}", flush=True)
    with cf.ThreadPoolExecutor(8) as ex:
        for n, (w, r) in enumerate(zip(need, ex.map(lambda a: _safe(first_funder, a), need))):
            if r:
                W[w] = r
            if n % 200 == 0:
                jsave(outdir + "/wallets.json", W); print(f"  {n}/{len(need)} calls {CALLS['n']}", flush=True)
    jsave(outdir + "/wallets.json", W); save_calls()
    print(f"wallets done; calls {CALLS['n']}", flush=True)


def whois(outdir):
    """who the biggest net buyers are: for the TOP (12) wallets that left the most SOL in the sampled pools, their 20 newest signatures
    and 3 of those transactions (programs called, whether a DAMM v2 pool of the sample or another venue, SOL balance); and for 2 line
    creators, 5 transactions spread over their signature list (what their thousands of signatures are)"""
    import random
    pl = jload(outdir + "/plan.json"); net = collections.Counter(); pools_of = collections.defaultdict(set)
    sample_pools = {it["pool"]["pool"] for it in pl["pick"]}
    for it in pl["pick"]:
        T = jload(f"{outdir}/tx/{it['pool']['pool']}.json")
        for r in T["rows"]:
            if (r["sol_d"] > 0 and r["tok_d"] < 0) or (r["sol_d"] < 0 and r["tok_d"] > 0):
                net[r["payer"]] += r["sol_d"]; pools_of[r["payer"]].add(it["pool"]["pool"])
    top = [w for w, _ in net.most_common(int(os.environ.get("TOP", "12")))]
    out = {"wallets": {}, "creators": {}}

    def progs(tx):
        m = tx["transaction"]["message"]; ks = list(m["accountKeys"]) + list((tx["meta"].get("loadedAddresses") or {}).get("writable", [])) + \
            list((tx["meta"].get("loadedAddresses") or {}).get("readonly", []))
        ps = sorted({ks[i["programIdIndex"]][:8] for i in m["instructions"]})
        mints = sorted({b["mint"][:8] for b in tx["meta"].get("postTokenBalances") or []} - {WSOL[:8]})
        return {"programs": ps, "mints": mints, "payer": ks[0], "t": tx["blockTime"], "touches_sample_pool": bool(set(ks) & sample_pools),
                "ix": [l.split("Instruction: ")[1] for l in tx["meta"].get("logMessages") or [] if "Program log: Instruction: " in l][:6]}
    for w in top:
        s = rpc("getSignaturesForAddress", [w, {"limit": 20}])
        info = {"net_sol": net[w] / 1e9, "sample_pools": len(pools_of[w]), "newest": [x.get("blockTime") for x in s[:1]], "tx": []}
        for x in s[:3]:
            tx = rpc("getTransaction", [x["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}])
            if tx:
                info["tx"].append(progs(tx))
        bal = rpc("getBalance", [w]); info["sol_now"] = (bal.get("value") if isinstance(bal, dict) else bal) / 1e9
        out["wallets"][w] = info
    lines_ = {it["line"]: it["pool"]["creator"] for it in pl["pick"] if not it["line"].startswith("contrast")}
    for c in list(dict.fromkeys(lines_.values()))[:2]:
        s = rpc("getSignaturesForAddress", [c, {"limit": 1000}])
        picks = [s[i] for i in sorted(random.Random(1).sample(range(len(s)), min(5, len(s))))]
        out["creators"][c] = {"n_newest_page": len(s), "tx": []}
        for x in picks:
            tx = rpc("getTransaction", [x["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}])
            if tx:
                out["creators"][c]["tx"].append(progs(tx))
    jsave(outdir + "/whois.json", out); save_calls()
    print(f"whois done; calls {CALLS['n']}", flush=True)


def control(outdir):
    """which buyers the operator controls: for the TOP (400) buyers by SOL bought, the newest transactions (2 signatures and the
    newest transaction): is it paid or co-signed by a controller (CONTROLLERS, comma list: the wallets found paying the buyers'
    sweeps and the creators' clean-ups) or by a creator/relay of the 80+ SOL lines. OUTDIR/control.json"""
    pl = jload(outdir + "/plan.json"); buy = collections.Counter()
    for it in pl["pick"]:
        T = jload(f"{outdir}/tx/{it['pool']['pool']}.json")
        for r in T["rows"]:
            if r["sol_d"] > 0 and r["tok_d"] < 0:
                buy[r["payer"]] += r["sol_d"]
    cen = json.load(open("out/amm/damm7.json"))["pools"]
    links = json.load(open("out/amm/damm7_chains.json"))["links"]
    net = {p["creator"] for p in cen if p["sol"] >= 80} | {l["via"] for l in links.values() if l.get("via")}
    ctrl = set(x for x in os.environ.get("CONTROLLERS", "").split(",") if x)
    C = jload(outdir + "/control.json", {})
    top = [w for w, _ in buy.most_common(int(os.environ.get("TOP", "400"))) if w not in C]

    def one(w):
        s = rpc("getSignaturesForAddress", [w, {"limit": 2}])
        out = {"newest_t": s[0].get("blockTime") if s else None, "payer": None, "signers": [], "ctrl": False, "net": False}
        if s:
            tx = rpc("getTransaction", [s[0]["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}])
            if tx:
                m = tx["transaction"]["message"]; ks = list(m["accountKeys"]); sig = ks[:m["header"]["numRequiredSignatures"]]
                out.update(payer=ks[0], signers=sig, ctrl=bool(set(sig) & ctrl), net=bool(set(sig) & net), n_signers=len(sig))
        return w, out
    with cf.ThreadPoolExecutor(8) as ex:
        for n, (w, o) in enumerate(ex.map(lambda a: _safe(one, a) or (a, None), top)):
            if o:
                C[w] = o
    jsave(outdir + "/control.json", C); save_calls()
    print(f"control: {len(C)} buyers checked; paid/co-signed by a controller {sum(1 for v in C.values() if v and v['ctrl'])}, "
          f"by a creator/relay {sum(1 for v in C.values() if v and v['net'])}; calls {CALLS['n']}", flush=True)


def sweep(outdir):
    """the wallets a controller signs for or funds: its newest MAX_TX (2000) transactions (getSignaturesForAddress pages + getTransaction):
    every co-signer, and every recipient of SOL from it. OUTDIR/sweep_<controller>.json"""
    c = os.environ["CONTROLLER"]; mx = int(os.environ.get("MAX_TX", "2000"))
    sg, before = [], None
    while len(sg) < mx:
        prm = {"limit": 1000}
        if before:
            prm["before"] = before
        page = rpc("getSignaturesForAddress", [c, prm])
        sg += page
        if len(page) < 1000:
            break
        before = page[-1]["signature"]
    sg = [x for x in sg if not x["err"]][:mx]
    cos, funded, times = collections.Counter(), collections.Counter(), []

    def one(x):
        try:
            return rpc("getTransaction", [x["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}])
        except RuntimeError:
            return None
    with cf.ThreadPoolExecutor(8) as ex:
        for tx in ex.map(one, sg):
            if not tx:
                continue
            m = tx["transaction"]["message"]; ks = list(m["accountKeys"]) + list((tx["meta"].get("loadedAddresses") or {}).get("writable", [])) + \
                list((tx["meta"].get("loadedAddresses") or {}).get("readonly", []))
            times.append(tx["blockTime"])
            for s_ in ks[:m["header"]["numRequiredSignatures"]]:
                if s_ != c:
                    cos[s_] += 1
            for g in [m["instructions"]] + [g["instructions"] for g in tx["meta"].get("innerInstructions") or []]:
                for ix in g:
                    if ks[ix["programIdIndex"]] == "11111111111111111111111111111111" and len(ix.get("accounts", [])) >= 2:
                        raw = b58d(ix["data"])
                        if len(raw) >= 12 and int.from_bytes(raw[:4], "little") == 2 and ks[ix["accounts"][0]] == c:
                            funded[ks[ix["accounts"][1]]] += int.from_bytes(raw[4:12], "little")
    jsave(f"{outdir}/sweep_{c}.json", {"controller": c, "n_tx": len(times), "span": [min(times), max(times)] if times else None,
                                        "cosigners": cos, "funded": funded})
    save_calls()
    print(f"sweep {c[:8]}: {len(times)} tx, {len(cos)} co-signers, {len(funded)} wallets funded; calls {CALLS['n']}", flush=True)


def _safe(fn, a):
    try:
        return fn(a)
    except SystemExit:
        raise
    except Exception:
        return None


if __name__ == "__main__":
    if not URL and sys.argv[1] != "scan":
        raise SystemExit("TRITON_URL is not set")
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True); load_calls(outdir)
    try:
        {"plan": plan, "trim": trim, "fetch": fetch, "meta": meta, "wallets": wallets, "whois": whois, "control": control, "sweep": sweep}[sys.argv[1]](outdir)
    finally:
        save_calls()
