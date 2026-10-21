#!/usr/bin/env python3
"""base_v2_roster.py: the V2 line's fleet roster from the chain (docs/BASE_V2.md section 4), written to BASE_V2_ROSTER_FILE
(/etc/flip/base_v2_roster.json) for src/base_v2_engine.py, which reads it at its start and again whenever its mtime changes and never adds
to it. A wallet is in the roster when it bought on at least MIN_PAIRS (3) of the line's fresh-wallet pairs created in the last DAYS (3) with
one of the fleet's two shapes, straight to the router (BASE_V2_ROUTER) with the swap selectors 7ff36ab5 or b6f9de95: a type-2 transaction
at a 0.001 gwei priority fee from a nonce under 20,000, or a legacy (type 0) transaction at a gas price of at most 0.01 gwei, any nonce.
The legacy shape is the fleet of Oct 20 (53 wallets at 0.0060-0.0066 gwei, nonces up to 115k, 1,611 buys on the 35 tolerant pairs, none
followed by a reaction); left out, every one of its buys is an outsider's, the scheduled pull 3-9 blocks after one ends the tier and the
outsider exit sells at +8. None of the day's 10 real outsiders (buys pulled 3-6 blocks later) has either shape. A pair of the line: PairCreated with WETH on
BASE_V2_FACTORY whose creation transaction is the creator's nonce BASE_V2_CREATOR_NONCE (2) to the router with BASE_V2_CREATE_SELECTOR
(f305d719). The probe (BASE_V2_PROBE) goes under its own key, never into `wallets`: the engine classes it by BASE_V2_PROBE, and stage 0 wants
its creation-block buy logged as outsider_buy (section 9). The chain is read through research/chase/v2scan.py's Scan on the archive
endpoint (BASE_V2_ARCHIVE_URL, else deploy/base_v2_sim.py's): the creations first, then the events and the first 40 swaps' transactions of
the line's pairs only; about 10-20 minutes for 3 days.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_roster.py                        # 3 days, >= 3 pairs, the file's wallets kept beside the build
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_roster.py --replace              # the build alone (a lookup the endpoint refused loses its wallet)
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_roster.py --days 5 --min-pairs 2 --out /tmp/roster.json
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_roster.py --show               # the file as it is: built, count, age
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_v2_roster.py --merge FILE         # FILE's wallets added to the file (no chain read)

The file ({"built": <utc>, "wallets": [...], "probe": [...], "days", "blocks", "pairs", "rule"}) is written whole and in place when it exists
(the same inode: flip-base-v2 has the file bound into its mount namespace, and a rename would leave the running engine the old one), else
created atomically (a temporary file renamed over the path). The engine keeps its last roster while a read fails and reads again 5 s
later, so a torn read costs nothing. Fewer than MIN_WALLETS (10) wallets means the fleet's shape changed or the chain was not read: the file
is not touched unless --force. deploy/base_v2_setup.sh installs the daily cron (00:20 UTC, /var/log/flip/base_v2_roster.log)."""
import argparse, datetime, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "research", "chase"))
import base_v2_wallet as BV

BLOCKS_A_DAY = 43200                                                                     # 2.000 s blocks
BUY_SELS = ("0x7ff36ab5", "0xb6f9de95")                                                  # swapExactETHForTokens, ...SupportingFeeOnTransferTokens
TIP_WEI = 10 ** 6                                                                        # the fleet's 0.001 gwei priority fee
MAX_NONCE = 20_000                                                                       # (the type-2 shape only)
LEGACY_MAX_WEI = 10 ** 7                                                                 # the legacy fleet's gas price cap, 0.01 gwei
MIN_WALLETS = 10
HORIZON, SWAPWIN, SWAP_CAP = 900, 300, 40                                                # the pull window, the swaps window, the swaps looked up a pair


def archive_url():
    v = BV.setting("BASE_V2_ARCHIVE_URL")
    if v:
        return v
    import base_v2_sim                                                                   # its RPC: the archive gateway of docs/BASE_V2.md section 5
    return base_v2_sim.RPC


