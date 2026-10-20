"""Hourly launch counts per fingerprint cluster (s03 + clusters.py), Oct 11 18:00 UTC to the head; clusters with >= 4 launches, the rest summed.
Per cluster: launches, distinct senders, senders at nonce <= 20, first..last launch."""
import collections, time
from clusters import load
rows = load()
hours = list(range(int(rows[0]["t"] // 3600), int(rows[-1]["t"] // 3600) + 1))
g = collections.defaultdict(list)
for r in rows: g[r["fam"]].append(r)
big = sorted([k for k in g if len(g[k]) >= 4], key=lambda k: -len(g[k]))
print("UTC hour (Oct 11 18 .. Oct 12 %s)" % time.strftime("%H", time.gmtime(hours[-1] * 3600)))
print("%-58s %5s %5s %5s %-23s | %s" % ("cluster", "n", "sndr", "fresh", "first..last", " ".join(time.strftime("%H", time.gmtime(h * 3600)).rjust(3) for h in hours)))
def line(name, v):
    c = collections.Counter(int(r["t"] // 3600) for r in v)
    print("%-58s %5d %5d %5d %s..%s | %s" % (name[:58], len(v), len({r["from"] for r in v}), sum(r["nonce"] <= 20 for r in v), time.strftime("%d %H:%M", time.gmtime(v[0]["t"])), time.strftime("%d %H:%M", time.gmtime(v[-1]["t"])),
                                           " ".join(str(c[h]).rjust(3) for h in hours)))
for k in big: line(k, g[k])
rest = [r for k in g if k not in big for r in g[k]]; rest.sort(key=lambda r: r["t"])
line("(all other clusters, < 4 launches each: %d clusters)" % len([k for k in g if k not in big]), rest)
line("ALL", rows)
