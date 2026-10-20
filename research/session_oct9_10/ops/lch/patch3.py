s=open('trace.py').read()
s=s.replace('''    # forwards: deployer's txs after the pull''','''    # the deployer's funder: everything it sent around then (who else it funded)
    if res["back"] and res["back"][0]["incoming"]:
        f0 = max(res["back"][0]["incoming"], key=lambda x: x["eth"])
        o, _ = outgoing(f0["from"], f0["bn"] - 100, maxfwd=600, want=200, extra=150)
        res["funder_sends"] = [{"to": x["to"], "eth": x["eth"], "nonce": x["nonce"], "bn": x["bn"], "tag": tag(x["to"])} for x in o]
    # forwards: deployer's txs after the pull''')
s=s.replace('''            res["fwd"].append({"hop": 2, "addr": r, "scanned": [big[0]["bn"], hi2], "out": o2})''','''            res["fwd"].append({"hop": 2, "addr": r, "scanned": [big[0]["bn"], hi2], "out": o2})
            ins = [T(bn, ts, t) for bn, ts, t in bc.txs(big[0]["bn"] - 100, big[0]["bn"] + 100) if t[2] == r and int(t[3]) > 0]
            res["collector_in"] = [{"from": x["from"], "eth": x["eth"], "nonce": x["nonce"], "bn": x["bn"], "tag": tag(x["from"])} for x in ins]''')
open('trace.py','w').write(s)
