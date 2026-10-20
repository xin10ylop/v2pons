"""Every token Transfer INTO the bot router (buys arrive PM -> router; deploys arrive 0x0 -> router), block A..head."""
import kc, json
A = 86100000
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
head = max(r["block"] for r in rows)
lg = kc.cached_logs("k03_botin_cache.jsonl", {"topics": [kc.T_TR, None, "0x" + "0" * 24 + kc.BOT[2:]]}, A, head, step=20000)
print("transfers into BOT", len(lg), "blocks", A, head)
