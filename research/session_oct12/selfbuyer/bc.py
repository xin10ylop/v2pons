"""selfbuyer common: the V3 self-buying launcher lc:0a493d1a|13ead562 (REPORT_S line), Oct 12 evening re-check.
Read-only, public RPC only, through research/session_oct12/c1/rpc.py (one POST at a time, >= 0.5 s apart, back-off on 429; read methods
only); its call log is redirected to this directory. Raw caches are *_cache.jsonl (git-ignored), rotated below 1.8 MB per file.
Records follow REPORT_S's scommon.load(): events in analyst C's compact format (W/wcommon.compact) for C/replay.py's V3Sim."""
import os, sys, json, glob, time, importlib.util
OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/W")
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/S")
from wcommon import compact, T_SW, T_MI, T_BU
from eth_utils import keccak
_spec = importlib.util.spec_from_file_location("c1rpc", "/home/user/v2pons/research/session_oct12/c1/rpc.py")
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R); R.LOG = os.path.join(OUT, "rpc_log.jsonl")

FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"; SR02 = "0xcaf681a66d020601342297493863e78c959e5cb2"
DEAD = "0x000000000000000000000000000000000000dead"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
def p(n): return os.path.join(OUT, n)
def ts(t): return time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
def pad(a): return "0x" + "0" * 24 + a[2:].lower()


class Cache:
    """append-only key -> value store over <name>_pNN_cache.jsonl files, each kept under 1.8 MB"""
    def __init__(self, name):
        self.name = name; self.d = {}
        for f in sorted(glob.glob(p(f"{name}_p*_cache.jsonl"))):
            for line in open(f):
                if line.strip():
                    k, v = json.loads(line); self.d[k] = v
        self.part = len(glob.glob(p(f"{name}_p*_cache.jsonl")))
        if self.part == 0: self.part = 1
    def _file(self):
        f = p(f"{self.name}_p{self.part - 1:02d}_cache.jsonl")
        if os.path.exists(f) and os.path.getsize(f) > 1_800_000:
            self.part += 1; f = p(f"{self.name}_p{self.part - 1:02d}_cache.jsonl")
        return f
    def put(self, k, v):
        self.d[k] = v
        with open(self._file(), "a") as fh: fh.write(json.dumps([k, v], separators=(",", ":")) + "\n")
    def __contains__(self, k): return k in self.d
    def __getitem__(self, k): return self.d[k]
    def get(self, k, dflt=None): return self.d.get(k, dflt)