def build(days, min_pairs, say=print):
    """the roster from the chain: ({... the file's content ...}, the stats)"""
    import v2scan
    url = archive_url(); router = BV.router()[2:]; sel = "0x" + (BV.setting("BASE_V2_CREATE_SELECTOR", "f305d719") or "f305d719").lower()
    nonce = int(BV.setting("BASE_V2_CREATOR_NONCE", "2") or 2)
    sc = v2scan.Scan(url, BV.factory(), BV.weth(), horizon=HORIZON, swapwin=SWAPWIN, threads=4, swap_cap=SWAP_CAP, log=say)
    head = sc.head(); b0 = max(1, head - days * BLOCKS_A_DAY)
    say(f"reading {BV.factory()} on {BV.BW.host(url)}: blocks {b0:,}-{head:,} ({days} days)")
    pairs = sc.pairs(b0, head); say(f"WETH pairs created: {len(pairs)}; their creation transactions:")
    txs = sc.fill_txs([p["tx"] for p in pairs.values()])
    line = {}
    for k, p in pairs.items():
        t = txs.get(p["tx"])
        if t and t[2] == nonce and t[1] == router and t[4] == sel:
            line[k] = p
    say(f"pairs of the line (creator nonce {nonce}, {sel} to the router): {len(line)}; their events and the first {SWAP_CAP} swaps' transactions:")
    sc.fill_events(line)
    txs = sc.fill_txs([s[6] for p in line.values() for s in p["swaps"][:SWAP_CAP]], txs)
    by_wallet, by_wallet_any = {}, {}
    for pair, p in line.items():
        for s in p["swaps"][:SWAP_CAP]:
            eth_in = s[2] if p["weth_is0"] else s[3]
            t = txs.get(s[6])
            if eth_in <= 0 or not t:
                continue
            frm, to, n, _value, sel_, typ, tip = t
            if to != router or sel_ not in BUY_SELS:
                continue
            by_wallet_any.setdefault("0x" + frm, set()).add(pair)
            if (typ == 2 and tip == TIP_WEI and n < MAX_NONCE) or (typ == 0 and tip <= LEGACY_MAX_WEI):
                by_wallet.setdefault("0x" + frm, set()).add(pair)
    wallets = sorted(w for w, ps in by_wallet.items() if len(ps) >= min_pairs)
    off_shape = sorted(w for w, ps in by_wallet_any.items() if len(ps) >= min_pairs and w not in wallets)
    built = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"built": built, "wallets": wallets, "probe": BV.probes(), "days": days, "blocks": [b0, head], "pairs": len(line), "min_pairs": min_pairs,
            "rule": f"bought on >= {min_pairs} pairs of the line (creator nonce {nonce}) in {days} days, {'/'.join(BUY_SELS)} to the router: type 2 at tip {TIP_WEI} wei "
                    f"and nonce < {MAX_NONCE}, or legacy at a gas price <= {LEGACY_MAX_WEI} wei",
            "off_shape": off_shape}
    return data, {"pairs_all": len(pairs), "line": len(line), "off_shape": len(off_shape)}


def write(path, data):
    """the file whole: in place through the existing inode (what a running flip-base-v2 sees), else created atomically; 'in place' / 'created'"""
    text = json.dumps(data, indent=1).encode()
    if os.path.exists(path):
        fd = os.open(path, os.O_WRONLY)
        try:
            os.pwrite(fd, text, 0); os.ftruncate(fd, len(text)); os.fsync(fd)
        finally:
            os.close(fd)
        return "in place"
    tmp = path + ".tmp"
    if os.path.lexists(tmp):
        os.unlink(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600); os.write(fd, text); os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    return "created"


