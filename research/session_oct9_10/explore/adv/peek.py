import pickle, sys
D = pickle.load(open("adv/cache.pkl", "rb"))
for pid, P in list(D.items())[:20]:
    m = P["meta"]; b0 = m["b0"]; tok = m["token"][2:].lower(); tb = bytes.fromhex(tok)
    print("==", m["src"], pid[:12], b0, "deployer", m["from"][:10], "nonce", m["nonce"])
    for b in P["blocks"]:
        if not b: continue
        n = int(b["number"], 16)
        if n - b0 > 30: break
        for t in b["transactions"]:
            data = bytes.fromhex(t["input"][2:])
            if tb in data or (t["to"] or "").lower()[2:] == tok:
                v = int(t["value"], 16)
                print(f"   +{n-b0:2d} i{int(t['transactionIndex'],16):3d} from {t['from'][:10]} to {(t['to'] or '')[:10]} sel {t['input'][:10]} len {len(data)} val {v/1e18:.6f} nonce {int(t['nonce'],16)} {'LAUNCH' if t['hash']==m['tx'] else ''}")
