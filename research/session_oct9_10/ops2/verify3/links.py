"""Adversarial re-fetch of key money links by tx hash: from, to, value, nonce, block, status (receipt)."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
L = [
 ("A1 main-loop deployer payout -> sweep", "0x96b31a93402af64fe3e002e3f1f8f982924bf221a48c260e6f4eef6ebd6e1771", "0x1763ea0e", "0x155f7db6", 3.2427, 2),
 ("A2 main-loop sweep -> dispatcher", "0x780e107e420a9c180dfeac8048045fd89fe277b3c37efda294f6448c489cfc21", "0x155f7db6", "0xe777da08", 7.0151, 0),
 ("A3 main-loop dispatcher n0 -> next deployer", "0x58499e0281fcff9ba5cf570ba753945069365d12355133cf11f24fa55a0d9798", "0xe777da08", "0xad3a1185", 2.7, 0),
 ("A4 dispatcher n1 -> crowd A 0x8700722d", "0xdd18f16ef8c76fe2fc8952287b710a531ddc4aa997c6ea5188e53b0fcfd49daf", "0xe777da08", "0x8700722d", 0.1256, 1),
 ("A5 main-loop dispatcher n0 -> latest deployer", "0x8e6d2d0a7ddc871e48c66a75bbe07934aa54de353f6066a407791724e0d1bbc0", "0x99b5ef5b", "0xfff26739", 2.11, 0),
 ("A6 latest launch", "0x063763da35d62e07e8b83d3fb526682a85b564ad831861dd71c1eef20add9303", "0xfff26739", "0x3194e326", 2.06, 0),
 ("A7 deployer funding of 0x1763ea0e", "0x6e88108c615e710f9eb577a016c5af4bd57fe17493b06e8ec1d557ee49e91fd7", "0xc84b1899", "0x1763ea0e", 2.75, 0),
 ("R1 restart: A trading wallet -> restart sweep", "0xb647db1c693e71c057737462fe0428115425bbd70a5e51ff6fccc1bc9e63ed01", "0xb63b68dc", "0xc139beb5", 2.219144, 6),
 ("R2 restart: crowd A 0x5861 -> restart sweep", "0x4f223d29c5e05cd2e25781654c7d654cffab1d794d476f72462b7828765ff67f", "0x58617088", "0xc139beb5", 0.17569, 1417),
 ("R3 restart sweep -> dispatcher", "0x3e98c3ae7d5e7f84ca448fe33c5cd06ecef13904990213813466cd900f5e3e0d", "0xc139beb5", "0x501f4f53", 7.038845, 0),
 ("X1 A trading wallet -> 0x3ee51814", "0x2974176467b389d234d8e7303bb2774e665a659539929703c31f9a84a19e3104", "0xb63b68dc", "0x3ee51814", 1.6, 5),
 ("X2 0x3ee51814 -> crowd D sweep", "0x0b633ab81c65a39d6c24ec712309f8c7b3643828ef7e89ab0fa2f3fae7d51161", "0x3ee51814", "0xdef59ef1", 0.8, 17),
 ("B1 B launch 14:32 deployer payout -> B sweep", "0x99c2e95c2379a2dc115e40474bb225dbbe0b5bdcb0167219a1652b3b0cfba365", "0x1821144f", "0xded28cc0", 6.154848, 7),
 ("B2 B sweep -> B dispatcher", "0x774ab9d983fbd4a9d3474c15880a02495cb2c97f0225d9a2ad8f74fcff489401", "0xded28cc0", "0x58fc6f17", 6.188873, 0),
 ("B3 B dispatcher n0 -> copy collector", "0x192930f63a6b51d79e75ac5ee1feead66af77f827a7dcd91a0fe51aa6521b7b8", "0x58fc6f17", "0x3fc5b8b8", 3.5, 0),
 ("B4 B dispatcher n1 -> crowd B 0x4c45af68", "0xeb0a93a44da91f36e9dd39ba627b048e36466deb744743529cf5cb0a271eb003", "0x58fc6f17", "0x4c45af68", 0.095447, 1),
 ("B5 crowd B 0x4c45af68 -> collector", "0xfc117e6f099bc482b9a50a810c4787a2e3ae91ae46b339ceb0c24de407db38ea", "0x4c45af68", "0x3fc5b8b8", 0.095446, None),
 ("B6 collector n789 exit", "0xb7dbc93be025fff40b61c6bd448b3d09174bcb46fa02c43c40000f9feb61967a", "0x3fc5b8b8", "0x1d18f103", 6.180324, 789),
 ("B7 relay -> B dispatcher", "0x8777a13d6d600e4c76f83d0304eb7d845edfefdbf3af6ec1406ef7e691b5d2ec", "0x1d18f103", "0xe50dd00a", 6.18031, 0),
 ("B8 B dispatcher -> crowd B 0x4c45af68", "0x707e73df0dc2f133ecd4d7c63ba8a172e1ff9559ed4e815ab7e00300b9961c82", "0xe50dd00a", "0x4c45af68", 0.132692, None),
 ("B9 collector n0 first copy funding", "0xe445bde075ef2916f00fd460d2cdd6896ec77899e573572f18012485ca95f305", "0x3fc5b8b8", "0xfcfdd782", 4.762014, 0),
 ("B10 today B deployer payout -> B sweep", "0x799b449f30850094d2ec2031824ebd80378549b6042c344cc691a03a30e6ba94", "0xa57fb285", "0xf9c48bc5", 2.249787, 2),
 ("B11 today B sweep -> B dispatcher", "0x89555ad9896004415377749bec4d76f653858091a68829e0cab7d5b7f52919ee", "0xf9c48bc5", "0xb0c4ef67", 4.85733, 0),
 ("B12 today B dispatcher n0 -> next B deployer", "0x96a8b8b84b7788f9e7971a2cc261d33b1ae6a49ac77733c105d25732d7a50f81", "0xb0c4ef67", "0x3298890a", 2.6, 0),
 ("B13 today B dispatcher n0 -> deployer 0xae35895b", "0xa75332fb1b7595ef98b19b3a11cdec9075fe840a7ceb1f06afd291c6d3fb4d24", "0xefa9bf82", "0xae35895b", 1.2, 0),
 ("B14 today B sweep -> dispatcher 0xefa9bf82", "0x65560f5ccbe5d5f11775c66dc36d6e9ceaf3023869bd2be42dee06016b93720e", "0x97630305", "0xefa9bf82", 4.855207, 0),
 ("C1 launcher creation", "0x7022ad9304f44da91edab20de0e17b9d30cd11810c3e7e5896e854ed50e71789", "0x3b11cafa", "", 0, 0),
 ("C2 first launch", "0x5abcd10225ed4e8e27a8057a7d3d3b95f2892321b9b6d62ac3b292211d97c3f9", "0x3b11cafa", "0x3194e326", 0.1, 1),
 ("C3 creator funding", "0x69653e38ecd216b4eb8f9ca72169d79831c39de3ae6ed5ecea22e29684bb0120", "0x3130ea49", "0x3b11cafa", 0.14999267808, 0),
 ("F1 pot F: 12:43 deployer payout -> F hub", "0x3fa9b0ae4da1f50b6cd67ef70f409feedc7465ccff8b60579ba0f4f37eee0a3c", "0x583fec35", "0xd4b94999", 1.899952, None),
 ("F2 pot F last pull", "0x5f652e96af74930b85ecae772dcfa88334aa729d8b9a8ceb4f6a5058a746b234", "0x1fd5451b", "0x58daec31", 0, None),
 ("K1 copy launch via own copy", "0x081bd2300a44d8864460148abf5541d42053205df24974e1e2cf1d1318b9fd0c", "0xc423cbd2", "0x8ea696db", 4.094, None),
]
calls = []
for _, h, *__ in L: calls += [("eth_getTransactionByHash", [h]), ("eth_getTransactionReceipt", [h])]
res = []
for i in range(0, len(calls), 40):
    res += batch(calls[i:i+40]); time.sleep(2)
ok = 0; out = []
for k, (lab, h, ef, et, ev, en) in enumerate(L):
    t, r = res[2*k], res[2*k+1]
    if not t: print("MISSING", lab, h); continue
    fr, to = t["from"].lower(), (t.get("to") or "").lower(); v = int(t["value"], 16)/1e18; n = int(t["nonce"], 16); b = int(t["blockNumber"], 16)
    st = int(r["status"], 16) if r else None; ca = (r or {}).get("contractAddress")
    good = fr.startswith(ef) and (to.startswith(et) if et else True) and abs(v - ev) < 1e-5 and (en is None or n == en) and st == 1
    ok += good
    print(f"{'OK ' if good else 'BAD'} {lab}: blk {b} {fr} -> {to or 'CREATE '+str(ca)} {v:.6f} ETH nonce {n} status {st} sel {t['input'][:10]}")
    out.append(dict(label=lab, hash=h, block=b, frm=fr, to=to, eth=v, nonce=n, status=st, contract=ca, sel=t["input"][:10], ok=good))
print(ok, "of", len(L), "match")
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2/verify3/links.json", "w"), indent=1)
