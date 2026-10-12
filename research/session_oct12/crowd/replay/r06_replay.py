"""The v3crowd rule replayed on every launch of r01 with exact V3 integer math (v3exact, validated on 14,832 of 14,832 live swaps):
our buy of q ETH lands at the head of block launch + e (e = 1, 2, 3); the exit's clock starts at the first buy the engine would count as
real (the crowd's call shapes with an amount word of >= 0.005 ETH, or anyone's call carrying the token with >= 0.005 ETH as its value) in a
block >= our buy's; the sell is sent when the feed shows that buy + 18, at the latest launch + 78, and lands 1 or 2 blocks later (at the head
of that block); every swap between is re-simulated by its input amount (our impact on everyone after us), Mints and Burns applied; the
first Burn of liquidity > 0 at or before the sell's block = -100% (and the sell burns its 500k gas limit on the empty range).
Gas (the V3 relay path, docs/RELAY_V3.md, HANDOFF 16.22): buy 260k + sell 175k at the window's base fee (r05). Also, per launch: the crowd's
first real buy, every other buyer before it, the first Burn and who sent it, and the engine's own dry pricing (send_sell/our_buy_landed/
apply_buy of src/flip_engine.py, mimicked with src/v4math.py) for comparison with the box. Writes r06_rows.json, r06_replay.out (stdout)."""
from common import *
import collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from v3exact import Pool, sqrt_at_tick
X = json.load(open(J("r01_launches.json"))); ev = jl(J("r02_events_cache.jsonl")); R2 = json.load(open(J("r02_meta.json")))
TX = {t["hash"]: t for t in jl(J("r03_txs_cache.jsonl"))}; GP = json.load(open(J("r05_gas_price.json")))
BASE_FEE = int(st.median(b[2] for b in GP["base_fee"])); ETH_USD = [p for p in GP["eth_usd_pools"] if p["fee"] == 100 and p["sym"] == "USDG"][0]["eth_usd"]
GAS_BUY, GAS_SELL, GAS_SELL_PULLED = 260_000, 175_000, 500_000
MIN = 5 * 10 ** 15; K = 18; CAP = 78; FEE = 100
by = collections.defaultdict(list)
for e in ev: by[e["a"]].append(e)
WETH_FEE = WETH[2:] + "000064"

def parse(x):
    """the pool's events, compact, with each swap's engine view"""
    out = []; tok = x["token"][2:]
    for e in by[x["pool"]]:
        k = e["t"][0]; r = {"bn": e["bn"], "li": e["li"], "ti": e["ti"], "tx": e["tx"]}
        if k == T_SW:
            r.update(k="s", a0=sgn(W(e["d"], 0)), a1=sgn(W(e["d"], 1)), sp=W(e["d"], 2), L=W(e["d"], 3), tick=sgn(W(e["d"], 4)))
            t = TX.get(e["tx"]); r["t"] = t; r["eng"] = None; r["crowd"] = False
            if t is not None and r["a0"] > 0:
                vw = CROWD_SHAPES.get((t["sel"], t["n"]))
                if vw is not None and t["value"] == 0 and (WETH_FEE + tok) in t["input"]:
                    r["crowd"] = True; r["eng"] = int(t["input"][2 + 8 + 64 * vw: 2 + 8 + 64 * (vw + 1)], 16)
                elif t["value"] > 0 and tok in t["input"][10:] and t["to"] != x["token"]:
                    r["eng"] = t["value"]
        elif k == T_MI:
            r.update(k="mi", owner="0x" + e["t"][1][-40:], lo=sgn(int(e["t"][2], 16)), hi=sgn(int(e["t"][3], 16)), amt=W(e["d"], 1))
        else:
            r.update(k="b", owner="0x" + e["t"][1][-40:], lo=sgn(int(e["t"][2], 16)), hi=sgn(int(e["t"][3], 16)), amt=W(e["d"], 0))
        out.append(r)
    out.sort(key=lambda r: (r["bn"], r["li"])); return out