def merge(path, src):
    """the file's wallets and src's (a roster built elsewhere: no chain read on a rate-limited box), the union written in place; never removes"""
    old = json.load(open(path)) if os.path.exists(path) else {"wallets": []}; new = json.load(open(src))
    ws_old = {w.lower() for w in old.get("wallets") or []}; ws_new = {w.lower() for w in new.get("wallets") or []}
    if len(ws_new) < MIN_WALLETS:
        sys.exit(f"{src}: {len(ws_new)} wallets, under {MIN_WALLETS}: not a roster; {path} is NOT touched")
    data = dict(new, wallets=sorted(ws_old | ws_new), probe=BV.probes(), built=max(str(old.get("built") or ""), str(new.get("built") or "")),
                rule=f"merged: {old.get('rule') or old.get('source') or '?'} | {new.get('rule') or new.get('source') or '?'}")
    how = write(path, data)
    print(f"merged: {len(ws_old)} + {len(ws_new - ws_old)} new = {len(data['wallets'])} wallets, written {how}: {path} (built {data['built']})", flush=True)


def show(path):
    try:
        d = json.load(open(path)); age = (time.time() - os.path.getmtime(path)) / 3600
    except FileNotFoundError:
        sys.exit(f"{path}: no roster yet (base_v2_roster.py builds it)")
    except Exception as e:
        sys.exit(f"{path}: not a roster ({type(e).__name__}: {str(e)[:80]})")
    ws = d.get("wallets") if isinstance(d, dict) else None
    print(f"{path}: {len(ws) if isinstance(ws, list) else 'NO'} wallets, built {d.get('built')} ({age:.1f} h ago), {d.get('pairs')} pairs of the line in {d.get('days')} days"
          + (f", {len(d['off_shape'])} wallet(s) with the pairs but not the shape" if d.get("off_shape") else ""))


def main(argv):
    ap = argparse.ArgumentParser(description="the V2 line's fleet roster from the chain (RUNBOOK 4m step 4)")
    ap.add_argument("--days", type=int, default=3, help="the window in days (default 3)")
    ap.add_argument("--min-pairs", type=int, default=3, help="pairs of the line a wallet must have bought on (default 3)")
    ap.add_argument("--out", default=None, help="the file to write (default BASE_V2_ROSTER_FILE)")
    ap.add_argument("--force", action="store_true", help=f"write even fewer than {MIN_WALLETS} wallets")
    ap.add_argument("--show", action="store_true", help="print the file as it is and exit")
    ap.add_argument("--replace", action="store_true", help="write the build alone; by default the file's wallets are kept beside it (a build that lost lookups never shrinks it)")
    ap.add_argument("--merge", metavar="FILE", default=None, help="add FILE's wallets (a roster built elsewhere) to the file, no chain read")
    a = ap.parse_args(argv)
    path = a.out or BV.roster_file()
    if a.show:
        return show(path)
    if a.merge:
        return merge(path, a.merge)
    if a.days < 1 or a.days > 30 or a.min_pairs < 1:
        sys.exit("--days is 1..30 and --min-pairs at least 1")
    say = lambda s: print(f"{time.strftime('%H:%M:%S')} {s}", flush=True)
    t0 = time.time()
    data, stats = build(a.days, a.min_pairs, say)
    n = len(data["wallets"])
    print(f"roster: {n} wallets (bought on >= {a.min_pairs} of {stats['line']} pairs of the line in {a.days} days, blocks {data['blocks'][0]:,}-{data['blocks'][1]:,}; "
          f"{stats['pairs_all']} WETH pairs in all; {stats['off_shape']} wallet(s) with the pairs but not the fleet's shape; {time.time() - t0:.0f} s)", flush=True)
    if os.path.exists(path) and not a.replace and n >= MIN_WALLETS:
        try:
            kept = {w.lower() for w in json.load(open(path)).get("wallets") or []} - set(data["wallets"])
        except Exception:
            kept = set()
        data["wallets"] = sorted(set(data["wallets"]) | kept)
        print(f"kept {len(kept)} wallet(s) of the file the build did not see: {len(data['wallets'])} in all (--replace writes the build alone)", flush=True)
    if n < MIN_WALLETS and not a.force:
        sys.exit(f"only {n} wallets, under {MIN_WALLETS}: the fleet's shape may have changed or the chain was not read; {path} is NOT touched (--force writes it anyway)")
    how = write(path, data)
    print(f"written {how}: {path} (built {data['built']}); flip-base-v2 reads it within 5 s when it has the file bound in, at its next start otherwise", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
