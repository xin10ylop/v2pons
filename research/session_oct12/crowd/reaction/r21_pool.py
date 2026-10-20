"""print one pool (by address prefix) from r04_pools_cache.jsonl: every swap up to the pull with its class, sender wallet and contract."""
from common import *
pre = sys.argv[1].lower()
for line in open(J("r04_pools_cache.jsonl")):
    p = json.loads(line)
    if not p["pool"].startswith(pre): continue
    print(f"pool {p['pool']} launch {utc(p['ts'])} lb {p['lb']} qs {p['qs']} lw {p['from']} pull +{p['pull_off']} by {p['pull_from']}")
    for s in p["sw"]:
        print(f"  +{s['off']:<5} {s['k']:<7} {s['dq']/1e18:+.5f} ETH  from {(s['from'] or '-')[:12]:<12} to {(s['to'] or '-')[:10]:<10} {s['sel'] or ''}/{s['len'] or ''} rcpt {s['rcpt'][:10]}")
