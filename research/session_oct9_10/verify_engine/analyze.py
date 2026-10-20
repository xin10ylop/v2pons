import json, base64, collections, sys
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
kinds = collections.Counter(); hk = collections.Counter(); per = []; seqs = []
first = None
for line in open(sys.argv[1]):
    fr = json.loads(line)
    if first is None: first = fr
    for m in fr.get("messages", []):
        inner = (m.get("message") or {}).get("message") or {}; hdr = inner.get("header") or {}
        raw = base64.b64decode(inner.get("l2Msg", "") or "")
        hk[hdr.get("kind")] += 1
        k = raw[0] if raw else None; kinds[k] += 1
        n_engine = len(E.decode_batch(inner.get("l2Msg", ""))) if hdr.get("kind") == 3 else None
        per.append((m.get("sequenceNumber"), hdr.get("kind"), k, len(raw), n_engine))
print("header kinds", hk); print("l2Msg first byte", kinds)
print("frame keys", list(first.keys()), "msgs/frame", collections.Counter(len(json.loads(l).get("messages", [])) for l in open(sys.argv[1])))
for r in per[:40]: print(r)
json.dump(per, open("per.json", "w"))
