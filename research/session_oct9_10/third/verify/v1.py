import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
txs = {
 "launch": "0x5c7330a350687a4629cc20eaba15c1fdc4880775488847272610208211b9d1a7",
 "deploy_exec": "0x65a23afedb5dc39d9d9c710e23e778a46be268ccd72d9ca99beb8de21b822533",
 "fund_relayer": "0x18b2fd680f886dc3a95f4f925e95bc070c927e1e016a1e18ea723776ec31cc5b",
 "dump1": "0xd6999594645cf2bb5fdf2b13fb8761e8351a21fad8e110d1a8a4c14377880c39",
 "fee": "0x10e5ecc119e758e946be923a5c9df0545d0f94d18b7f6508fe42a10f147f4267",
 "coll_disp": "0xc6ed04c1a122e9f3ffaa4f893a1aad9249d7c6212826c1ed13e7b470ae9a284f",
 "disp_creator": "0xa73fa73868884f668af8382071887107075028eaf9c14e7ca0ffe2cf0f32492c",
 "dump2": "0xe92a079cc602eec76251b0acefab85a1f6923019330824a0eb8554b84bc96bdd",
 "coll2_disp": "0xee8b7a27ee63cbcadb4fce7bcb98ca05248cfa98179d1767f2179293fff50271",
 "zsweep": "0x512b98338ffa13fc6d9be14cc0a4e30cf5bbc2941d9753bc93cb7c7711ff9097",
 "Y1": "0xb389bfba7c6314690715f3850bff88f6af2c51c2410d70cc1d6bbdd0ea31dc17",
 "feeclaim": "0xfdf733c7eae52f9ecf3bf761b04626e85fe1af44a3850b7c1edc78b88e5210fc",
 "loopB": "0xf4c206f1b1496d12a2ac71c107c9697fa332f95aadbe429259153a0e184e4fde",
}
res = batch([("eth_getTransactionByHash",[h]) for h in txs.values()] + [("eth_getTransactionReceipt",[h]) for h in txs.values()])
n = len(txs); out = {}
for i,k in enumerate(txs):
    t, r = res[i], res[n+i]
    out[k] = {"tx": t, "rc": r}
    if not t: print(k, "MISSING"); continue
    print(f"== {k} blk {int(t['blockNumber'],16)} from {t['from']} to {t.get('to')} val {int(t['value'],16)/1e18:.6f} nonce {int(t['nonce'],16)} type {t.get('type')} sel {t['input'][:10]} len {len(t['input'])} status {r['status']} contract {r.get('contractAddress')} nlogs {len(r['logs'])}")
    for l in r['logs'][:40]:
        print("   ", l['address'], [x[:10]+'..'+x[-40:] if len(x)==66 else x for x in l['topics']], l['data'][:200])
json.dump(out, open("v1.json","w"))
