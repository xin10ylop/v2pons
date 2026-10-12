"""Skeptic 1, step 5: replay the v3crowd rule on every WETH-token0 launch with my own V3 model (k04_v3.py).
Rule (engine: fire in the launch block, buy lands at + 2; exit clock = the first engine-counted buy at or after our buy's block, sell sent at
that + 18, cap: sent when the feed shows launch + 78; the sell lands LAND blocks after its send):
- our buy (stake Q, exact input WETH) at the head of block lb + 2;
- every later Swap re-simulated by its input amount, Mints/Burns applied by liquidity, until the head of the sell block;
- our sell (all our tokens) at the head of block X = min(T + 18, lb + 78) + LAND;
- a Burn with liquidity > 0 at or before block X: -100% (and the buy's gas plus a 500k-gas failed sell);
- gas: (260k + 175k) x the launch block's base fee, the relay's figures (docs/RELAY_V3.md, HANDOFF 16.22).
Engine-counted buy (src/flip_engine.py trigger_word / on_wave_call / ingest_tx): a value-0 call of a crowd shape (3593564c/484 word 9,
a0193551/452 word 8, 49f74a5d/452 word 8) to any contract, carrying the token as an address word or after WETH+fee in a word-aligned path,
amount word in [0.005, 10] ETH; or an ETH-value call carrying the token with value >= 0.005 ETH.
Also: a validation pass (no trade of ours) of every on-chain Swap in the fetched windows against the logged amounts, price, L and tick."""
import sys, os, json, statistics as st, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from k04_v3 import Pool, tick_at_sqrt
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)"); T_IN = tp("Initialize(uint160,int24)")
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"; WETH_B = bytes.fromhex(WETH[2:])
SHAPES = {("3593564c", 484): 9, ("a0193551", 452): 8, ("49f74a5d", 452): 8}
MIN_W, MAX_W = 5 * 10 ** 15, 10 * 10 ** 18
GAS_RT, GAS_BUY, GAS_FAILED_SELL = 435_000, 260_000, 500_000
def S(h):
    x = int(h, 16); return x - (1 << 256) if x >> 255 else x
def W(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]

D = json.load(open(os.path.join(HERE, "k01_launches.json"))); HEAD, T_HEAD = D["head"], D["t_head"]
LA = {x["pool"]: x for x in D["line"]}
win, burns = {}, []
for line in open(os.path.join(HERE, "k02_events_cache.jsonl")):
    r = json.loads(line)
    if r["kind"] == "win": win[r["pool"]] = r["logs"]
    else: burns = r["logs"]
TX = {}
for line in open(os.path.join(HERE, "k03_txs_cache.jsonl")):
    r = json.loads(line); TX[r["hash"]] = r["tx"]
