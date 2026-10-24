#!/usr/bin/env python3
"""pumplib.py: shared helpers for the pump.fun / PumpSwap / Meteora scripts (read-only; HELIUS_API_KEY in the environment).

- rpc(): census_fast's shared adaptive limiter (one gap for every thread, grows on a 429), always allowing version-1 transactions.
- gtfa(): Helius's getTransactionsForAddress (full transactions, ascending or descending, blockTime filters, paginationToken),
  100 transactions a call; one call returns a wallet's oldest transaction (its funder) or a bonding curve's first 100 trades.
- keys(), ixs(): a raw 'json'-encoded transaction's account keys (static + address-table) and its instructions in execution order
  (each top-level instruction, then its inner instructions), program id and account addresses resolved.
- pump_events(): pump.fun's anchor event-CPI records (CreateEvent, TradeEvent, CompleteEvent) decoded from the inner instructions.
  CreateEvent's mayhem flag marks a Mayhem-mode launch: pump.fun's agent (MAYHEM_AGENT) buys and sells it, fee-free.
- system_transfers(): SOL moved by System Program transfers (top-level and inner).
- Curve math: buy(vS, vT, sol_net) -> tokens; sell(vS, vT, tokens) -> gross SOL. Constant product on the virtual reserves; the
  protocol and creator fees are charged on top of a buy's SOL and taken out of a sell's SOL (rates read from the TradeEvents)."""
import json, os, sys, time, struct, hashlib, collections, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_fast as CF

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_MINT_AUTH = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
PUMPSWAP = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
DAMM2 = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
SYSTEM = "11111111111111111111111111111111"
MAYHEM_AGENT = "BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s"          # trades only Mayhem-mode launches, fee 0 (verified on 60 launches)
WSOL = "So11111111111111111111111111111111111111112"
JITO_TIP = {"96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
            "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
            "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
            "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"}
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58I = {c: i for i, c in enumerate(B58)}
EV_TAG = bytes.fromhex("e445a52e51cb9a1d")
disc = lambda kind, name: hashlib.sha256(f"{kind}:{name}".encode()).digest()[:8]
D_TRADE, D_CREATE, D_COMPLETE = disc("event", "TradeEvent"), disc("event", "CreateEvent"), disc("event", "CompleteEvent")
STATS = CF.STATS


def b58d(s):
    n = 0
    for ch in s:
        n = n * 58 + _B58I[ch]
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def b58e(b):
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\x00"))) + s


def rpc(m, p):
    return CF.rpc(m, p)


def gtfa(addr, gte=None, lte=None, asc=True, limit=100, max_pages=1, details="full", status="succeeded", lt=None):
    """getTransactionsForAddress pages; returns (txs, complete). details='full' gives raw json transactions (100 max a call),
    'signatures' gives signature rows (1000 max a call)."""
    flt = {}
    bt = {}
    if gte is not None:
        bt["gte"] = int(gte)
    if lte is not None:
        bt["lte"] = int(lte)
    if lt is not None:
        bt["lt"] = int(lt)
    if bt:
        flt["blockTime"] = bt
    if status:
        flt["status"] = status
    out, tok = [], None
    for _ in range(max_pages):
        cfg = {"transactionDetails": details, "sortOrder": "asc" if asc else "desc", "limit": limit, "filters": flt}
        if details == "full":
            cfg.update({"encoding": "json", "maxSupportedTransactionVersion": 1})
        if tok:
            cfg["paginationToken"] = tok
        r = rpc("getTransactionsForAddress", [addr, cfg])
        out += r.get("data") or []
        tok = r.get("paginationToken")
        if not tok or not r.get("data"):
            return out, True
    return out, False


def keys(tx):
    m = tx["transaction"]["message"]
    ks = [k if isinstance(k, str) else k["pubkey"] for k in m["accountKeys"]]
    la = (tx.get("meta") or {}).get("loadedAddresses") or {}
    return ks + list(la.get("writable") or []) + list(la.get("readonly") or [])


