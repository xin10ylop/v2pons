"""stream pools.jsonl once; keep v4 non-quote-pair rows with the fields the grid needs -> v4rows.pkl"""
from common import *
KEEP = ["pool", "token", "quote", "quote_side", "fee", "tick_spacing", "hooks", "sqrt_p0", "tick0", "launch_block", "launch_ts", "launch_utc",
        "launch_tx", "known_fp", "n_swaps", "n_buys", "buy_eth_total", "n_adds", "liq_off", "liq_in_launch_tx", "pulls", "n_pulls", "first_pull_off",
        "first_pull_full", "pull_by_launch_wallet", "swaps12", "first_buys", "first_real_buys", "frb", "outsider12", "pull_after_last_buy12", "ours", "fam"]
rows = []
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if not line.startswith('{"dex":"v4"'): continue
        r = json.loads(line)
        if r["dex"] != "v4" or r.get("quote_pair"): continue
        x = {k: r.get(k) for k in KEEP}
        l = r["launch"]
        x["launch"] = {k: l.get(k) for k in ("from", "to", "nonce", "value_wei", "selector", "calldata_len", "created_contract", "target", "target_code_hash", "n_pools_in_tx", "max_prio")}
        x["tok_size"] = (r.get("token_code") or {}).get("size")
        rows.append(x)
pickle.dump(rows, open(os.path.join(G, "v4rows.pkl"), "wb"))
print(len(rows), "v4 rows", C.Counter(r["quote"] for r in rows))
