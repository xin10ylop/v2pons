#!/usr/bin/env python3
"""feedrace.py [--seconds 120] [--poll-ms 100] [--file urls.txt] URL...: which source shows a new Robinhood Chain block first, from this box.

Each source is watched side by side for SECONDS:
  https://...        polled with eth_blockNumber every POLL_MS; once a new number shows, its full block (eth_getBlockByNumber, with the
                     transactions: what the engine needs) is fetched from the same source and timed
  wss://...          an eth_subscribe newHeads websocket (Alchemy, publicnode, ...)
  feed:wss://...     a Nitro sequencer feed (Robinhood's own, Dwellir's): the reference when it is reachable
For every block number, the earliest arrival over all sources is the reference. Per source: the share of blocks it showed, how far behind
the earliest it showed them (median, p90, ms), and for the https sources how long the full block took after that (median, ms): the
engine sees a block at "behind + full block". URLs may carry an API key: only the host is printed. Read-only; at the default pace about
10 requests a second a source. Put keyed URLs in a file (--file, one a line) rather than on the command line, so they stay out of the
shell history.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/feedrace.py --file ~/sources.txt"""
import sys, time, json, threading, asyncio, statistics as st, urllib.request, urllib.parse, collections

ARGS = sys.argv[1:]
SECONDS = float(ARGS[ARGS.index("--seconds") + 1]) if "--seconds" in ARGS else 120.0
POLL = float(ARGS[ARGS.index("--poll-ms") + 1]) / 1000 if "--poll-ms" in ARGS else 0.1
URLS = [a for i, a in enumerate(ARGS) if not a.startswith("--") and (i == 0 or ARGS[i - 1] not in ("--seconds", "--poll-ms", "--file"))]
if "--file" in ARGS:
    URLS += [l.strip() for l in open(ARGS[ARGS.index("--file") + 1]) if l.strip() and not l.startswith("#")]
seen = collections.defaultdict(dict)        # label -> {block: wall time first seen}
full = collections.defaultdict(list)        # label -> [seconds for the full block]
errors = collections.Counter()
t_end = time.time() + SECONDS


def label(u):
    p = urllib.parse.urlparse(u.replace("feed:", "", 1))
    kind = "feed" if u.startswith("feed:") else ("ws" if p.scheme in ("ws", "wss") else "http")
    return f"{kind} {p.hostname}" + ("" if p.path in ("", "/") else " (keyed)" if len(p.path) > 12 else p.path)


def post(u, method, params):
    req = urllib.request.Request(u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), {"Content-Type": "application/json", "User-Agent": "feedrace/1"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())["result"]


def http_watch(u):
    lb = label(u); last = None
    while time.time() < t_end:
        t0 = time.time()
        try:
            n = int(post(u, "eth_blockNumber", []), 16); now = time.time()
            if last is None:
                last = n
            elif n > last:
                for b in range(last + 1, n + 1):
                    seen[lb].setdefault(b, now)
                last = n
                t1 = time.time()
                blk = post(u, "eth_getBlockByNumber", [hex(n), True])
                if blk:
                    full[lb].append(time.time() - t1)
        except Exception as e:
            errors[(lb, type(e).__name__)] += 1
        time.sleep(max(0.0, POLL - (time.time() - t0)))


async def ws_watch(u):
    import websockets
    lb = label(u)
    while time.time() < t_end:
        try:
            async with websockets.connect(u, open_timeout=10, max_size=None) as ws:
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
                while time.time() < t_end:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=10)); now = time.time()
                    r = (m.get("params") or {}).get("result") or {}
                    if "number" in r:
                        seen[lb].setdefault(int(r["number"], 16), now)
        except Exception as e:
            errors[(lb, type(e).__name__)] += 1; await asyncio.sleep(2)


async def feed_watch(u):
    import websockets
    lb = label(u); url = u.replace("feed:", "", 1)
    while time.time() < t_end:
        try:
            async with websockets.connect(url, open_timeout=10, max_size=None, compression="deflate") as ws:
                while time.time() < t_end:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=10)); now = time.time()
                    for x in m.get("messages", []):
                        if x.get("sequenceNumber") is not None:
                            seen[lb].setdefault(int(x["sequenceNumber"]), now)
        except Exception as e:
            errors[(lb, type(e).__name__ + " " + str(e)[:60])] += 1; await asyncio.sleep(5)


def main():
    if not URLS:
        print(__doc__); return
    labels = [label(u) for u in URLS]
    print(f"racing {len(URLS)} sources for {SECONDS:g} s: " + ", ".join(labels), flush=True)
    for u in URLS:
        if u.startswith("http"):
            threading.Thread(target=http_watch, args=(u,), daemon=True).start()

    async def run_ws():
        await asyncio.gather(*[(feed_watch(u) if u.startswith("feed:") else ws_watch(u)) for u in URLS if not u.startswith("http")], return_exceptions=True)
    if any(not u.startswith("http") for u in URLS):
        threading.Thread(target=lambda: asyncio.run(run_ws()), daemon=True).start()
    time.sleep(SECONDS + 1)
    blocks = sorted(set().union(*[set(v) for v in seen.values()])) if seen else []
    blocks = blocks[5:-5]                                                           # the edges: some sources not yet started or already stopped
    first = {b: min(v[b] for v in seen.values() if b in v) for b in blocks}
    print(f"\n{len(blocks)} blocks compared. Behind = after the first source to show the block; the engine sees a block at behind + full block.")
    print(f"{'source':48s} {'blocks':>7s} {'behind median':>14s} {'p90':>8s} {'full block':>11s} {'first':>7s}")
    rows = []
    for lb in labels:
        d = [1000 * (seen[lb][b] - first[b]) for b in blocks if b in seen[lb]]
        f = 1000 * st.median(full[lb]) if full[lb] else None
        wins = sum(1 for b in blocks if b in seen[lb] and seen[lb][b] == first[b])
        rows.append((st.median(d) + (f or 0) if d else 1e9, lb, len(d), d, f, wins))
    for _, lb, n, d, f, wins in sorted(rows):
        if d:
            print(f"{lb:48s} {n / len(blocks):7.0%} {st.median(d):11.0f} ms {sorted(d)[9 * len(d) // 10]:5.0f} ms {(f'{f:.0f} ms' if f is not None else '-'):>11s} {wins / len(blocks):7.0%}")
        else:
            print(f"{lb:48s}   none")
    for (lb, e), n in errors.most_common(8):
        print(f"  errors: {lb}: {e} x{n}")


if __name__ == "__main__":
    main()
