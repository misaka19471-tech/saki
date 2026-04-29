#!/usr/bin/env python3
"""用 bili_gui.py 的爬虫逻辑测试全量爬取"""
import requests, hashlib, json, time, urllib.parse

BVID = "BV13Mo5BYEA9"
COOKIE = "SESSDATA=8385ceff%2C1792923812%2C01f6b%2A42CjBo_ka1mWB4NNEDYl6BtmBhsVKSBaegideKMK-n9ZLRcedxMxWAvmD35ZkzgDABPpkSVm5INmVIclVJX0c4SGNUakoxWUhPU3hCaEVfazRTek56Rm43SHE2OTRwR2RkanRGMGllaWpJRDE1SjF3UEo4d3ZwOThfNUVFZTJxTVBYbk9WM05KNUFBIIEC"

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.bilibili.com/',
    'Origin': 'https://www.bilibili.com',
    'Connection': 'keep-alive',
}

MIXIN_INDEX = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 34, 44
]

session = requests.Session()
session.headers.update(BASE_HEADERS)
for item in COOKIE.split(';'):
    item = item.strip()
    if '=' in item:
        k, v = item.split('=', 1)
        session.cookies.set(k.strip(), v.strip())

# Get WBI key
resp = session.get('https://api.bilibili.com/x/web-interface/nav', timeout=10)
data = resp.json()
wbi_img = data.get('data', {}).get('wbi_img', {})
img_key = wbi_img.get('img_url', '').split('/')[-1].split('.')[0]
sub_key = wbi_img.get('sub_url', '').split('/')[-1].split('.')[0]
mixin_key = ''.join((img_key + sub_key)[i] for i in MIXIN_INDEX if i < len(img_key + sub_key))[:32]
print(f"mixin_key={mixin_key}")

def wbi_sign(params):
    sp = {k: str(v) for k, v in params.items()}
    sp['wts'] = str(int(time.time()))
    sorted_keys = sorted(sp.keys())
    qs = '&'.join(f"{k}={urllib.parse.quote(sp[k])}" for k in sorted_keys)
    sp['w_rid'] = hashlib.md5((qs + mixin_key).encode()).hexdigest()
    return sp

# Get video info
resp = session.get(f'https://api.bilibili.com/x/web-interface/view?bvid={BVID}', timeout=15)
info = resp.json()
oid = info['data']['aid']
total = info['data']['stat']['reply']
print(f"oid={oid}, total={total}")

# Crawl with WBI method
all_c, offset, page = [], "", 0
while True:
    page += 1
    time.sleep(0.8)
    params = wbi_sign({
        'oid': oid, 'type': 1, 'mode': 3,
        'pagination_str': json.dumps({"offset": offset}, separators=(',', ':')),
        'plat': 1, 'web_location': 1315875,
    })
    url = 'https://api.bilibili.com/x/v2/reply/wbi/main?' + urllib.parse.urlencode(params)
    resp = session.get(url, timeout=15)
    d = resp.json()
    if d.get('code') != 0:
        print(f"  p{page}: code={d.get('code')} msg={d.get('message')}"); break
    replies = d.get('data', {}).get('replies', [])
    all_c.extend(replies)
    cursor = d.get('data', {}).get('cursor', {})
    next_offset = cursor.get('pagination_reply', {}).get('next_offset', '')
    is_end = cursor.get('is_end', False)
    print(f"  p{page}: +{len(replies)} = {len(all_c)} | is_end={is_end} | next={'有' if next_offset else '空'} | all_count={cursor.get('all_count')}")
    if not next_offset or is_end: break
    offset = next_offset

print(f"\nWBI -> {len(all_c)}/{total}")

# Also try fallback: old API with pn
print("\n=== Fallback: old /x/v2/reply/main?pn ===")
all_c2, pn = [], 1
while True:
    time.sleep(0.8)
    resp = session.get(f'https://api.bilibili.com/x/v2/reply/main?oid={oid}&type=1&mode=3&ps=20&pn={pn}', timeout=15)
    d = resp.json()
    if d.get('code') != 0:
        print(f"  p{pn}: code={d.get('code')} msg={d.get('message')}"); break
    replies = d.get('data', {}).get('replies', [])
    if not replies: break
    all_c2.extend(replies)
    pg = d.get('data', {}).get('page', {})
    total_pages = pg.get('count', 0) // 20 + 1
    if pn <= 3 or pn % 20 == 0:
        print(f"  p{pn}: +{len(replies)} = {len(all_c2)} | count={pg.get('count')} | pages={total_pages}")
    if pn >= total_pages: break
    pn += 1
print(f"Fallback -> {len(all_c2)}/{total}")

# Also try: legacy /x/v2/reply
print("\n=== Legacy: /x/v2/reply?sort=2 ===")
all_c3, pn = [], 1
while True:
    time.sleep(0.8)
    resp = session.get(f'https://api.bilibili.com/x/v2/reply?pn={pn}&type=1&oid={oid}&sort=2', timeout=15)
    d = resp.json()
    if d.get('code') != 0:
        print(f"  p{pn}: code={d.get('code')} msg={d.get('message')}"); break
    replies = d.get('data', {}).get('replies', [])
    if not replies: break
    all_c3.extend(replies)
    pg = d.get('data', {}).get('page', {})
    total_pages = pg.get('count', 0) // 20 + 1
    if pn <= 3 or pn % 20 == 0:
        print(f"  p{pn}: +{len(replies)} = {len(all_c3)} | count={pg.get('count')} | pages={total_pages}")
    if pn >= total_pages: break
    pn += 1
print(f"Legacy -> {len(all_c3)}/{total}")

print(f"\nSUMMARY: WBI={len(all_c)}, Fallback={len(all_c2)}, Legacy={len(all_c3)}, Total={total}")