def apply(pool, r):
    if r["k"] == "s":
        if r["a0"] > 0: pool.swap(True, r["a0"])
        elif r["a1"] > 0: pool.swap(False, r["a1"])
    elif r["k"] == "mi": pool.modify(r["owner"], r["lo"], r["hi"], r["amt"])
    elif r["amt"] > 0: pool.modify(r["owner"], r["lo"], r["hi"], -r["amt"])

def replay(x, es, e, q, d, tail=False):
    lb = x["lb"]; buy_blk = lb + e
    pool = Pool(x["sqrt_p"]); i = 0
    pre = (lambda r: r["bn"] <= buy_blk) if tail else (lambda r: r["bn"] < buy_blk)
    while i < len(es) and pre(es[i]):
        apply(pool, es[i]); i += 1
    s_entry = pool.sp
    pull = next((r["bn"] for r in es if r["k"] == "b" and r["amt"] > 0), None)
    if pull is not None and pull < buy_blk + (1 if tail else 0):
        return {"ret": -GAS_BUY * BASE_FEE / q, "gross": 0.0, "pulled_before_buy": True, "pulled": False}
    a0, a1 = pool.swap(True, q); tok = -a1
    trig = next((r for r in es if r["k"] == "s" and r.get("eng") is not None and r["eng"] >= MIN and r["a0"] > 0 and (r["bn"] > buy_blk if tail else r["bn"] >= buy_blk)), None)
    send = min(trig["bn"] + K, lb + CAP) if trig else lb + CAP
    land = send + d
    pulled = pull is not None and pull <= land
    chain = Pool(x["sqrt_p"])          # the chain's own price at the sell (no us): the price move
    while i < len(es) and es[i]["bn"] < land:
        apply(pool, es[i]); i += 1
    s_exit = None
    for r in es:
        if r["bn"] >= land: break
        if r["k"] == "s": s_exit = r["sp"]
    s_exit = s_exit or x["sqrt_p"]
    o0, o1 = pool.swap(False, tok); out = -o0
    gross = -1.0 if pulled else (out - q) / q
    gas = (GAS_BUY + (GAS_SELL_PULLED if pulled else GAS_SELL)) * BASE_FEE
    return {"ret": gross - gas / q, "gross": gross, "gross_unpulled": (out - q) / q, "pulled": pulled, "pulled_before_buy": False, "tok": tok,
            "trig_off": trig["bn"] - lb if trig else None, "trig_eth": trig["eng"] / 1e18 if trig else None, "send_off": send - lb, "land_off": land - lb,
            "move": (s_entry / s_exit) ** 2 - 1, "cap": trig is None or trig["bn"] + K > lb + CAP}

def engine_dry(x, es, q, base_fee=BASE_FEE):
    """the engine's dry_ret for a v3crowd trade (fire in the launch block, plan_buy_seq = launch + 2): the price copy from the launch's
    sqrtP and L moved by apply_buy for each buy the feed shows (crowd-shaped calls: the amount word; ETH-value calls carrying the token:
    the value), sells and other value-0 buys unseen; feed_tokens at the head of launch + 2; the exit's clock at the first of >= min_eth at or
    after our buy (+ 18), the cap at launch + 78 (buy_seq + send_after); take_profit 9 (900%); dry_ret at the sell's send block, our buy put
    on top of the copy, less base_fee x 250k; pulls never counted (settle_dry has no pull check for a crowd family)"""
    lb = x["lb"]; sp = float(x["sqrt_p"]); liq = x["liq"]; feed = None; exit_seq = None
    nf = lambda v: v - (v * FEE + 999_999) // 1_000_000
    def price():
        s2 = v4math.sqrt_after_buy(sp, liq, nf(q))
        return (v4math.sell_out_int(int(s2), liq, feed, FEE) - q - base_fee * 250_000) / q
    blocks = sorted(set(r["bn"] for r in es if lb <= r["bn"] <= lb + CAP) | {lb + 2, lb + CAP})
    for b in range(lb, lb + CAP + 1):
        if b == lb + 2: feed = v4math.buy_out_int(int(sp), liq, q, FEE)
        for r in es:
            if r["bn"] != b or r["k"] != "s" or r.get("eng") is None: continue
            sp = v4math.sqrt_after_buy(sp, liq, nf(r["eng"]))
            if r["eng"] >= MIN and feed is not None and exit_seq is None and b >= lb + 2: exit_seq = b + K
            if feed is not None and b >= lb + 2:
                pr = price()
                if pr >= 9.0: return {"dry": pr, "send_off": b - lb, "why": "tp"}
        if feed is not None and exit_seq is not None and b >= exit_seq: return {"dry": price(), "send_off": b - lb, "why": "crowd"}
        if feed is not None and b >= lb + CAP: return {"dry": price(), "send_off": b - lb, "why": "cap"}

