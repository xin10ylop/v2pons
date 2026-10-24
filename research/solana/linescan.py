#!/usr/bin/env python3
"""linescan.py fetch|scan CENSUS.json OUTDIR [EXTRA.json ...]: every candidate pump-and-pull line of a census, replayed (read-only;
HELIUS_API_KEY). EXTRA files (linehist.py output) add pools the census missed; their funder is set.

Lines: a funder that fed 4+ pools, or a creator with 3+ pools (census.py's funder: the sender of the creator's first SOL); with
CHAINS=name=funderA+funderB also one operator's successive funders as one line; and (HUBSOL=1, the default) pools whose creator
was funded by a hub or an unknown sender, fresh (under 20 transactions), >= 1 SOL and pulled, grouped by the exact SOL amount (3+);
and with OPS=clusters.json (opclusters.py) each creator cluster as one line. Only lines with at least one pull in the census are
fetched; LaunchLab's migrator RAYpQbFN... is left out (it never pulls). LINES=a,b keeps only lines whose key contains a or b.

fetch (cached in OUTDIR, resumable):
  meta.json         per pool: open_time and fee tier (CPMM initialize's data and its AmmConfig; AMM v4 initialize2's data, fee 0.25%)
  trades/<pool>     every successful transaction on the pool account from the creation to the last LP-mint move + 10 min (or +24 h if
                    the LP never moved): RPC signatures, parsed by Helius's /v0/transactions; per transaction the fee payer and the two
                    vaults' changes (the SOL vault: + a buy, - a sell or the pull)
  outflows/<addr>   the funder's and the creators' outgoing SOL (>= 0.005) over the line's life (Helius address history); a funder with
                    1000 signatures in under 3 days is a hub (an exchange or a service) and is not read
scan:
  wallets.json      the first funder of every buyer that has to be checked (census.creator_profile: the sender of its oldest transaction)
  per line: the fleet (payers on 2+ of the line's pools that are not the pool's creator, minus generic bots that buy across 3+ unrelated
  lines and sell or buy dust; plus single-pool buyers funded by the line's funder, its creators or its fleet, or by a parent that also
  funds single-pool buyers in another of the line's pools), the operator's buys (fleet + creator), the pump (price after the last
  operator buy / price before the first), the pull (the SOL vault emptied: a withdraw of half the SOL or more, or the vault under 5% of
  the deposit), verified outsiders (one pool of the line, not linked, first funder looked up), the pre-fleet cases and the reaction to
  later outsider buys, and the paper seat: buy at open_time (after anything in the opening second), our impact replayed on the reserves
  (others' buys keep their SOL in, sells their tokens in), sell in the slot after the operator's last buy before the pull (or after
  its first buy: 'seat_first'); -100% when the pull lands in or before our sell's slot. Fee 0.25% a leg ('fee_pool': the pool's tier).
Writes OUTDIR/linescan.json and prints the table."""
import json, os, sys, time, threading, collections, statistics as st, urllib.request, urllib.error, concurrent.futures as cf, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C
import census_fast as CF

KEY = os.environ["HELIUS_API_KEY"].strip()
rpc = CF.rpc
C.rpc = CF.rpc                                                                # census.creator_profile / parse use the adaptive limiter too
LAUNCHLAB = "RAYpQbFNq9i3mu6cKpTKKRwwHFDeK5AuZz8xvxUrCgw"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
CPMM_INIT = bytes.fromhex("afaf6d1f0d989bed")
HGAP = float(os.environ.get("HELIUS_GAP", "0.2")); _hl = threading.Lock(); _hn = [0.0]; _hg = [HGAP]; HSTATS = collections.Counter()
SIZES = (0.5, 1.0, 2.0); FEE = 0.0025; MIN_CASE = 0.01; DUST = 0.01         # an operator buy is >= DUST SOL
ONLY = [x for x in os.environ.get("LINES", "").split(",") if x]              # testing: only lines whose key contains one of these
HUBSOL = os.environ.get("HUBSOL", "1") == "1"
OPS = os.environ.get("OPS", "")                                               # opclusters.py's output: {name: [creators]}, one line each                               # also the hub-funded pools grouped by exact SOL amount
CHAINS = {c.split("=")[0]: c.split("=")[1].split("+") for c in os.environ.get("CHAINS", "").split(",") if "=" in c}  # name=funderA+funderB


def b58d(s):
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def helius(url, body=None):
    for k in range(40):
        with _hl:                                     # adaptive: the gap grows 15% on a 429 and shrinks 1% on a success
            w = _hn[0] - time.time(); _hn[0] = max(_hn[0], time.time()) + _hg[0]
        if w > 0:
            time.sleep(w)
        try:
            req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                         {"Content-Type": "application/json", "User-Agent": "research"})
            HSTATS["calls"] += 1
            out = json.load(urllib.request.urlopen(req, timeout=90))
            with _hl:
                _hg[0] = max(HGAP, _hg[0] * 0.99); HSTATS["gap_ms"] = int(_hg[0] * 1000)
            return out
        except urllib.error.HTTPError as e:
            HSTATS[f"http{e.code}"] += 1
            if e.code in (429, 500, 502, 503, 504):
                with _hl:
                    _hg[0] = min(3.0, _hg[0] * 1.15); _hn[0] = max(_hn[0], time.time()) + 0.5
                continue
            raise RuntimeError(f"helius HTTP {e.code}")
        except Exception:
            HSTATS["exc"] += 1; time.sleep(2 * (k + 1))
    raise RuntimeError("helius: no answer")


def addr_history(addr, t_min, max_pages=30):
    out, before = [], None
    for _ in range(max_pages):
        page = helius(f"https://api.helius.xyz/v0/addresses/{addr}/transactions?api-key={KEY}&limit=100" + (f"&before={before}" if before else ""))
        if not page:
            return out, True
        out += page; before = page[-1]["signature"]
        if page[-1].get("timestamp", 0) < t_min or len(page) < 100:
            return out, True
    return out, False


