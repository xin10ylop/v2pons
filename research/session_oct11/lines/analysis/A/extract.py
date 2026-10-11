"""Stream pools.jsonl once; keep every pool of launcher family lc:c873e135|ac9650d8 (PositionManager multicall), decode the launch
calldata (initializePool + MINT_POSITION: tickLower, tickUpper, liquidity) from cache/tx_launch.jsonl. Output: A/lc_rows.jsonl"""
import json, os, sys
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
OUT = os.path.dirname(os.path.abspath(__file__))
LC = "c873e135dc9aaec88489cfbad146b4cb49d6a32e0d80326377784b7ba17670b2|ac9650d8"
SEL_INIT_POOL = "f7020405"; SEL_MODLIQ = "dd46508f"


def _u(b, at): return int.from_bytes(b[at:at + 32], "big")
def _s(b, at):
    v = _u(b, at); return v - (1 << 256) if v >= 1 << 255 else v
def _dyn(b, base, at):
    st = base + _u(b, at); ln = _u(b, st)
    if st + 32 + ln > len(b): raise ValueError
    return st + 32, ln


def decode(data):
    """same logic as src/flip_engine.decode_launch (copied; read-only repo). Returns all mints found too."""
    b = bytes(data)
    try:
        if len(b) < 68 or b[:4].hex() != "ac9650d8": return None
        arr = 4 + _u(b, 4); n = _u(b, arr)
        if not 0 < n <= 8: return None
        key = sqrt_p = None; mints = []; inner = []; actions_hex = None
        for i in range(n):
            st, ln = _dyn(b, arr + 32, arr + 32 + 32 * i); sel = b[st:st + 4].hex(); inner.append(sel)
            if sel == SEL_INIT_POOL and ln >= 196 and key is None:
                k = st + 4; key = b[k:k + 160]; sqrt_p = _u(b, k + 160)
            elif sel == SEL_MODLIQ:
                a = st + 4; ust, _ = _dyn(b, a, a); ast, aln = _dyn(b, ust, ust); actions = b[ast:ast + aln]; actions_hex = actions.hex()
                parr = ust + _u(b, ust + 32); pn = _u(b, parr)
                for j in range(min(pn, len(actions))):
                    pst, pln = _dyn(b, parr + 32, parr + 32 + 32 * j)
                    if actions[j] == 0x02 and pln >= 384:
                        mints.append({"lo": _s(b, pst + 160), "hi": _s(b, pst + 192), "liq": _u(b, pst + 224),
                                      "a0max": _u(b, pst + 256), "a1max": _u(b, pst + 288), "same_key": b[pst:pst + 160] == key})
        r = {"inner": inner, "actions": actions_hex, "n_mints": len(mints)}
        if key is not None:
            r.update({"c0": key[12:32].hex(), "c1": key[44:64].hex(), "fee": _u(key, 64), "ts": _s(key, 96), "hooks": key[140:160].hex(), "sqrt_p": sqrt_p})
        if mints:
            m = mints[0]; r.update({"lo": m["lo"], "hi": m["hi"], "mint_liq": m["liq"], "a0max": m["a0max"], "a1max": m["a1max"], "mint_same_key": m["same_key"]})
        return r
    except Exception:
        return {"err": 1}


rows = []
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if LC not in line: continue
        r = json.loads(line)
        if (r.get("fam") or {}).get("lc") == LC: rows.append(r)
print("rows", len(rows))
need = {r["launch_tx"] for r in rows}; tx = {}
with open(os.path.join(CEN, "cache", "tx_launch.jsonl")) as f:
    for line in f:
        x = json.loads(line)
        if x["hash"] in need: tx[x["hash"]] = x
print("launch txs found", len(tx), "of", len(need))
nd = 0
with open(os.path.join(OUT, "lc_rows.jsonl"), "w") as g:
    for r in rows:
        x = tx.get(r["launch_tx"]); d = None
        if x and x.get("input"):
            d = decode(bytes.fromhex(x["input"][2:]))
        if d and "mint_liq" in d: nd += 1
        r["dec"] = d
        g.write(json.dumps(r) + "\n")
print("decoded with mint", nd)