STAKES = [0.0012, 0.0020, 0.0036, 0.0040, 0.0058, 0.0060]
rows = []; skipped = []
for x in sorted(X, key=lambda x: x["lb"]):
    elig = x["qs"] == 0 and x["lo"] == -887272 and x["amount0"] == 0 and x["sqrt_p"] == sqrt_at_tick(x["hi"])
    if not elig: skipped.append({"pool": x["pool"], "utc": utc(x["ts"]), "qs": x["qs"], "lo": x["lo"], "hi": x["hi"]}); continue
    if x["lb"] + CAP + 5 > R2["head"]: continue
    es = parse(x); lb = x["lb"]
    sw = [r for r in es if r["k"] == "s"]
    crowd1 = next((r for r in sw if r["crowd"] and r["a0"] >= MIN), None)
    eng1 = next((r for r in sw if r.get("eng") is not None and r["eng"] >= MIN and r["a0"] > 0), None)
    any1 = next((r for r in sw if r["a0"] >= MIN), None)
    before = [(r["bn"] - lb, (r["t"] or {}).get("from"), (r["t"] or {}).get("to"), (r["t"] or {}).get("sel"), r["a0"] / 1e18, r["crowd"], r.get("eng") is not None)
              for r in sw if r["a0"] > 0 and (crowd1 is None or (r["bn"], r["li"]) < (crowd1["bn"], crowd1["li"])) and r["bn"] - lb <= 200]
    burn = next((r for r in es if r["k"] == "b" and r["amt"] > 0), None)
    bt = TX.get(burn["tx"]) if burn else None
    row = {"pool": x["pool"], "token": x["token"], "lb": lb, "ts": x["ts"], "utc": utc(x["ts"]), "launch_from": x["from"], "hi": x["hi"], "L": x["liq"],
           "crowd1_off": crowd1["bn"] - lb if crowd1 else None, "crowd1_eth": crowd1["a0"] / 1e18 if crowd1 else None, "crowd1_to": crowd1["t"]["to"] if crowd1 else None,
           "eng1_off": eng1["bn"] - lb if eng1 else None, "eng1_eth": eng1["eng"] / 1e18 if eng1 else None, "any1_off": any1["bn"] - lb if any1 else None,
           "any1_who": (((any1["t"] or {}).get("to") or "?")[:10] + ":" + ((any1["t"] or {}).get("sel") or "?")) if any1 else None,
           "before": before, "burn_off": burn["bn"] - lb if burn else None, "burn_from": bt["from"] if bt else None, "burn_to": bt["to"] if bt else None,
           "burn_sel": bt["sel"] if bt else None, "burn_by_launcher": (bt["from"] == x["from"]) if bt else None, "burn_frac": burn["amt"] / x["liq"] if burn else None,
           "r": {}, "dry": {}}
    for qe in STAKES:
        q = int(round(qe * 1e18))
        for e in (1, 2, 3):
            for d in (1, 2):
                row["r"][f"{qe}|{e}|{d}"] = replay(x, es, e, q, d)
        row["r"][f"{qe}|2|2|tail"] = replay(x, es, 2, q, 2, tail=True)
        row["dry"][str(qe)] = engine_dry(x, es, q)
    rows.append(row)
json.dump({"rows": rows, "skipped": skipped, "base_fee": BASE_FEE, "eth_usd": ETH_USD, "head": R2["head"], "gas": [GAS_BUY, GAS_SELL, GAS_SELL_PULLED], "stakes": STAKES},
          open(J("r06_rows.json"), "w"))
print(f"replayed {len(rows)} launches; skipped (not the engine's shape) {len(skipped)}: {skipped}; base fee {BASE_FEE / 1e9:.4f} gwei; ETH ${ETH_USD:,.0f}")