def ixs(tx, ks=None):
    """[(top_index, depth, program, [accounts], data_bytes)] in execution order"""
    ks = ks or keys(tx)
    m = tx["transaction"]["message"]
    inner = {g["index"]: g["instructions"] for g in (tx.get("meta") or {}).get("innerInstructions") or []}
    out = []
    for i, ix in enumerate(m["instructions"]):
        out.append((i, 1, ks[ix["programIdIndex"]], [ks[a] for a in ix["accounts"]], ix["data"]))
        for j in inner.get(i, []):
            out.append((i, j.get("stackHeight") or 2, ks[j["programIdIndex"]], [ks[a] for a in j["accounts"]], j["data"]))
    return out


class _R:
    def __init__(self, b):
        self.b, self.o = b, 0

    def pk(self):
        v = b58e(self.b[self.o:self.o + 32]); self.o += 32; return v

    def u64(self):
        v = struct.unpack_from("<Q", self.b, self.o)[0]; self.o += 8; return v

    def i64(self):
        v = struct.unpack_from("<q", self.b, self.o)[0]; self.o += 8; return v

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v

    def s(self):
        L = struct.unpack_from("<I", self.b, self.o)[0]; v = self.b[self.o + 4:self.o + 4 + L]; self.o += 4 + L
        return v.decode("utf-8", "replace")


def decode_event(raw):
    """raw: an event-CPI instruction's bytes (tag + discriminator + body) -> dict or None"""
    if raw[:8] != EV_TAG:
        return None
    d, r = raw[8:16], _R(raw[16:])
    try:
        if d == D_TRADE:
            e = {"ev": "trade", "mint": r.pk(), "sol": r.u64(), "tok": r.u64(), "buy": bool(r.u8()), "user": r.pk(), "ts": r.i64(),
                 "vS": r.u64(), "vT": r.u64(), "rS": r.u64(), "rT": r.u64(), "fee_rec": r.pk(), "fee_bps": r.u64(), "fee": r.u64(),
                 "creator": r.pk(), "cfee_bps": r.u64(), "cfee": r.u64()}
            try:
                r.u8(); r.u64(); r.u64(); r.u64(); r.i64(); e["ix"] = r.s()
            except Exception:
                pass
            return e
        if d == D_CREATE:
            e = {"ev": "create", "name": r.s()[:40], "symbol": r.s()[:20], "uri": r.s()[:200], "mint": r.pk(), "curve": r.pk(), "user": r.pk()}
            try:
                e["creator"] = r.pk(); e["ts"] = r.i64(); e["vT"] = r.u64(); e["vS"] = r.u64(); e["rT"] = r.u64(); e["supply"] = r.u64()
                e["token_program"] = r.pk(); e["mayhem"] = bool(r.u8())      # Mayhem mode: pump.fun's agent trades the token (fee-free)
            except Exception:
                pass
            return e
        if d == D_COMPLETE:
            return {"ev": "complete", "user": r.pk(), "mint": r.pk(), "curve": r.pk()}
    except Exception:
        return None
    return None


def pump_events(tx, ks=None):
    out = []
    for top, depth, prog, accs, data in ixs(tx, ks):
        if prog != PUMP or depth < 2:
            continue
        raw = b58d(data)
        if raw[:8] == EV_TAG:
            e = decode_event(raw)
            if e:
                out.append(e)
    return out


def system_transfers(tx, ks=None):
    """[(from, to, lamports)] for System Program transfer instructions (index 2), top-level and inner"""
    out = []
    for top, depth, prog, accs, data in ixs(tx, ks):
        if prog != SYSTEM or len(accs) < 2:
            continue
        raw = b58d(data)
        if len(raw) >= 12 and struct.unpack_from("<I", raw, 0)[0] == 2:
            out.append((accs[0], accs[1], struct.unpack_from("<Q", raw, 4)[0]))
    return out


def tip(tx, ks=None):
    return sum(l for f, t, l in system_transfers(tx, ks) if t in JITO_TIP)


# ---------------------------------------------------------------- curve math (lamports / raw token units)

def buy_tokens(vS, vT, sol_net):
    return vT * sol_net // (vS + sol_net)


def sell_sol(vS, vT, tok):
    return vS * tok // (vT + tok)


# ---------------------------------------------------------------- small io helpers

def jload(path, default=None):
    try:
        return json.load(open(path))
    except Exception:
        return default


def jsave(path, obj):
    tmp = path + ".tmp"; json.dump(obj, open(tmp, "w")); os.replace(tmp, path)
