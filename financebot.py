# 福生无量天尊
from openai import OpenAI
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os

# OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
# 从环境变量获取 Server酱 SendKeys
server_chan_keys_env = os.getenv("SERVER_CHAN_KEYS")
if not server_chan_keys_env:
    raise ValueError("环境变量 SERVER_CHAN_KEYS 未设置，请在Github Actions中设置此变量！")
server_chan_keys = server_chan_keys_env.split(",")

openai_client = OpenAI(api_key=openai_api_key, base_url="https://api.deepseek.com/v1")

# RSS源地址列表
rss_feeds = {
    "💲 华尔街见闻":{
        "华尔街见闻":"https://dedicated.wallstreetcn.com/rss.xml",      
    },
    "💻 36氪":{
        "36氪":"https://36kr.com/feed",   
        },
    "🇨🇳 中国经济": {
        "香港經濟日報":"https://www.hket.com/rss/china",
        "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
        "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
        "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
        "国家统计局-最新发布":"https://www.stats.gov.cn/sj/zxfb/rss.xml",
    },
      "🇺🇸 美国经济": {
        "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
        "华尔街日报 - 市场":"https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
        "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
        "ETF Trends": "https://www.etftrends.com/feed/",
    },
    "🌍 世界经济": {
        "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
        "BBC全球经济": "http://feeds.bbci.co.uk/news/business/rss.xml",
    },
}

# 关键词过滤（中文 + 英文），可按需扩展
FILTER_KEYWORDS = [
    "零食", "零售", "连锁",
    "snack", "snacks", "retail", "chain", "chains",
    "convenience", "convenience store", "grocery", "supermarket",
    "store", "retailer"
]

# 是否启用 DeepSeek 语义分类（需要设置 OPENAI_API_KEY）
USE_DEEPSEEK = bool(openai_api_key)


def contains_keyword(text: str) -> bool:
    """快速关键词匹配（中/英混合）。"""
    if not text:
        return False
    text_lower = text.lower()
    for kw in FILTER_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def classify_with_deepseek(text: str) -> bool:
    """
    使用 DeepSeek（OpenAI 兼容接口）对文章进行相关性判断。
    要求模型只返回 YES 或 NO。出错时返回 False（不相关）。
    """
    if not USE_DEEPSEEK:
        return False
    try:
        # 尽量控制输入长度以减少 token 消耗
        prompt_text = text[:3000]
        completion = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": (
                    "你是一个简洁的二分类文本判断器。判断给定新闻是否与零食、零售、连锁相关，"
                    "同时包含它们的英文对应词（例如 snack, retail, chain 等）。只返回一个单词：YES 表示相关，NO 表示不相关。"
                )},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=6,
            temperature=0
        )
        resp = completion.choices[0].message.content.strip().upper()
        if resp.startswith("Y") or resp.startswith("是") or "YES" in resp:
            return True
        return False
    except Exception as e:
        print(f"⚠️ DeepSeek 分类出错：{e}")
        return False

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 爬取网页正文 (用于 AI 分析，但不展示)
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"⚠️ 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"❌ 文章爬取失败: {url}，错误: {e}")
        return "（未能获取文章正文）"

# 添加 User-Agent 头
def fetch_feed_with_headers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)


# 自动重试获取 RSS
def fetch_feed_with_retry(url, retries=3, delay=5):
    for i in range(retries):
        try:
            feed = fetch_feed_with_headers(url)
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                return feed
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取RSS内容（爬取正文但不展示）
def fetch_rss_articles(rss_feeds, max_articles=10):
    news_data = {}
    analysis_text = ""  # 用于AI分析的正文内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            print(f"📡 正在获取 {source} 的 RSS 源: {url}")
            feed = fetch_feed_with_retry(url)
            if not feed:
                print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                continue
            print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

            articles = []  # 每个 source 都需要重新初始化列表
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                if not link:
                    print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                    continue

                # 先做快速关键词匹配
                quick_text = f"{title}\n{summary}"
                quick_hit = contains_keyword(quick_text)

                # 爬取正文用于深度分析（仅在需要时使用）
                article_text = None
                if quick_hit:
                    # 若关键词命中，再爬正文用于后续汇总
                    article_text = fetch_article_text(link)
                    relevant = True
                else:
                    # 关键词未命中，尝试爬取正文并用 DeepSeek 判定
                    article_text = fetch_article_text(link)
                    check_text = f"{title}\n{summary}\n{article_text}"
                    if USE_DEEPSEEK:
                        relevant = classify_with_deepseek(check_text)
                    else:
                        relevant = False

                if not relevant:
                    print(f"⛔ 已移除不相关新闻: {title}")
                    continue

                # 若相关，加入分析文本和展示列表
                analysis_text += f"【{title}】\n{article_text}\n\n"
                print(f"🔹 {source} - {title} 获取并保留")
                articles.append(f"- [{title}]({link})")

            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

        news_data[category] = category_content

    return news_data, analysis_text

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    completion = openai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": """
             你是一名专业的财经新闻分析师，请根据以下新闻内容，按照以下步骤完成任务：
             1. 提取新闻中涉及的主要行业和主题，找出近1天涨幅最高的3个行业或主题，以及近3天涨幅较高且此前2周表现平淡的3个行业/主题。（如新闻未提供具体涨幅，请结合描述和市场情绪推测热点）
             2. 针对每个热点，输出：
                - 催化剂：分析近期上涨的可能原因（政策、数据、事件、情绪等）。
                - 复盘：梳理过去3个月该行业/主题的核心逻辑、关键动态与阶段性走势。
                - 展望：判断该热点是短期炒作还是有持续行情潜力。
             3. 将以上分析整合为一篇1500字以内的财经热点摘要，逻辑清晰、重点突出，适合专业投资者阅读。
             """},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content.strip()

# 发送微信推送
def send_to_wechat(title, content):
    for key in server_chan_keys:
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        response = requests.post(url, data=data, timeout=10)
        if response.ok:
            print(f"✅ 推送成功: {key}")
        else:
            print(f"❌ 推送失败: {key}, 响应：{response.text}")


if __name__ == "__main__":
    today_str = today_date().strftime("%Y-%m-%d")

    # 每个网站获取最多 5 篇文章
    articles_data, analysis_text = fetch_rss_articles(rss_feeds, max_articles=5)
    
    # AI生成摘要
    summary = summarize(analysis_text)

    # 生成仅展示标题和链接的最终消息
    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"

    # 推送到多个server酱key
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
