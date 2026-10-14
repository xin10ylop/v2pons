"""shared loaders for the bnbfreeze/data study"""
import json, os, collections
D = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(D, "cache")
ROUTER = "0x10ed43c718714eb63d5aa57b78b54704e256024e"; WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
LAUNCHER = "0xc9b7cc619200418649f9e3fc718e45028dfe9c47"; US = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"
DEAD = {"0x000000000000000000000000000000000000dead", "0x0000000000000000000000000000000000000000"}
SEL = {"7ff36ab5": "swapExactETHForTokens", "b6f9de95": "swapExactETHForTokensSupportingFOT", "fb3bdb41": "swapETHForExactTokens",
       "18cbafe5": "swapExactTokensForETH", "791ac947": "swapExactTokensForETHSupportingFOT", "4a25d94a": "swapTokensForExactETH",
       "38ed1739": "swapExactTokensForTokens", "5c11d795": "swapExactTokensForTokensSupportingFOT", "a9059cbb": "transfer", "23b872dd": "transferFrom"}
def launches():
    return json.load(open(os.path.join(D, "d01_launches.json")))["launches"]
def transfers():
    return [json.loads(l) for l in open(os.path.join(CACHE, "d02_transfers_cache.jsonl"))]
def pairlogs():
    return [json.loads(l) for l in open(os.path.join(CACHE, "d02_pairlogs_cache.jsonl"))]
def txs():
    t = {}
    fn = os.path.join(CACHE, "d03_txs_cache.jsonl")
    if os.path.exists(fn):
        for l in open(fn): t.update(json.loads(l))
    return t
def amount_out(a, ri, ro):
    if a <= 0 or ri <= 0 or ro <= 0: return 0
    x = a * 9975; return x * ro // (ri * 10000 + x)