BURNS = {}
for l in sorted(burns, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
    BURNS.setdefault(l["address"].lower(), []).append(l)


def ev_of(logs):
    out = []
    for l in sorted(logs, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        t, d, bn, h = l["topics"], l["data"], int(l["blockNumber"], 16), l["transactionHash"]
        if t[0] == T_IN: out.append(("in", bn, int(W(d, 0), 16), S(W(d, 1)), h))
        elif t[0] == T_SW: out.append(("sw", bn, S(W(d, 0)), S(W(d, 1)), int(W(d, 2), 16), int(W(d, 3), 16), S(W(d, 4)), h))
        elif t[0] == T_MI: out.append(("mi", bn, S(t[2]), S(t[3]), int(W(d, 1), 16), h))
        elif t[0] == T_BU: out.append(("bu", bn, S(t[2]), S(t[3]), int(W(d, 0), 16), h))
    return out


def counted(h, token):
    """the engine's view of tx h on this pool: the amount it counts (>= min) or None"""
    t = TX.get(h)
    if t is None: return None
    data = bytes.fromhex(t["input"][2:]); val = int(t["value"], 16); to = (t.get("to") or "").lower(); tok = bytes.fromhex(token[2:])
    if val > 0:
        return val if (tok in data and to != token and len(data) >= 20 and val >= MIN_W) else None
    vw = SHAPES.get((data[:4].hex(), len(data)))
    if vw is None: return None
    path = WETH_B + (100).to_bytes(3, "big"); i = data.find(tok); ok = False
    while i >= 0:
        if ((i - 4) % 32 == 12 and data[i - 12:i] == bytes(12)) or ((i - 4) % 32 == 23 and data[i - 23:i] == path): ok = True; break
        i = data.find(tok, i + 1)
    if not ok: return None
    amt = int.from_bytes(data[4 + 32 * vw: 4 + 32 * (vw + 1)], "big")
    return amt if MIN_W <= amt <= MAX_W else None


def build(pool):
    x = LA[pool]; ev = ev_of(win[pool]); ini = [e for e in ev if e[0] == "in"]
    assert ini and ini[0][1] == x["lb"], pool
    return x, ev, ini[0]


VAL = {"swaps": 0, "exact": 0, "out_off": 0, "sp_off": 0, "miss": []}
def validate(pool):
    x, ev, ini = build(pool)
    p = Pool(ini[2], 100)
    assert p.tick == ini[3], (pool, p.tick, ini[3])
    for e in ev:
        if e[0] == "mi": p.modify(e[2], e[3], e[4])
        elif e[0] == "bu": p.modify(e[2], e[3], -e[4])
        elif e[0] == "sw":
            a0, a1, sp, liq, tick = e[2], e[3], e[4], e[5], e[6]
            if a0 <= 0 and a1 <= 0: continue
            zfo = a0 > 0; ain = a0 if zfo else a1; aout = -(a1 if zfo else a0)
            used, out = p.swap(zfo, ain)
            VAL["swaps"] += 1
            if out == aout and p.sp == sp and p.liq == liq and p.tick == tick and used == ain: VAL["exact"] += 1
            else:
                if out != aout: VAL["out_off"] += 1
                if p.sp != sp: VAL["sp_off"] += 1
                if len(VAL["miss"]) < 8: VAL["miss"].append((pool[:10], e[1] - x["lb"], ain, out, aout, p.sp == sp, p.liq == liq, p.tick, tick))
                p.sp, p.liq, p.tick = sp, liq, tick           # re-sync to the chain


def trade(pool, Q, E=2, LAND=2, CAP_SEND=78, K=18):
    x, ev, ini = build(pool); lb = x["lb"]; tok = x["token1"]
    trig = None
    for e in ev:
        if e[0] == "sw" and e[1] >= lb + E and e[2] > 0:
            if counted(e[7], tok) is not None: trig = e[1]; break
    send = min(trig + K, lb + CAP_SEND) if trig is not None else lb + CAP_SEND
    X = send + LAND
    pl = [l for l in BURNS.get(pool, []) if int(l["data"][2:66], 16) > 0]
    pull = int(pl[0]["blockNumber"], 16) if pl else None
    fee_wei = x["basefee"]
    if pull is not None and pull <= X:
        return {"ret": -1 - fee_wei * (GAS_BUY + GAS_FAILED_SELL) / Q, "gross": -1.0, "pulled": True, "trig": None if trig is None else trig - lb, "exit": X - lb}
    p = Pool(ini[2], 100); ours = None
    for e in ev:
        if ours is None and e[1] >= lb + E:
            used, ours = p.swap(True, Q); assert used == Q
        if e[1] >= X: break
        if e[0] == "mi": p.modify(e[2], e[3], e[4])
        elif e[0] == "bu": p.modify(e[2], e[3], -e[4])
        elif e[0] == "sw":
            a0, a1 = e[2], e[3]
            if a0 <= 0 and a1 <= 0: continue
            zfo = a0 > 0; p.swap(zfo, a0 if zfo else a1)
    if ours is None:
        used, ours = p.swap(True, Q)
    assert X <= lb + 120, "window too short"
    _, back = p.swap(False, ours)
    gross = back / Q - 1
    return {"ret": gross - fee_wei * GAS_RT / Q, "gross": gross, "pulled": False, "trig": None if trig is None else trig - lb, "exit": X - lb, "back": back, "tok": ours}


def pull_info(pool):
    x = LA[pool]; pl = [l for l in BURNS.get(pool, []) if int(l["data"][2:66], 16) > 0]
    if not pl: return None
    l = pl[0]; t = TX.get(l["transactionHash"]) or {}
    mint_L = sum(e[4] for e in ev_of(win[pool]) if e[0] == "mi" and e[1] == x["lb"])
    return {"off": int(l["blockNumber"], 16) - x["lb"], "by_launcher": (t.get("from") or "").lower() == x["from"], "to": (t.get("to") or "").lower(),
            "frac": int(l["data"][2:66], 16) / mint_L if mint_L else None}


if __name__ == "__main__":
    pools0 = sorted([p for p, x in LA.items() if x["token0"] == WETH], key=lambda p: LA[p]["lb"])
    pools1 = [p for p, x in LA.items() if x["token0"] != WETH]
    for p in pools0: validate(p)
    print(f"validation (no trade of ours, swaps in [lb, lb+120]): {VAL['exact']}/{VAL['swaps']} exact (amounts, sqrtP, L, tick); out differs {VAL['out_off']}, sqrtP differs {VAL['sp_off']}")
    for m in VAL["miss"]: print("  miss", m)
    rows = []
    for p in pools0:
        x = LA[p]; r = {"pool": p, "lb": x["lb"], "ts": x["ts"], "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(x["ts"])), "basefee": x["basefee"], "pull": pull_info(p)}
        for Q in (0.0012, 0.0058):
            for LAND in (1, 2):
                r[f"{Q}|{LAND}"] = trade(p, int(Q * 1e18), 2, LAND)
        rows.append(r)
    json.dump({"head": HEAD, "t_head": T_HEAD, "rows": rows, "qs1": pools1, "val": {k: v for k, v in VAL.items() if k != "miss"}}, open(os.path.join(HERE, "k05_rows.json"), "w"))
    print(f"replayed {len(rows)} WETH-token0 launches; {len(pools1)} WETH-token1 launches not traded (the engine skips them)")