def jload(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def jsave(path, obj):
    tmp = path + ".tmp"; json.dump(obj, open(tmp, "w")); os.replace(tmp, path)


# ---------------------------------------------------------------- lines

def load_pools(census, extras):
    pools = {p["sig"]: p for p in json.load(open(census))["pools"] if p.get("sol")}
    for e in extras:
        for p in json.load(open(e))["pools"]:
            if p.get("sol"):
                q = pools.get(p["sig"], {}); q.update({k: v for k, v in p.items() if v is not None}); pools[p["sig"]] = q
    return list(pools.values())


def census_pulled(p):
    return bool(p.get("lp_later")) and (p.get("sol_now") is None or p["sol_now"] < 0.05 * p["sol"])


def build_lines(pools, hubs=None):
    byf, byc = collections.defaultdict(list), collections.defaultdict(list)
    for p in pools:
        if p.get("funder"):
            byf[p["funder"]].append(p)
        byc[p["creator"]].append(p)
    lines = [{"key": "funder:" + f, "kind": "funder", "id": f, "pools": ps} for f, ps in byf.items() if len(ps) >= 4]
    lines += [{"key": "creator:" + c, "kind": "creator", "id": c, "pools": ps} for c, ps in byc.items() if len(ps) >= 3]
    if hubs is not None and HUBSOL:   # creators funded by an exchange or an unknown sender: fresh, >= 1 SOL, pulled, by exact SOL amount
        bys = collections.defaultdict(list)
        for p in pools:
            if (not p.get("funder") or hubs.get(p["funder"], {}).get("hub")) and (p.get("n") or 99) < 20 and p["sol"] >= 1 and census_pulled(p):
                bys[round(p["sol"], 3)].append(p)
        lines += [{"key": f"hubsol:{a}", "kind": "hubsol", "id": f"hub-funded {a} SOL", "pools": ps} for a, ps in bys.items() if len(ps) >= 3]
    if OPS:                                          # creator clusters (opclusters.py): one operator behind exchange-funded creators
        for name, cs in json.load(open(OPS)).items():
            ps = [p for c in cs for p in byc.get(c, [])]
            if len(ps) >= 3:
                lines.append({"key": "ops:" + name, "kind": "ops", "id": name, "members": cs, "pools": ps})
    for name, addrs in CHAINS.items():                                       # one operator's successive funders, as one more line
        ps = [p for a in addrs for p in byf.get(a, [])]
        if ps:
            lines.append({"key": "chain:" + name, "kind": "chain", "id": name, "members": addrs, "pools": ps})
    for L in lines:
        L["pools"].sort(key=lambda p: p["t"]); L["n_census_pulled"] = sum(census_pulled(p) for p in L["pools"])
        L["selected"] = L["n_census_pulled"] > 0 and L["id"] != LAUNCHLAB and (not ONLY or any(o in L["key"] for o in ONLY))
    return lines


# ---------------------------------------------------------------- fetch

def pool_meta(p):
    tx = rpc("getTransaction", [p["sig"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    out = {"open_time": None, "amm_config": None, "disc": None}
    if not tx:
        return out
    prog = C.PROG[p["kind"]][0]
    ixs = tx["transaction"]["message"]["instructions"] + [i for inner in tx["meta"].get("innerInstructions") or [] for i in inner["instructions"]]
    for ix in ixs:
        if ix.get("programId") != prog or "data" not in ix or ix.get("accounts", [None])[C.POS[p["kind"]]["pool"]:][:1] != [p["pool"]]:
            continue
        raw = b58d(ix["data"])
        if p["kind"] == "cpmm":
            out["disc"] = raw[:8].hex()
            if raw[:8] == CPMM_INIT and len(raw) >= 32:
                out["open_time"] = int.from_bytes(raw[24:32], "little"); out["amm_config"] = ix["accounts"][1]
        else:
            out["disc"] = raw[:1].hex()
            if raw[:1] == b"\x01" and len(raw) >= 10:
                out["open_time"] = int.from_bytes(raw[2:10], "little")
        break
    return out


def fee_rate(cfg, cache):
    if cfg not in cache:
        a = rpc("getAccountInfo", [cfg, {"encoding": "base64"}])
        b = base64.b64decode(a["value"]["data"][0]) if a and a.get("value") else b""
        cache[cfg] = int.from_bytes(b[12:20], "little") / 1e6 if len(b) >= 20 else None
    return cache[cfg]


def pool_trades(p):
    t_end = (max(p["lp_later"]) + 600) if p.get("lp_later") else p["t"] + 86400
    t_end = min(t_end, p["t"] + 3 * 86400)
    sigs, before, complete = [], None, False
    for _ in range(80):
        prm = {"limit": 1000}
        if before:
            prm["before"] = before
        page = rpc("getSignaturesForAddress", [p["pool"], prm])
        sigs += page
        if len(page) < 1000 or (page[-1].get("blockTime") or 0) < p["t"] - 5:
            complete = True; break
        before = page[-1]["signature"]
    sigs.reverse()                                                          # oldest first, within a slot too
    keep = [s for s in sigs if not s["err"] and p["t"] - 5 <= (s.get("blockTime") or 0) <= t_end]
    truncated = len(keep) > 4000 or not complete
    keep = keep[:4000]
    order = {s["signature"]: i for i, s in enumerate(keep)}
    parsed = {}
    for k in range(0, len(keep), 100):
        batch = [s["signature"] for s in keep[k:k + 100]]
        for t in helius(f"https://api.helius.xyz/v0/transactions?api-key={KEY}", {"transactions": batch}) or []:
            parsed[t["signature"]] = t
    tok_vault = p["v1"] if p["sol_vault"] == p["v0"] else p["v0"]
    rows = []
    for s in keep:
        t = parsed.get(s["signature"])
        if t is None:
            rows.append({"i": order[s["signature"]], "t": s.get("blockTime"), "slot": s["slot"], "sig": s["signature"], "missing": True}); continue
        d = collections.Counter()
        for a in t.get("accountData") or []:
            for c in a.get("tokenBalanceChanges") or []:
                if c.get("tokenAccount") in (p["v0"], p["v1"]):
                    d[c["tokenAccount"]] += int(c["rawTokenAmount"]["tokenAmount"]) / 10 ** c["rawTokenAmount"]["decimals"]
        rows.append({"i": order[s["signature"]], "t": t.get("timestamp") or s.get("blockTime"), "slot": t.get("slot") or s["slot"], "sig": s["signature"],
                     "payer": t.get("feePayer"), "type": t.get("type"), "source": t.get("source"), "sol_d": d[p["sol_vault"]], "tok_d": d[tok_vault],
                     "err": bool(t.get("transactionError"))})
    return {"rows": rows, "n_sigs": len(sigs), "truncated": truncated, "missing": sum(1 for r in rows if r.get("missing")), "t_end": t_end,
            "fetched": int(time.time())}


def hub_check(addr):
    sigs = rpc("getSignaturesForAddress", [addr, {"limit": 1000}])
    span = (sigs[0].get("blockTime") or 0) - (sigs[-1].get("blockTime") or 0) if sigs else 0
    return {"n": len(sigs), "span_h": span / 3600, "hub": len(sigs) >= 1000 and span < 3 * 86400}


def outflows(addr, t_min):
    txs, complete = addr_history(addr, t_min)
    sent = collections.defaultdict(list)
    for t in txs:
        if t.get("timestamp", 0) < t_min or t.get("transactionError"):
            continue
        for n in t.get("nativeTransfers") or []:
            if n.get("fromUserAccount") == addr and n.get("toUserAccount") and n["amount"] >= 5 * 10 ** 6:
                sent[n["toUserAccount"]].append((t["timestamp"], n["amount"] / 1e9))
    return {"sent": sent, "n_tx": len(txs), "complete": complete}


def fetch(census, outdir, extras):
    os.makedirs(outdir + "/trades", exist_ok=True); os.makedirs(outdir + "/outflows", exist_ok=True)
    pools = load_pools(census, extras); lines = [L for L in build_lines(pools) if L["selected"]]
    hubs = jload(outdir + "/hubs.json", {})
    for L in lines:                                                         # a hub funder (an exchange) is no operator: not fetched
        if L["kind"] == "funder" and L["id"] not in hubs:
            try:
                hubs[L["id"]] = hub_check(L["id"])
            except Exception:
                pass
    jsave(outdir + "/hubs.json", hubs)
    lines = [L for L in build_lines(pools, hubs) if L["selected"]]
    hub_lines = [L["key"] for L in lines if L["kind"] == "funder" and hubs.get(L["id"], {}).get("hub")]
    lines = [L for L in lines if L["key"] not in hub_lines]
    todo = list({p["sig"]: p for L in lines for p in L["pools"]}.values())
    print(f"{len(lines)} lines selected ({len(hub_lines)} hub funders left out: {[k[7:17] for k in hub_lines]}), {len(todo)} pools", flush=True)
    meta = jload(outdir + "/meta.json", {}); cfgs = jload(outdir + "/fee_cfg.json", {})
    need = [p for p in todo if p["pool"] not in meta]
    with cf.ThreadPoolExecutor(4) as ex:
        for n, (p, m) in enumerate(zip(need, ex.map(lambda p: C.safe(pool_meta, "meta")(p), need))):
            if m:
                meta[p["pool"]] = m
            if n % 100 == 0:
                print(f"  meta {n}/{len(need)} {dict(CF.STATS)}", flush=True); jsave(outdir + "/meta.json", meta)
    for p in todo:
        m = meta.get(p["pool"])
        if m and m.get("amm_config") and "fee" not in m:
            try:
                m["fee"] = fee_rate(m["amm_config"], cfgs)
            except Exception:
                m["fee"] = None
        elif m and p["kind"] == "ammv4":
            m["fee"] = 0.0025
    jsave(outdir + "/meta.json", meta); jsave(outdir + "/fee_cfg.json", cfgs)
    def stale(p):                                   # no file, or the census now shows LP moves after the cached window
        tr = jload(f"{outdir}/trades/{p['pool']}.json", None)
        if tr is None:
            return True
        want = min((max(p["lp_later"]) + 600) if p.get("lp_later") else p["t"] + 86400, p["t"] + 3 * 86400)
        return tr.get("t_end", 0) < want and tr.get("fetched", 0) < want
    need = [p for p in todo if stale(p)]
    print(f"trades: {len(need)} pools to read", flush=True)

    def one(p):
        try:
            jsave(f"{outdir}/trades/{p['pool']}.json", pool_trades(p)); return True
        except Exception as e:
            C.FAILED["trades"] += 1; print(f"  trades failed {p['pool'][:10]}: {str(e)[:80]}", flush=True); return False
    with cf.ThreadPoolExecutor(4) as ex:
        for n, _ in enumerate(ex.map(one, need)):
            if n % 50 == 0:
                print(f"  trades {n}/{len(need)} rpc {dict(CF.STATS)} helius {dict(HSTATS)}", flush=True)
    addrs = {}
    for L in lines:
        t_min = L["pools"][0]["t"] - 2 * 86400
        for a in ([L["id"]] if L["kind"] == "funder" else L.get("members", [])):
            addrs[a] = min(addrs.get(a, 1e12), t_min)
        for p in L["pools"]:
            addrs[p["creator"]] = min(addrs.get(p["creator"], 1e12), t_min)
    for a in addrs:
        if a not in hubs:
            try:
                hubs[a] = hub_check(a)
            except Exception:
                pass
    jsave(outdir + "/hubs.json", hubs)
    need = [a for a in addrs if not os.path.exists(f"{outdir}/outflows/{a}.json") and not hubs.get(a, {}).get("hub")]
    print(f"outflows: {len(need)} wallets to read ({sum(1 for a in addrs if hubs.get(a, {}).get('hub'))} hubs skipped)", flush=True)

    def flow(a):
        try:
            jsave(f"{outdir}/outflows/{a}.json", outflows(a, addrs[a]))
        except Exception as e:
            print(f"  outflows failed {a[:10]}: {str(e)[:80]}", flush=True)
    with cf.ThreadPoolExecutor(3) as ex:
        for n, _ in enumerate(ex.map(flow, need)):
            if n % 50 == 0:
                print(f"  outflows {n}/{len(need)} helius {dict(HSTATS)}", flush=True)
    print(f"fetch done; rpc {dict(CF.STATS)} helius {dict(HSTATS)} failed {dict(C.FAILED)}", flush=True)


# ---------------------------------------------------------------- replay

def replay(p, tr, meta):
    """the pool's events in order, with the reserves after each; the pull"""
    S, T = p["sol"], (p.get("v1_amt") if p["sol_vault"] == p["v0"] else p.get("v0_amt")) or 0.0
    ev = []
    for r in sorted(tr["rows"], key=lambda r: (r["slot"], r["i"])):
        if r.get("missing") or r.get("err") or r["sig"] == p["sig"]:
            continue
        sd, td = r["sol_d"], r["tok_d"]
        if abs(sd) < 1e-9 and abs(td) < 1e-9:
            continue
        kind = "buy" if sd > 0 and td < 0 else "sell" if sd < 0 and td > 0 else "add" if sd > 0 and td > 0 else "remove" if sd < 0 and td < 0 else "other"
        S0, T0 = S, T; S += sd; T += td
        ev.append({"k": kind, "w": r["payer"], "t": r["t"], "slot": r["slot"], "sd": sd, "td": td, "S0": S0, "T0": T0, "S": S, "T": T})
    pull = None
    for n, e in enumerate(ev):
        if e["sd"] < 0 and (e["S"] < 0.05 * p["sol"] or (e["k"] == "remove" and -e["sd"] >= 0.5 * e["S0"])):
            pull = n; e["pull"] = "remove" if e["k"] == "remove" else "dump"; break
    m = meta.get(p["pool"]) or {}
    open_t = m.get("open_time")
    if open_t is not None:                     # CPMM: an open_time at or before the creation means creation + 1 s
        open_t = max(open_t, p["t"] + 1) if p["kind"] == "cpmm" else max(open_t, p["t"])
    return {"ev": ev, "pull": pull, "open": open_t if open_t is not None else (ev[0]["t"] if ev else p["t"]), "open_known": open_t is not None,
            "fee": m.get("fee"),
            "T0": (p.get("v1_amt") if p["sol_vault"] == p["v0"] else p.get("v0_amt")) or 0.0}


def seat(p, R, entry, exit_slot, x, fee):
    """our buy of x SOL before ev[entry] (ev index), replay to the end of exit_slot, sell; None if the pull lands first"""
    ev = R["ev"]
    if R["pull"] is not None and ev[R["pull"]]["slot"] <= exit_slot + 1:
        return -x
    S, T = (ev[entry]["S0"], ev[entry]["T0"]) if entry < len(ev) else (ev[-1]["S"], ev[-1]["T"]) if ev else (p["sol"], R["T0"])
    if S <= 0 or T <= 0:
        return -x
    q = T * x * (1 - fee) / (S + x * (1 - fee)); S += x; T -= q
    for e in ev[entry:]:
        if e["slot"] > exit_slot:
            break
        if e["k"] == "buy":
            o = T * e["sd"] * (1 - fee) / (S + e["sd"] * (1 - fee)); S += e["sd"]; T -= o
        elif e["k"] == "sell":
            o = S * e["td"] * (1 - fee) / (T + e["td"] * (1 - fee)); S -= o; T += e["td"]
        elif e["k"] in ("add", "remove") and e["S0"] > 0:
            f = e["S"] / e["S0"]; S *= f; T *= f                               # a deposit or partial withdraw scales the pool, not our tokens
        else:
            S += e["sd"]
    return S * q * (1 - fee) / (T + q * (1 - fee)) - x


# ---------------------------------------------------------------- scan

def scan(census, outdir, extras):
    meta = jload(outdir + "/meta.json", {}); hubs = jload(outdir + "/hubs.json", {})
    pools = load_pools(census, extras); lines = build_lines(pools, hubs)
    for L in lines:
        if L["selected"] and L["kind"] == "funder" and hubs.get(L["id"], {}).get("hub"):
            L["selected"] = False; L["excluded"] = "hub funder"
    sel = [L for L in lines if L["selected"]]
    R, TR = {}, {}
    for L in sel:
        for p in L["pools"]:
            if p["pool"] in R:
                continue
            tr = jload(f"{outdir}/trades/{p['pool']}.json", None)
            if tr is None:
                continue
            TR[p["pool"]] = tr; R[p["pool"]] = replay(p, tr, meta)
    # clusters: lines sharing a pool are one operator's
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    for L in sel:
        for p in L["pools"]:
            parent[find(p["pool"])] = find(L["key"])
    # every wallet's buys and sells over all scanned pools
    bought, big, sold, bsize = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(list)
    bpool = collections.defaultdict(list)
    for L in sel:
        for p in L["pools"]:
            if p["pool"] not in R:
                continue
            for e in R[p["pool"]]["ev"]:
                if e["k"] == "buy":
                    bought[e["w"]].add(p["pool"]); bsize[e["w"]].append(e["sd"]); bpool[(e["w"], p["pool"])].append(e["sd"])
                    if e["sd"] >= DUST:
                        big[e["w"]].add(p["pool"])
                elif e["k"] == "sell":
                    sold[e["w"]].add(p["pool"])
    clusters = {w: {find(pp) for pp in ps} for w, ps in bought.items()}

    def generic(w):                                   # buys in 3+ unrelated lines (lines sharing a pool are one cluster)
        return len(clusters[w]) >= 3

    flows = {}
    for f in os.listdir(outdir + "/outflows"):
        if f.endswith(".json"):
            flows[f[:-5]] = jload(f"{outdir}/outflows/{f}", {}).get("sent", {})
    # pass 1: provisional fleets, the buyers to look up
    prov = {}
    look = set()
    for L in sel:
        lp = {p["pool"] for p in L["pools"] if p["pool"] in R}
        creators = {p["creator"] for p in L["pools"]}
        opw = ({L["id"]} if L["kind"] == "funder" else set(L.get("members", []))) | creators
        rec = set()
        for a in opw:
            if len(flows.get(a, {})) <= 150:                                  # a service that pays 150+ wallets links nobody
                rec |= set(flows.get(a, {}))
        multi = {w for w in bought if len(bought[w] & lp) >= 2 and w not in creators}
        funded = {w for w in bought if bought[w] & lp and w in rec and w not in creators}
        core = {w for w in multi if len(big[w] & lp) >= 2 and not generic(w) and len(sold[w] & lp) < 0.5 * len(bought[w] & lp)
                and (len(big[w] & lp) >= 3 or st.median([x for pp in lp for x in bpool.get((w, pp), [])]) >= 0.1)}
        fleet = core | funded
        prov[L["key"]] = (lp, creators, opw, rec, core, fleet, multi, funded)
        with_op, cand_pre, cand_post = 0, set(), []
        for p in L["pools"]:
            if p["pool"] not in R:
                continue
            ev = R[p["pool"]]["ev"]; pull = R[p["pool"]]["pull"]; end = pull if pull is not None else len(ev)
            first_op = next((n for n, e in enumerate(ev[:end]) if e["k"] == "buy" and e["sd"] >= DUST and (e["w"] in fleet or e["w"] == p["creator"])), end)
            with_op += first_op < end
            for n, e in enumerate(ev[:end]):
                if e["k"] == "buy" and e["w"] not in fleet and e["w"] not in opw and len(bought[e["w"]] & lp) == 1 and e["sd"] >= MIN_CASE:
                    if n < first_op:
                        cand_pre.add(e["w"])
                    elif e["sd"] >= 0.05:
                        cand_post.append((e["sd"], e["w"]))
        if with_op >= 0.5 * max(1, len(lp)):                                   # buyers are checked only where a fleet shows up
            look |= cand_pre | {w for _, w in sorted(cand_post, reverse=True)[:150]} | (core - funded)
    wallets = jload(outdir + "/wallets.json", {})
    need = sorted(w for w in look if w not in wallets)
    print(f"buyer lookups: {len(look)} wallets, {len(need)} new", flush=True)
    with cf.ThreadPoolExecutor(6) as ex:
        for n, r in enumerate(ex.map(C.safe(C.creator_profile, "wallet"), need)):
            if r:
                wallets[r[0]] = r[1]
            if n % 200 == 0:
                print(f"  lookups {n}/{len(need)} {dict(CF.STATS)}", flush=True); jsave(outdir + "/wallets.json", wallets)
    jsave(outdir + "/wallets.json", wallets)
    # parents that fund single-pool buyers in 2+ pools of a line: hub check
    par_need = set()
    for L in sel:
        lp, creators, opw, rec, core, fleet, multi, funded = prov[L["key"]]
        byparent = collections.defaultdict(set)
        for w in look:
            if w in wallets and wallets[w].get("funder") and wallets[w]["n"] < 1000 and len(bought[w] & lp) == 1:
                byparent[wallets[w]["funder"]] |= bought[w] & lp
        par_need |= {a for a, ps in byparent.items() if len(ps) >= 2 and a not in hubs}
    for a in sorted(par_need):
        try:
            hubs[a] = hub_check(a)
        except Exception:
            pass
    jsave(outdir + "/hubs.json", hubs)

    res = []
    for L in sel:
        res.append(analyse(L, R, TR, prov[L["key"]], wallets, hubs, bought, sold, generic, clusters, flows))
    jsave(outdir + "/linescan.json", res)
    report(res, lines)


def analyse(L, R, TR, provL, wallets, hubs, bought, sold, generic, clusters, flows):
    lp, creators, opw, rec, core, fleet0, multi, funded = provL
    ps = [p for p in L["pools"] if p["pool"] in R]
    opl = {a for a in opw if not hubs.get(a, {}).get("hub") and len(flows.get(a, {})) <= 150}   # a hub or a service links nobody
    # linked single-pool buyers
    def first_funder(w):
        x = wallets.get(w) or {}
        return x.get("funder") if x.get("n", 1000) < 1000 else None
    linked = {}
    for w in bought:
        if w in fleet0 or len(bought[w] & lp) != 1:
            continue
        f = first_funder(w)
        if f and (f in opl or f in fleet0):
            linked[w] = "funded by the line"
    byparent = collections.defaultdict(set)
    for w in bought:
        if w not in fleet0 and len(bought[w] & lp) == 1 and first_funder(w):
            byparent[first_funder(w)].add(w)
    for a, ws in byparent.items():
        if len({pp for w in ws for pp in bought[w] & lp}) >= 2 and a in hubs and not hubs[a]["hub"] and a not in opw:
            for w in ws:
                linked.setdefault(w, "parent funds buyers in 2+ pools")
    def busy(w):
        return (wallets.get(w) or {}).get("n", 0) >= 1000

    def harvested(w):                                 # the pull lands within 60 s of its last buy in half its pools: a victim
        hit = n = 0
        for pp in bought[w] & lp:
            ev, pull = R[pp]["ev"], R[pp]["pull"]
            if pull is None:
                continue
            tb = [e["t"] for e in ev[:pull] if e["w"] == w and e["k"] == "buy"]
            if tb:
                n += 1; hit += ev[pull]["t"] - max(tb) <= 60
        return n > 0 and hit >= 0.5 * n
    victims = {w for w in core - funded if busy(w) or harvested(w)}
    fleet0 = fleet0 - victims
    for w in victims:
        linked.pop(w, None)
    fleet = fleet0 | set(linked)

    def who(e, p):
        w = e["w"]
        if w == p["creator"]:
            return "creator"
        if w in fleet or w in opw:
            return "op"
        if w in multi:
            return "bot" if generic(w) or w in victims else "amb"   # bot: 3+ unrelated lines, or a busy / harvested repeat buyer;
        x = wallets.get(w)                            # amb: 2+ pools of this line, not the fleet's shape (sells, or dust) and not funded
        return "out" if x else "out?"
    pools_out = []
    for p in ps:
        Rp = R[p["pool"]]; ev = Rp["ev"]; pull = Rp["pull"]; end = pull if pull is not None else len(ev)
        for e in ev:
            e["who"] = who(e, p)
        opb = [n for n, e in enumerate(ev[:end]) if e["k"] == "buy" and e["who"] in ("op", "creator") and e["sd"] >= DUST]
        price = lambda n: ev[n]["S"] / ev[n]["T"] if ev[n]["T"] > 0 else None
        price0 = lambda n: ev[n]["S0"] / ev[n]["T0"] if ev[n]["T0"] > 0 else None
        p_open = p["sol"] / Rp["T0"] if Rp["T0"] else None
        o = {"pool": p["pool"], "creator": p["creator"], "t": p["t"], "sol0": p["sol"], "kind": p["kind"], "fee": Rp["fee"], "open_off": Rp["open"] - p["t"],
             "open_known": Rp["open_known"], "n_ev": len(ev), "truncated": TR[p["pool"]]["truncated"], "missing": TR[p["pool"]]["missing"],
             "pulled": pull is not None, "pull_s": (ev[pull]["t"] - p["t"]) if pull is not None else None,
             "pull_kind": ev[pull]["pull"] if pull is not None else None, "pull_who": ev[pull]["who"] if pull is not None else None,
             "pull_sol": -ev[pull]["sd"] if pull is not None else None, "census_pulled": census_pulled(p),
             "op_buys": [(ev[n]["t"] - Rp["open"], round(ev[n]["sd"], 4), ev[n]["who"]) for n in opb],
             "op_sol": sum(ev[n]["sd"] for n in opb), "creator_buys": sum(1 for n in opb if ev[n]["who"] == "creator")}
        if opb:
            pb, pa = price0(opb[0]), price(opb[-1])
            o["pump"] = pa / pb if pb and pa else None
            o["first_op_s"] = ev[opb[0]]["t"] - Rp["open"]; o["last_op_s"] = ev[opb[-1]]["t"] - Rp["open"]
            o["pull_after_last_op_s"] = (ev[pull]["t"] - ev[opb[-1]]["t"]) if pull is not None else None
            o["op_at_open"] = ev[opb[0]]["t"] <= Rp["open"]
        pk = max((price(n) for n in range(end) if price(n)), default=None)
        o["peak"] = pk / p_open if pk and p_open else None
        first_op = opb[0] if opb else end
        # pre-fleet outsider buys (verified: one pool of the line, first funder looked up, not linked)
        pre = [n for n in range(first_op) if ev[n]["k"] == "buy" and ev[n]["who"] in ("out", "bot") and ev[n]["sd"] >= MIN_CASE]
        if pre:
            ws = {ev[n]["w"] for n in pre}
            held = {}
            for w in ws:
                b = -sum(e["td"] for e in ev[:first_op] if e["w"] == w and e["k"] == "buy")
                s_ = sum(e["td"] for e in ev[:first_op] if e["w"] == w and e["k"] == "sell")
                held[w] = b > 0 and s_ < 0.5 * b
            o["pre"] = {"wallets": sorted(ws), "sol": round(sum(ev[n]["sd"] for n in pre), 4), "max": round(max(ev[n]["sd"] for n in pre), 4),
                        "first_s": ev[pre[0]]["t"] - Rp["open"], "last_t": ev[pre[-1]]["t"], "held_sol": round(sum(ev[n]["sd"] for n in pre if held[ev[n]["w"]]), 4),
                        "fleet_came": bool(opb), "fleet_sol": o["op_sol"],
                        "pull_delay_s": (ev[pull]["t"] - ev[pre[-1]]["t"]) if pull is not None else None,
                        "wallet_info": {w: dict({k: (wallets.get(w) or {}).get(k) for k in ("n", "funder", "funded_sol")}, cls="generic bot" if w in multi else "one pool", line_pools=len(bought[w] & lp), clusters=len(clusters[w]))
                                        for w in ws}}
        # later outsider buys: the pull's delay after each
        o["post"] = [(round(ev[n]["sd"], 4), (ev[pull]["t"] - ev[n]["t"]) if pull is not None else None) for n in range(first_op, end)
                     if ev[n]["k"] == "buy" and ev[n]["who"] in ("out", "bot") and n > first_op and ev[n]["sd"] >= MIN_CASE]
        o["amb_buys"] = [(ev[n]["t"] - Rp["open"], round(ev[n]["sd"], 4)) for n in range(end) if ev[n]["k"] == "buy" and ev[n]["who"] == "amb" and ev[n]["sd"] >= DUST]
        o["unverified_buys"] = sum(1 for n in range(end) if ev[n]["k"] == "buy" and ev[n]["who"] == "out?")
        o["bot_buys"] = sum(1 for n in range(end) if ev[n]["k"] == "buy" and ev[n]["who"] == "bot")
        pools_out.append(o)
    # line medians (pools without a pre-fleet case)
    clean = [o for o in pools_out if "pre" not in o]
    med = lambda xs: st.median(xs) if xs else None
    ref_pull = med([o["pull_s"] for o in clean if o["pulled"]]) or med([o["pull_s"] for o in pools_out if o["pulled"]])  # no clean pool: all
    ref_last = med([o["last_op_s"] for o in pools_out if o.get("last_op_s") is not None])
    ref_first = med([o["first_op_s"] for o in pools_out if o.get("first_op_s") is not None])
    ref_op = med([o["op_sol"] for o in clean if o["op_buys"]]) or med([o["op_sol"] for o in pools_out if o["op_buys"]])
    min_clean_pull = min([o["pull_s"] for o in clean if o["pulled"]], default=None)
    for o in pools_out:
        c = o.get("pre")
        if not c:
            continue
        early = o["pulled"] and ((c["pull_delay_s"] is not None and c["pull_delay_s"] < 120) or bool(min_clean_pull and o["pull_s"] < 0.8 * min_clean_pull))
        c["fleet_sol_vs_line"] = (c["fleet_sol"] / ref_op) if ref_op else None
        if c["fleet_came"]:
            c["outcome"] = "early pull" if early else "fleet reduced" if (c["fleet_sol_vs_line"] or 0) < 0.5 else "tolerated"
        elif ref_first is not None and c["first_s"] > ref_first + 60:
            c["outcome"] = "skipped, but the outsider came after the fleet's usual start"     # no evidence either way
        else:
            c["outcome"] = "skipped, pulled" if o["pulled"] else "skipped, not pulled"
        c["fleet_sol_vs_line"] = (c["fleet_sol"] / ref_op) if ref_op else None
    # the seat
    for o in pools_out:
        p = next(q for q in ps if q["pool"] == o["pool"]); Rp = R[p["pool"]]; ev = Rp["ev"]; end = Rp["pull"] if Rp["pull"] is not None else len(ev)
        entry = next((n for n, e in enumerate(ev) if e["t"] > Rp["open"]), len(ev))
        later_op = [n for n in range(entry, end) if ev[n]["k"] == "buy" and ev[n]["who"] in ("op", "creator") and ev[n]["sd"] >= DUST]
        o["ahead_of_seat"] = [(ev[n]["who"], round(ev[n]["sd"], 4)) for n in range(entry) if ev[n]["k"] == "buy" and ev[n]["sd"] >= DUST]

        def slot_at(t_rel):
            t_abs = Rp["open"] + t_rel
            prior = [e for e in ev if e["t"] <= t_abs]
            return prior[-1]["slot"] if prior else (ev[0]["slot"] - 1 if ev else 0)
        for tag, n_exit, fallback in (("seat", later_op[-1] if later_op else None, ref_last), ("seat_first", later_op[0] if later_op else None, ref_first)):
            if n_exit is not None:
                xs = ev[n_exit]["slot"]
            elif fallback is not None:
                xs = slot_at(fallback)
            else:
                xs = None
            o[tag] = {str(x): (round(seat(p, Rp, entry, xs, x, FEE), 4) if xs is not None and ev else None) for x in SIZES}
            if Rp["fee"] and abs(Rp["fee"] - FEE) > 1e-9 and tag == "seat":
                o["seat_fee_pool"] = {str(x): (round(seat(p, Rp, entry, xs, x, Rp["fee"]), 4) if xs is not None and ev else None) for x in SIZES}
            o[tag + "_exit_by"] = "op buy" if n_exit is not None else "line median" if xs is not None else None
    # line summary
    ok = [o for o in pools_out if not o["truncated"]]
    ts = [o["t"] for o in ok] or [p["t"] for p in L["pools"]]
    span_d = (max(ts) - min(ts)) / 86400
    cases = [o for o in ok if o.get("pre")]
    fo = [o for o in cases if o["pre"]["outcome"] == "tolerated" and o["pre"]["held_sol"] >= 0.1]
    fw = [o for o in cases if o["pre"]["outcome"] == "tolerated" and o["pre"]["held_sol"] < 0.1]
    clean_ok = [o for o in ok if "pre" not in o]
    base_skip = (sum(1 for o in clean_ok if not o["op_buys"]) / len(clean_ok)) if clean_ok else None
    # a skip counts against the seat only when the line rarely skips a pool nobody bought early
    ag = [o for o in cases if o["pre"]["outcome"] == "early pull" or (o["pre"]["outcome"] == "skipped, pulled" and base_skip is not None and base_skip <= 0.25)]
    skip_inc = [o for o in cases if o["pre"]["outcome"] == "skipped, pulled" and o not in ag]
    reduced = [o for o in cases if o["pre"]["outcome"] == "fleet reduced"]
    pumped = [o for o in ok if o.get("pump")]
    with_fleet = len([o for o in ok if o["op_buys"]])
    if not ok:
        verdict = "NO DATA"
    elif with_fleet < 0.5 * len(ok) or (med([o["pump"] for o in pumped]) or 0) < 1.3:
        verdict = "NO PUMP"
    elif len(fo) >= 2 and not ag:
        verdict = "OPEN"
    elif len(ag) >= 2 and len(ag) > len(fo):
        verdict = "CLOSED"
    else:
        verdict = "UNKNOWN"
    buckets = collections.defaultdict(list)
    for o in ok:
        for sz, d in o["post"]:
            b = "<0.1" if sz < 0.1 else "0.1-0.5" if sz < 0.5 else "0.5-2" if sz < 2 else ">=2"
            buckets[b].append(d)
    react = {b: {"n": len(v), "pulled_within_60s": sum(1 for d in v if d is not None and d <= 60), "median_delay_s": med([d for d in v if d is not None])}
             for b, v in buckets.items()}
    seat_tot = {k: {str(x): round(sum(o[k][str(x)] for o in ok if o[k][str(x)] is not None), 3) for x in SIZES} for k in ("seat", "seat_first")}
    seat_win = {k: {str(x): f"{sum(1 for o in ok if (o[k][str(x)] or 0) > 0)}/{sum(1 for o in ok if o[k][str(x)] is not None)}" for x in SIZES}
                for k in ("seat", "seat_first")}
    lost = {str(x): sum(1 for o in ok if o["seat"][str(x)] is not None and o["seat"][str(x)] <= -x + 1e-9) for x in SIZES}
    return {"key": L["key"], "kind": L["kind"], "id": L["id"], "n_pools": len(L["pools"]), "n_scanned": len(ok), "n_truncated": len(pools_out) - len(ok),
            "first": min(ts), "last": max(ts), "span_d": span_d, "per_day": len(ok) / max(span_d, 1.0),
            "creators": len({p["creator"] for p in L["pools"]}), "fresh_creators": sum(1 for p in L["pools"] if (p.get("n") or 0) < 20),
            "sol_sizes": sorted({round(p["sol"], 3) for p in L["pools"]}), "fees": sorted({o["fee"] for o in ok if o["fee"]}),
            "funder_hub": hubs.get(L["id"], {}).get("hub") if L["kind"] == "funder" else None,
            "pulled": sum(o["pulled"] for o in ok), "pull_min_median": (med([o["pull_s"] for o in ok if o["pulled"]]) or 0) / 60,
            "pull_min_range": [min([o["pull_s"] / 60 for o in ok if o["pulled"]], default=None), max([o["pull_s"] / 60 for o in ok if o["pulled"]], default=None)],
            "fleet_core": len(core), "fleet_funded": len(funded - core), "fleet_linked": len(linked), "fleet": sorted(fleet & set(bought)),
            "multi_not_fleet": {"bot": len([w for w in multi - fleet if generic(w)]), "victims": len(victims),
                                "amb": len([w for w in multi - fleet if not generic(w) and w not in victims])},
            "pools_with_op_buys": with_fleet, "op_sol_median": med([o["op_sol"] for o in ok if o["op_buys"]]),
            "pump_median": med([o["pump"] for o in pumped]), "pump_range": [min([o["pump"] for o in pumped], default=None), max([o["pump"] for o in pumped], default=None)],
            "first_op_s_median": ref_first, "last_op_s_median": ref_last, "op_at_open": sum(1 for o in ok if o.get("op_at_open")),
            "pull_after_last_op_min_median": (med([o["pull_after_last_op_s"] for o in ok if o.get("pull_after_last_op_s") is not None]) or 0) / 60,
            "cases": [{"pool": o["pool"], **{k: v for k, v in o["pre"].items() if k != "wallet_info"}, "pull_min": (o["pull_s"] or 0) / 60,
                       "ref_pull_min": (ref_pull or 0) / 60, "wallet_info": o["pre"]["wallet_info"]} for o in cases],
            "evidence": {"for_held": len(fo), "for_weak": len(fw), "against": len(ag), "skip_inconclusive": len(skip_inc), "fleet_reduced": len(reduced), "base_skip": base_skip,
                         "max_held_sol": max([o["pre"]["held_sol"] for o in fo], default=0),
                         "max_against_sol": max([o["pre"]["max"] for o in ag], default=0)},
            "verdict": verdict, "reaction": react, "seat": seat_tot, "seat_won": seat_win, "seat_lost_to_pull": lost,
            "seat_fee_pool": {str(x): round(sum((o.get("seat_fee_pool") or o["seat"])[str(x)] or 0 for o in ok), 3) for x in SIZES},
            "unverified_buys": sum(o["unverified_buys"] for o in ok), "bot_buys": sum(o["bot_buys"] for o in ok),
            "amb_buys": sum(len(o["amb_buys"]) for o in ok), "pools": pools_out}


def report(res, lines):
    day = lambda t: time.strftime("%m-%d", time.gmtime(t))
    order = {"OPEN": 0, "UNKNOWN": 1, "CLOSED": 2, "NO PUMP": 3, "NO DATA": 4}
    res = sorted(res, key=lambda r: (order[r["verdict"]], -(r["seat"]["seat"]["1.0"] or 0)))
    print(f"\n{len(res)} lines scanned ({sum(1 for L in lines if not L['selected'])} candidate groups without a pull, or LaunchLab, left out)")
    for r in res:
        e = r["evidence"]; s = r["seat"]["seat"]
        print(f"{r['verdict']:8s} {r['key'][:52]:52s} pools {r['n_scanned']:3d} ({r['per_day']:.1f}/d, {day(r['first'])}..{day(r['last'])}) "
              f"SOL {r['sol_sizes'][0]}-{r['sol_sizes'][-1]} pulled {r['pulled']} ({r['pull_min_median']:.0f} min) | fleet {len(r['fleet'])} "
              f"in {r['pools_with_op_buys']} pools, pump x{(r['pump_median'] or 0):.2f} first +{(r['first_op_s_median'] or 0):.0f}s | pre-fleet "
              f"for {e['for_held']}(+{e['for_weak']} weak) against {e['against']} | seat 0.5/1/2: {s['0.5']:+.2f}/{s['1.0']:+.2f}/{s['2.0']:+.2f} "
              f"won {r['seat_won']['seat']['1.0']} lost-to-pull {r['seat_lost_to_pull']['1.0']}")


if __name__ == "__main__":
    {"fetch": fetch, "scan": scan}[sys.argv[1]](sys.argv[2], sys.argv[3], sys.argv[4:])
