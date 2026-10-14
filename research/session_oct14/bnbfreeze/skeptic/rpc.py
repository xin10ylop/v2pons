"""skeptic: minimal read-only JSON-RPC (eth_call / eth_simulateV1 / reads only). No key, no transaction."""
import json, time, urllib.request
from eth_hash.auto import keccak
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (read-only research)"}
URLS = {"pn": "https://bsc-rpc.publicnode.com", "ds": "https://bsc-dataseed.bnbchain.org", "df": "https://bsc-dataseed1.defibit.io",
        "se": "https://bsc.rpc.sentio.xyz", "bm": "https://rpc-bsc.blockmachine.io", "pk": "https://bsc.api.pocket.network"}
def raw(method, params, ep="pn", timeout=60):
    req = urllib.request.Request(URLS[ep], json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), H)
    for i in range(4):
        try: return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception as e: err = str(e)[:200]; time.sleep(0.5 * 2 ** i)
    return {"error": {"message": "transport: " + err}}
def k(b): return keccak(b)
def pad(x): return (x if isinstance(x, int) else int(x, 16)).to_bytes(32, "big")
def mslot(key, slot): return "0x" + k(pad(key) + pad(slot)).hex()
def mslot2(a, b, slot):   # mapping(a => mapping(b => v)) at slot
    return "0x" + k(pad(b) + k(pad(a) + pad(slot))).hex()
def hx(i): return "0x%064x" % i
