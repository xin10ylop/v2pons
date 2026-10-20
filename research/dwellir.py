"""The research key for Dwellir's Robinhood Chain archive RPC (the owner's research key, kept outside the repository in
/root/.config/v2pons/dwellir_research_key; never the engine's key). Dwellir caps eth_getLogs at 500 blocks on this plan, so log scans
stay on the public node; transactions, receipts, blocks, eth_call and historical state go here. One shared pace across every research
process (a lock file): at most RATE posts a second in total, batches of at most BATCH items, so research cannot crowd the plan the
live engine also uses. Set RESEARCH_PUBLIC_ONLY=1 to switch it off."""
import fcntl, json, os, time, urllib.error, urllib.request
KEY_FILE = "/root/.config/v2pons/dwellir_research_key"
PACE_FILE = "/tmp/v2pons_dwellir.pace"
RATE = 8.0; BATCH = 25
H = {"Content-Type": "application/json", "User-Agent": "v2pons-research"}
URL = None
if os.environ.get("RESEARCH_PUBLIC_ONLY") != "1" and os.path.exists(KEY_FILE):
    URL = "https://api-robinhood-mainnet-archive.n.dwellir.com/" + open(KEY_FILE).read().strip()
def _pace():
    with open(PACE_FILE, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.seek(0)
        try: last = float(f.read() or 0)
        except ValueError: last = 0.0
        wait = last + 1.0 / RATE - time.time()
        if wait > 0: time.sleep(wait)
        f.seek(0); f.truncate(); f.write(repr(time.time())); f.flush()
def post(body):
    """POST to Dwellir with the shared pace; None when it cannot answer (the caller falls back to the public node)"""
    if not URL: return None
    for i in range(4):
        _pace()
        try: return json.load(urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), H), timeout=60))
        except urllib.error.HTTPError as e: time.sleep(2 * (i + 1) if e.code == 429 else 1)
        except Exception: time.sleep(1 + i)
    return None
