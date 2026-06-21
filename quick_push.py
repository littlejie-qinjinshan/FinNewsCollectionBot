import feedparser
import requests
from datetime import datetime
import pytz
import os
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

selected_feeds = {
    "💲 财经媒体": {
        "华尔街见闻": "https://dedicated.wallstreetcn.com/rss.xml",
        "财联社": "https://www.cls.cn/rss",
    },
    "💻 科技媒体": {
        "36氪": "https://36kr.com/feed",
    },
    "📰 综合新闻": {
        "澎湃新闻": "https://www.thepaper.cn/rss",
    },
}

today_str = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")
final_summary = f"📅 **{today_str} 财经新闻摘要（即时推送）**\n\n"

for category, sources in selected_feeds.items():
    category_content = ""
    for source, url in sources.items():
        print(f"📡 获取 {source}: {url}")
        try:
            feed = feedparser.parse(url, request_headers=headers)
        except Exception as e:
            print(f"❌ {source} 获取失败: {e}")
            continue
        if not feed or not feed.entries:
            print(f"⚠️ {source} 没有内容")
            continue
        print(f"✅ {source} 获取成功，共 {len(feed.entries)} 条")
        articles = []
        for entry in feed.entries[:5]:
            title = entry.get('title', '无标题').strip()
            link = entry.get('link', '') or entry.get('guid', '')
            if not link:
                continue
            articles.append(f"- [{title}]({link})")
        if articles:
            category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"
    if category_content:
        final_summary += f"## {category}\n{category_content}\n\n"

final_summary += "---\n\n📌 以上为即时抓取的新闻标题与链接汇总。"

print("\n" + "=" * 50)
print("最终推送内容预览：")
print("=" * 50)
print(final_summary[:2000])

server_chan_keys_env = os.getenv("SERVER_CHAN_KEYS", "")
if server_chan_keys_env and server_chan_keys_env.strip():
    keys = [k.strip() for k in server_chan_keys_env.split(",") if k.strip()]
    for key in keys:
        try:
            url = f"https://sctapi.ftqq.com/{key}.send"
            data = {"title": f"📌 {today_str} 财经新闻摘要", "desp": final_summary}
            r = requests.post(url, data=data, timeout=10)
            if r.ok:
                print(f"✅ 推送成功: {key}")
            else:
                print(f"❌ 推送失败: {key} => {r.text}")
        except Exception as e:
            print(f"❌ 推送异常: {e}")
else:
    print("\n⚠️ SERVER_CHAN_KEYS 未配置，跳过微信推送，仅在控制台打印结果。")
