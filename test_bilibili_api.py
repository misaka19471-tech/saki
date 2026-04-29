"""测试 bilibili-api 库全量爬取"""
import asyncio
from bilibili_api import sync, Credential
from bilibili_api.comment import CommentResourceType, OrderType, get_comments

BVID = "BV13Mo5BYEA9"
SESSDATA = "8385ceff%2C1792923812%2C01f6b%2A42CjBo_ka1mWB4NNEDYl6BtmBhsVKSBaegideKMK-n9ZLRcedxMxWAvmD35ZkzgDABPpkSVm5INmVIclVJX0c4SGNUakoxWUhPU3hCaEVfazRTek56Rm43SHE2OTRwR2RkanRGMGllaWpJRDE1SjF3UEo4d3ZwOThfNUVFZTJxTVBYbk9WM05KNUFBIIEC"

async def main():
    credential = Credential(sessdata=SESSDATA)

    # 获取视频 OID
    from bilibili_api.video import Video
    v = Video(bvid=BVID, credential=credential)
    info = await v.get_info()
    oid = info["aid"]
    total = info["stat"]["reply"]
    print(f"oid={oid}, title={info['title'][:30]}, total={total}")

    # 用旧版 page-based API (有 Credential)
    all_comments = []
    page = 1
    while True:
        data = await get_comments(
            oid=oid,
            type_=CommentResourceType.VIDEO,
            page_index=page,
            order=OrderType.LIKE,
            credential=credential,
        )
        replies = data.get("replies") or []
        all_comments.extend(replies)
        page_info = data.get("page", {})
        count = page_info.get("count", 0)
        print(f"  p{page}: +{len(replies)} = {len(all_comments)} | count={count}")
        if not replies:
            break
        if count and len(all_comments) >= count:
            break
        page += 1

    print(f"\nRESULT: {len(all_comments)}/{total}")

sync(main())
