#!/usr/bin/env python3
"""DrissionPage: 多排序模式合并去重 v2"""
from DrissionPage import ChromiumPage, ChromiumOptions
import json, time

COOKIE_RAW = "8385ceff%2C1792923812%2C01f6b%2A42CjBo_ka1mWB4NNEDYl6BtmBhsVKSBaegideKMK-n9ZLRcedxMxWAvmD35ZkzgDABPpkSVm5INmVIclVJX0c4SGNUakoxWUhPU3hCaEVfazRTek56Rm43SHE2OTRwR2RkanRGMGllaWpJRDE1SjF3UEo4d3ZwOThfNUVFZTJxTVBYbk9WM05KNUFBIIEC"
BVID = "BV13Mo5BYEA9"

co = ChromiumOptions()
co.set_argument("--disable-blink-features=AutomationControlled")
page = ChromiumPage(co)
page.set.cookies([{"name": "SESSDATA", "value": COOKIE_RAW, "domain": ".bilibili.com"}])

# 获取 oid
page.get(f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}")
time.sleep(1.5)
info = json.loads(page.run_js("return document.body.innerText"))
total_expected = info["data"]["stat"]["reply"]
print(f"Expected: {total_expected}", flush=True)

INTERCEPTOR = "window.__c=[];(function(){var o=window.fetch;window.fetch=function(...a){var u=typeof a[0]==='string'?a[0]:(a[0]?.url||'');var p=o.apply(this,a);if(u.includes('wbi/main')){p.then(r=>r.clone().json()).then(d=>{window.__c.push(d);})}return p;}})();"

all_rpids = set()

# 加载视频页一次
page.get(f"https://www.bilibili.com/video/{BVID}")
time.sleep(5)
page.run_js(INTERCEPTOR)

# 爬取两个模式
for label, click_js in [
    ("按热度", None),  # 默认就是按热度
    ("按时间", """var els=document.querySelectorAll('.reply-header .sort-item,.reply-sort-item,.sort-tabs span');for(let e of els){if(e.textContent.includes('时间')){e.click();break;}}"""),
]:
    if click_js:
        print(f"\n=== {label} ===", flush=True)
        page.run_js(click_js)
        time.sleep(3)
        page.run_js("window.__c=[]")  # 清空旧数据
        page.run_js(INTERCEPTOR)
    else:
        print(f"\n=== {label} (默认) ===", flush=True)

    for i in range(120):
        page.run_js("window.scrollBy(0, 3000)")
        time.sleep(0.5)
        cnt = page.run_js("return window.__c.length")
        end = page.run_js(f"return window.__c.length>0?window.__c[window.__c.length-1].data?.cursor?.is_end:null") if cnt > 0 else None
        if i % 30 == 0:
            print(f"  scroll {i}: {cnt} pkts, end={end}", flush=True)
        if end and cnt > 3:
            break

    caps = json.loads(page.run_js("return JSON.stringify(window.__c)"))
    mode_set = set()
    for c in caps:
        for r in (c.get("data") or {}).get("replies") or []:
            if r.get("rpid"):
                mode_set.add(r["rpid"])
    print(f"  => {len(mode_set)} unique", flush=True)
    all_rpids |= mode_set

print(f"\nTOTAL: {len(all_rpids)}/{total_expected} ({len(all_rpids)/total_expected*100:.1f}%)", flush=True)
page.quit()