def slim_tx(t):
    if t is None: return None
    return {"hash": t["hash"], "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "input": t["input"], "value": t["value"],
            "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "type": t.get("type")}


def txs(cache, hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in cache]
    for i in range(0, len(need), 100):
        chunk = need[i:i + 100]
        res = R.batch("eth_getTransactionByHash", [[h] for h in chunk], n=20)
        for h, t in zip(chunk, res): cache.put(h, slim_tx(t))
    return {h: cache.get(h) for h in hashes}


def block_ts(cache, blocks):
    need = sorted({b for b in blocks if str(b) not in cache})
    for i in range(0, len(need), 100):
        chunk = need[i:i + 100]
        res = R.batch("eth_getBlockByNumber", [[hex(b), False] for b in chunk], n=20)
        for b, x in zip(chunk, res): cache.put(str(b), int(x["timestamp"], 16))
    return {b: cache.get(str(b)) for b in blocks}


def words(h, o=0): return [h[o + 64 * i: o + 64 * (i + 1)] for i in range((len(h) - o) // 64)]
def decode_buy(t):
    """the swap call: to, selector, length, value, and for SwapRouter02 exactInputSingle 04e45aaf (also inside a multicall) amountIn/minOut/recipient"""
    inp = t["input"][2:]; sel = inp[:8]
    r = {"to": t["to"], "sel": sel, "len": len(inp) // 2, "value": int(t["value"], 16) / 1e18, "amount_in": None, "min_out": None, "recipient": None}
    def eis(h):
        w = words(h); r["amount_in"] = int(w[4], 16); r["min_out"] = int(w[5], 16); r["recipient"] = "0x" + w[3][-40:]
    if sel == "04e45aaf": eis(inp[8:])
    elif sel in ("ac9650d8", "5ae401dc", "1f0464d1"):
        b = bytes.fromhex(inp[8:]); base = 32 if sel == "5ae401dc" else 0
        try:
            arr = int.from_bytes(b[base:base + 32], "big"); n = int.from_bytes(b[arr:arr + 32], "big")
            for i in range(n):
                st = arr + 32 + int.from_bytes(b[arr + 32 + 32 * i: arr + 64 + 32 * i], "big"); ln = int.from_bytes(b[st:st + 32], "big")
                c = b[st + 32: st + 32 + ln].hex()
                if c[:8] == "04e45aaf": eis(c[8:])
        except Exception: pass
    return r
LINE_RANGES = ((-887272, 204200), (-204200, 887272))
def build(x, ev, ev_to, TXd, tr=None):
    """one launch record from its compact events (x = a b01-style launch dict)"""
    lb = x["lb"]; qs = x["qs"]; lw = x["launch_from"].lower()
    mints, swaps, burns = [], [], []
    for e in ev:
        t = TXd.get(e[-1]); frm = t["from"] if t else None
        if e[0] == "mi":
            mints.append({"off": e[1] - lb, "lo": e[6], "hi": e[7], "L": e[8], "a0": e[9], "a1": e[10], "from": frm, "by_lw": frm == lw,
                          "to": t["to"] if t else None, "sel": t["input"][2:10] if t else None, "len": (len(t["input"]) - 2) // 2 if t else None, "e": e})
        elif e[0] == "b":
            burns.append({"off": e[1] - lb, "L": e[8], "from": frm, "by_lw": frm == lw, "sel": t["input"][2:10] if t else None, "e": e})
        elif e[0] == "s":
            dq = e[7] if qs == 0 else e[8]; dt = e[8] if qs == 0 else e[7]
            d = {"off": e[1] - lb, "ti": e[2], "li": e[3], "dir": "B" if dq > 0 else "S", "eth": abs(dq) / 1e18, "tok": abs(dt), "from": frm,
                 "by_lw": frm == lw, "e": e, "known": t is not None}
            if t: d.update(decode_buy(t)); d["type"] = t.get("type")
            swaps.append(d)
    own = [s for s in swaps if s["by_lw"] and s["dir"] == "B"]
    pulls = [b for b in burns if b["L"] > 0]
    m0 = mints[0] if mints else None
    r = {"pool": x["pool"], "lb": lb, "ts": x.get("ts"), "fee": x["fee"], "qs": qs, "lw": lw, "nonce": x["launch_nonce"], "ev_to": ev_to, "ev": ev,
         "mints": mints, "swaps": swaps, "burns": burns, "own": own, "own1": own[0] if own else None, "pull1": pulls[0] if pulls else None,
         "token": x["token"], "tr": tr or []}
    r["line"] = (r["fee"] == 100 and m0 is not None and m0["by_lw"] and (m0["lo"], m0["hi"]) in LINE_RANGES)
    dead = [t for t in r["tr"] if t[1] == DEAD]
    r["dead_off"] = dead[0][0] - lb if dead else None
    o = r["own1"]
    r["pre"] = [s for s in swaps if s["dir"] == "B" and not s["by_lw"] and (o is None or (s["e"][1], s["e"][3]) < (o["e"][1], o["e"][3]))]
    return r
def load(extra=False):
    """-> (meta, records) for the b01 launches (and, extra=True, the census pools of b06 too), newest last"""
    D = json.load(open(p("b01_launches.json"))); EV = Cache("b02_ev"); TX = Cache("b02_tx"); TR = Cache("b02_tr")
    L = [x for x in D["launches"] if x["qs"] is not None]
    if extra and os.path.exists(p("b06_census_pools.json")):
        L = json.load(open(p("b06_census_pools.json"))) + L
    recs = []
    for x in L:
        if x["pool"] not in EV.d: continue
        E = EV[x["pool"]]
        recs.append(build(x, E["ev"], E["ev_to"], TX.d, TR.get(x["pool"])))
    recs.sort(key=lambda r: (r["lb"], r["pool"]))
    return D["meta"], recs
