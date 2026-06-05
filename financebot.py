# 福生无量天尊
import sys
import io
import os
# 修复 Windows 控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

# HTTP 服务端口配置
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
ENABLE_HTTP = os.getenv("ENABLE_HTTP", "true").lower() == "true"

try:
    from openai import OpenAI
except Exception:
    OpenAI = None
    print("[WARNING] openai 模块不可用，DeepSeek 相关功能将被禁用。若需要，请安装 openai 包并设置 OPENAI_API_KEY。")
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import re
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
import schedule

# OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")

# 从环境变量获取 Server酱 SendKeys（非必须，未设置时仅打印摘要）
server_chan_keys_env = os.getenv("SERVER_CHAN_KEYS", "")
if server_chan_keys_env and server_chan_keys_env.strip():
    server_chan_keys = [k.strip() for k in server_chan_keys_env.split(",") if k.strip()]
else:
    server_chan_keys = []
    print("[WARNING] 环境变量 SERVER_CHAN_KEYS 未设置，推送功能将被禁用。设置 SERVER_CHAN_KEYS 后可启用微信推送。")

# 邮件配置
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.163.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")  # 发件人邮箱
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # 发件人授权码
# 收件人邮箱（多个邮箱用逗号分隔）
RECIPIENT_EMAILS = [email.strip() for email in os.getenv("RECIPIENT_EMAIL", "18685329778@163.com").split(",") if email.strip()]
# 定时任务配置（默认每天早上 9 点）
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "09:00")

# 初始化 OpenAI/DeepSeek 客户端（可选）
openai_client = None
if openai_api_key:
    try:
        openai_client = OpenAI(api_key=openai_api_key, base_url="https://api.deepseek.com/v1")
    except Exception as e:
        print(f"[WARNING] 无法初始化 OpenAI/DeepSeek 客户端: {e}")

# 是否启用 DeepSeek 语义分类（以客户端是否可用为准）
USE_DEEPSEEK = bool(openai_client)

# RSS源地址列表
rss_feeds = {
    "[财经媒体]": {
        "华尔街见闻": "https://dedicated.wallstreetcn.com/rss.xml",
        "东方财富": "http://rss.eastmoney.com/rss_partener.xml",
        "香港经济日报": "https://www.hket.com/rss/china",
        "中新网财经": "https://www.chinanews.com.cn/rss/finance.xml",
        "人民日报财经": "http://www.people.com.cn/rss/finance.xml",
    },
    "[科技媒体]": {
        "36氪": "https://36kr.com/feed",
        "虎嗅网": "https://www.huxiu.com/rss/0.xml",
        "钛媒体": "https://www.tmtpost.com/rss",
        "爱范儿": "https://www.ifanr.com/feed",
        "IT之家": "https://www.ithome.com/rss/",
    },
    "[综合新闻]": {
        "人民日报时政": "http://www.people.com.cn/rss/politics.xml",
        "人民日报国际": "http://www.people.com.cn/rss/world.xml",
    },
    "[国际财经]": {
        "华尔街日报": "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
        "MarketWatch": "https://www.marketwatch.com/rss/topstories",
        "BBC商业": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "CNBC财经": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "CNBC商业": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "CNBC投资": "https://www.cnbc.com/id/15839069/device/rss/rss.html",
        "CNBC财报": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        "CNBC新闻": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    },
    "[A股市场]": {
        "个股频道": "http://rss.jrj.com.cn/stock/725.xml",
        "综合频道": "http://rss.jrj.com.cn/stock/734.xml",
        "个股异动": "http://rss.jrj.com.cn/stock/677.xml",
        "报刊头条": "http://rss.jrj.com.cn/stock/742.xml",
        "新股要闻": "http://rss.jrj.com.cn/stock/724.xml",
        "公告速递": "http://rss.jrj.com.cn/stock/729.xml",
        "今日提示": "http://rss.jrj.com.cn/stock/727.xml",
        "行业新闻": "http://rss.jrj.com.cn/stock/740.xml",
        "数据掘金": "http://rss.jrj.com.cn/stock/736.xml",
        "融资融券": "http://rss.jrj.com.cn/stock/733.xml",
        "机会情报": "http://rss.jrj.com.cn/stock/745.xml",
    },
    "[港股市场]": {
        "港交所参与者通告": "https://sc.hkex.com.hk/TuniS/www.hkex.com.hk/Services/RSS-Feeds/The-Stock-Exchange-of-Hong-Kong-Limited?sc_lang=zh-HK",
        "港交所研究资料": "https://sc.hkex.com.hk/TuniS/www.hkex.com.hk/Services/RSS-Feeds/Research-Materials?sc_lang=zh-HK",
    },
    "[美股市场]": {
        "SeekingAlpha ETF策略": "https://seekingalpha.com/tag/etf-portfolio-strategy.xml",
        "SeekingAlpha IPO分析": "https://seekingalpha.com/tag/ipo-analysis.xml",
        "SeekingAlpha医疗板块": "https://seekingalpha.com/sector/healthcare.xml",
        "SeekingAlpha突发新闻": "https://seekingalpha.com/market_currents.xml",
        "纳斯达克财报": "https://www.nasdaq.com/feed/rssoutbound?category=Earnings",
        "纳斯达克市场": "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
        "纳斯达克分红": "https://www.nasdaq.com/feed/rssoutbound?category=Dividends",
        "SEC文件": "https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
    },
}

# 关键词过滤（中文 + 英文），可按需扩展
FILTER_KEYWORDS = [
    "零食", "零售", "连锁",
    "snack", "snacks", "retail", "chain", "chains",
    "convenience", "convenience store", "grocery", "supermarket",
    "store", "retailer"
]

def contains_keyword(text: str) -> bool:
    """快速关键词匹配（中/英混合）。"""
    if not text:
        return False
    text_lower = text.lower()
    for kw in FILTER_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def classify_titles_with_deepseek(titles: list) -> dict:
    """
    对一组新闻标题进行批量判定，返回编号到标签的映射。
    标签为 'YES'/'NO'/'MAYBE'。如果 DeepSeek 不可用，则基于关键词做保守回退（命中关键词为 YES，其他为 MAYBE）。
    """
    labels = {}
    if not titles:
        return labels

    # 初始化默认为 MAYBE（不剔除）
    for i in range(1, len(titles) + 1):
        labels[i] = 'MAYBE'

    if not USE_DEEPSEEK or not openai_client:
        for i, t in enumerate(titles, start=1):
            labels[i] = 'YES' if contains_keyword(t) else 'MAYBE'
        return labels

    # 构造编号标题列表
    numbered = "\n".join([f"{i}. {titles[i-1]}" for i in range(1, len(titles)+1)])
    system_prompt = (
        "你是一个简洁的三分类文本判断器。给定编号的新闻标题列表，判断每条标题是否与零食、零售、连锁相关（包括英文关键词 snack/retail/chain 等）。\n"
        "对于每个编号仅输出一行，格式为：编号: YES|NO|MAYBE。YES 表示明确相关，NO 表示明确不相关，MAYBE 表示仅凭标题无法判断。不要输出额外说明。"
    )
    try:
        resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": numbered}
            ],
            max_tokens=max(64, len(titles) * 6),
            temperature=0
        )
        text = resp.choices[0].message.content
        # 解析每行结果
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\s*(\d+)\s*[:\.\)\-]?\s*([A-Za-z]+)", line, re.IGNORECASE)
            if m:
                idx = int(m.group(1))
                tag = m.group(2).upper()
                if tag.startswith('Y'):
                    labels[idx] = 'YES'
                elif tag.startswith('N'):
                    labels[idx] = 'NO'
                else:
                    labels[idx] = 'MAYBE'
            else:
                # 如果没有数字开头，尝试解析类似 "1 YES" 或包含 YES/NO 的行
                m2 = re.search(r"(YES|NO|MAYBE)", line, re.IGNORECASE)
                midx = re.search(r"^(\d+)", line)
                if midx and m2:
                    idx = int(midx.group(1))
                    tag = m2.group(1).upper()
                    labels[idx] = tag
        return labels
    except Exception as e:
        print(f"[WARNING] 标题级 DeepSeek 判定出错：{e}，使用关键词回退")
        for i, t in enumerate(titles, start=1):
            labels[i] = 'YES' if contains_keyword(t) else 'MAYBE'
        return labels


def classify_text_with_deepseek(text: str) -> str:
    """
    对单篇文章（标题+正文）进行判定，返回 'YES'/'NO'/'MAYBE'。
    DeepSeek 不可用时基于关键词回退。出错时返回 'MAYBE'。
    """
    if not text:
        return 'MAYBE'
    if not USE_DEEPSEEK or not openai_client:
        return 'YES' if contains_keyword(text) else 'MAYBE'
    try:
        prompt_text = text[:3000]
        system_prompt = (
            "你是一个简洁的三分类文本判断器。判断给定新闻标题与正文是否与零食、零售、连锁相关（包括英文词如 snack, retail, chain 等）。\n"
            "只返回一个单词：YES 表示相关，NO 表示不相关，MAYBE 表示不确定或无法判断。不要额外说明。"
        )
        resp = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=6,
            temperature=0
        )
        out = resp.choices[0].message.content.strip().upper()
        if out.startswith('Y') or 'YES' in out:
            return 'YES'
        if out.startswith('N') or 'NO' in out:
            return 'NO'
        return 'MAYBE'
    except Exception as e:
        print(f"[WARNING] 正文级 DeepSeek 判定出错：{e}")
        return 'MAYBE'

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 爬取网页正文 (用于 AI 分析，但不展示)
def fetch_article_text(url):
    try:
        print(f"[INFO] 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"[WARNING] 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"[ERROR] 文章爬取失败: {url}，错误: {e}")
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
            print(f"[WARNING] 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"[ERROR] 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取RSS内容并收集文章详情
def fetch_rss_articles(rss_feeds, max_articles=None):
    news_data = {}
    all_articles_with_details = []  # 收集所有筛选后的文章详情

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            print(f"[INFO] 正在获取 {source} 的 RSS 源: {url}")
            feed = fetch_feed_with_retry(url)
            if not feed:
                print(f"[WARNING] 无法获取 {source} 的 RSS 数据")
                continue
            print(f"[SUCCESS] {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

            # 两轮筛选：1) 标题编号批量判定；2) 对保留项抓取正文并二次判定
            if max_articles:
                entries = feed.entries[:max_articles]
            else:
                entries = feed.entries
            titles = [e.get('title', '无标题') for e in entries]
            title_labels = classify_titles_with_deepseek(titles)
            # 打印所有判定结果
            label_strs = [f"{i}:{title_labels.get(i)}" for i in sorted(title_labels.keys())]
            # 如果结果太多，分块打印，每行最多10个
            for i in range(0, len(label_strs), 10):
                chunk = label_strs[i:i+10]
                if i == 0:
                    print(f"[INFO] {source} 标题级判定: " + ", ".join(chunk))
                else:
                    print("   " + ", ".join(chunk))

            articles = []
            for idx, entry in enumerate(entries, start=1):
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                # 提取图片
                images = []
                # 尝试从RSS条目中获取图片
                if 'media_content' in entry:
                    for media in entry.get('media_content', []):
                        if media.get('url'):
                            images.append(media.get('url'))
                # 尝试从links中获取
                for link_item in entry.get('links', []):
                    if link_item.get('rel') == 'enclosure' or link_item.get('type', '').startswith('image'):
                        images.append(link_item.get('href', ''))
                # 尝试从summary中提取图片
                if summary and not images:
                    import re
                    img_matches = re.findall(r'<img[^>]+src="([^"]+)"', summary)
                    images.extend(img_matches)
                
                if not link:
                    print(f"[WARNING] {source} 的新闻 '{title}' 没有链接，跳过")
                    continue

                tlabel = title_labels.get(idx, 'MAYBE')
                if tlabel == 'NO':
                    print(f"[SKIP] 标题判定为非相关，跳过: [{idx}] {title}")
                    continue

                # 对保留项抓取正文并做二次判定
                article_text = fetch_article_text(link)
                check_text = f"{title}\n{article_text}"
                final_label = classify_text_with_deepseek(check_text)
                if final_label == 'NO':
                    print(f"[SKIP] 正文判定为非相关，移除: [{idx}] {title}")
                    continue

                # 保留（YES 或 MAYBE）
                article_detail = {
                    'title': title,
                    'link': link,
                    'content': article_text,
                    'source': source,
                    'category': category,
                    'images': images
                }
                all_articles_with_details.append(article_detail)
                print(f"[KEEP] {source} - [{idx}] {title} 保留 (标题判定={tlabel} -> 正文判定={final_label})")
                articles.append(f"- [{title}]({link})")

            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

        news_data[category] = category_content

    return news_data, all_articles_with_details

# AI 生成结构化内容（分析 + 重要新闻）
def generate_structured_content(articles_with_details):
    """
    使用 DeepSeek/OpenAI 生成结构化内容，包括分析摘要、详细新闻分析和最终总结
    
    Args:
        articles_with_details: 列表，每个元素是 {'title': 标题, 'link': 链接, 'content': 正文}
    
    Returns:
        {'summary': 总起摘要, 'important_articles': [{'title': 标题, 'link': 链接, ..., 'analysis': '详细分析内容'}], 'conclusion': '全文总结'}
    """
    try:
        if not USE_DEEPSEEK or not openai_client:
            # 回退
            important = articles_with_details[:5] if len(articles_with_details) > 5 else articles_with_details
            for article in important:
                article['analysis'] = ''
            return {
                'summary': "未配置 OPENAI_API_KEY，以下为相关文章。",
                'important_articles': important,
                'conclusion': "今日重点关注以上新闻。"
            }
        
        # 第一步：筛选重要新闻
        print("[INFO] 正在筛选重要新闻...")
        news_text = "\n\n".join([
            f"[{i+1}] 标题：{a['title']}\n内容：{a['content'][:600]}" 
            for i, a in enumerate(articles_with_details)
        ])
        
        completion1 = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": """
                 你是一名专业零食连锁零售行业的财经新闻分析师。请从提供的新闻中，选择5-8篇最重要的新闻，按重要性排序。
                 请用JSON格式输出，格式如下：
                 {
                     "important_articles": [1, 3, 5, 7, 8]
                 }
                 important_articles 数组中填入选中新闻的编号（例如[1,3,5]表示选第1、3、5篇）
                 """},
                {"role": "user", "content": news_text}
            ]
        )
        
        result1 = completion1.choices[0].message.content.strip()
        selected_indices = []
        json_match = re.search(r'\{[\s\S]*\}', result1)
        if json_match:
            import json
            try:
                data = json.loads(json_match.group())
                selected_indices = data.get('important_articles', [])
            except:
                pass
        
        if not selected_indices:
            selected_indices = list(range(1, min(6, len(articles_with_details)+1)))
        
        # 获取选中的文章
        important = []
        for idx in selected_indices:
            if 1 <= idx <= len(articles_with_details):
                important.append(articles_with_details[idx-1].copy())
        
        if len(important) < 3:
            important = articles_with_details[:min(5, len(articles_with_details))].copy()
        
        print(f"[INFO] 已筛选 {len(important)} 篇重要新闻")
        
        # 第二步：生成总起摘要和全文总结
        print("[INFO] 正在生成总起摘要和全文总结...")
        selected_news_text = "\n\n".join([
            f"[{i+1}] 标题：{a['title']}\n内容：{a['content'][:800]}" 
            for i, a in enumerate(important)
        ])
        
        completion2 = openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": """
                 你是一名专业零食连锁零售行业的财经新闻分析师。请根据提供的重要新闻完成：
                 1. 总起摘要：写一段300-500字的总起摘要，概括今日财经新闻的整体情况和重点
                 2. 全文总结：写一段200-300字的总结，对今日重点新闻进行收尾和展望
                 
                 请用JSON格式输出，格式如下：
                 {
                     "summary": "这里是总起摘要内容",
                     "conclusion": "这里是全文总结内容"
                 }
                 """},
                {"role": "user", "content": selected_news_text}
            ]
        )
        
        result2 = completion2.choices[0].message.content.strip()
        summary = ""
        conclusion = ""
        json_match2 = re.search(r'\{[\s\S]*\}', result2)
        if json_match2:
            try:
                data = json.loads(json_match2.group())
                summary = data.get('summary', '')
                conclusion = data.get('conclusion', '')
            except:
                pass
        
        # 第三步：为每篇重要新闻生成详细分析
        print("[INFO] 正在为每篇新闻生成详细分析...")
        for i, article in enumerate(important):
            print(f"  正在分析第 {i+1}/{len(important)} 篇...")
            article_content = f"标题：{article['title']}\n内容：{article['content']}"
            
            try:
                completion3 = openai_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": """
                         你是一名专业零食连锁零售行业的财经新闻分析师。请根据提供的这篇新闻，写一篇500-800字的分析，分为以下四个部分：
                         1. 背景介绍：介绍这篇新闻的背景和基本情况
                         2. 催化剂：分析近期上涨的可能原因（政策、数据、事件、情绪等）
                         3. 复盘：梳理过去3个月该行业/主题的核心逻辑、关键动态与阶段性走势
                         4. 展望：判断该热点是短期炒作还是有持续行情潜力
                         
                         请用纯文本输出，不要使用Markdown格式，不要使用*、#、-等符号，直接按四个部分分段写即可，每个部分作为一个段落。
                         """},
                        {"role": "user", "content": article_content}
                    ]
                )
                article['analysis'] = completion3.choices[0].message.content.strip()
            except Exception as e:
                print(f"    分析失败：{e}")
                article['analysis'] = ""
        
        print("[INFO] 分析完成！")
        
        return {
            'summary': summary,
            'important_articles': important,
            'conclusion': conclusion
        }
        
    except Exception as e:
        print(f"[ERROR] 生成结构化内容时出错：{e}")
        traceback.print_exc()
        important = articles_with_details[:min(5, len(articles_with_details))].copy()
        for article in important:
            article['analysis'] = ''
        return {
            'summary': "生成分析失败，以下为相关文章。",
            'important_articles': important,
            'conclusion': "今日重点关注以上新闻。"
        }

# 发送微信推送
def send_to_wechat(title, content):
    for key in server_chan_keys:
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        response = requests.post(url, data=data, timeout=10)
        if response.ok:
            print(f"[SUCCESS] 推送成功: {key}")
        else:
            print(f"[ERROR] 推送失败: {key}, 响应：{response.text}")


def set_font(run, font_name, font_size):
    """设置字体"""
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    run.font.size = Pt(font_size)

def download_image(url, save_path):
    """下载图片"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return save_path
    except Exception as e:
        print(f"[WARNING] 下载图片失败: {url}, 错误: {e}")
    return None

def generate_word_doc(today_str, structured_content, output_path):
    """生成美观的 Word 文档
    
    Args:
        today_str: 日期字符串
        structured_content: {'summary': 分析摘要, 'important_articles': [{'title': ..., 'link': ..., ...}]}
        output_path: 输出路径
    """
    doc = Document()
    
    # 设置默认字体
    doc.styles['Normal'].font.name = '宋体'
    doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    doc.styles['Normal'].font.size = Pt(10.5)  # 5号字
    # 设置段落间距
    doc.styles['Normal'].paragraph_format.line_spacing = 1.5
    
    # 1. 添加主标题
    title_para = doc.add_heading(f"{today_str} 财经新闻摘要", level=1)
    for run in title_para.runs:
        set_font(run, '宋体', 18)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)  # 深蓝色
    title_para.alignment = 1  # 居中
    title_para.paragraph_format.space_after = Pt(20)
    
    # 2. 添加总起摘要部分
    sec1_title = doc.add_heading('一、总起摘要', level=2)
    for run in sec1_title.runs:
        set_font(run, '宋体', 14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)
    
    # 分段处理摘要内容
    summary = structured_content.get('summary', '')
    for para_text in summary.split('\n'):
        if para_text.strip():
            p = doc.add_paragraph(para_text)
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.first_line_indent = Pt(21)  # 首行缩进2字符
            for run in p.runs:
                set_font(run, '宋体', 10.5)
                run.font.color.rgb = RGBColor(30, 30, 30)
    
    # 添加分隔线
    divider = doc.add_paragraph()
    divider.paragraph_format.space_before = Pt(20)
    divider.paragraph_format.space_after = Pt(20)
    from docx.oxml.shared import OxmlElement
    p = divider._element
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')  # 1/2 pt
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '0066CC')
    pBdr.append(bottom)
    pPr.append(pBdr)
    
    # 3. 添加新闻概览部分（详细分析）
    sec2_title = doc.add_heading('二、新闻概览', level=2)
    for run in sec2_title.runs:
        set_font(run, '宋体', 14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)
    sec2_title.paragraph_format.space_before = Pt(15)
    
    important_articles = structured_content.get('important_articles', [])
    temp_images = []
    
    for idx, article in enumerate(important_articles, start=1):
        # 新闻序号和标题（使用3级标题）
        news_title = f"{idx}. {article.get('title', '无标题')}"
        title_para = doc.add_heading(news_title, level=3)
        for run in title_para.runs:
            set_font(run, '黑体', 12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 68, 136)
        title_para.paragraph_format.space_before = Pt(15)
        title_para.paragraph_format.space_after = Pt(5)
        
        # 来源
        source = article.get('source', '未知来源')
        source_para = doc.add_paragraph()
        source_run = source_para.add_run(f"来源：{source}")
        set_font(source_run, '楷体', 10)
        source_run.font.color.rgb = RGBColor(100, 100, 100)
        
        # 添加详细分析内容
        analysis = article.get('analysis', '')
        if analysis:
            for para_text in analysis.split('\n'):
                if para_text.strip():
                    p = doc.add_paragraph(para_text)
                    p.paragraph_format.line_spacing = 1.5
                    p.paragraph_format.first_line_indent = Pt(21)
                    for run in p.runs:
                        set_font(run, '宋体', 10.5)
                        run.font.color.rgb = RGBColor(30, 30, 30)
        
        # 尝试添加图片
        images = article.get('images', [])
        if images:
            img_url = images[0]
            temp_path = os.path.join(os.path.dirname(output_path), f"temp_img_{idx}.jpg")
            downloaded = download_image(img_url, temp_path)
            if downloaded:
                temp_images.append(downloaded)
                img_para = doc.add_paragraph()
                try:
                    run_img = img_para.add_run()
                    run_img.add_picture(downloaded, width=Pt(300))  # 限制宽度
                    img_para.alignment = 1  # 居中
                    img_para.paragraph_format.space_before = Pt(8)
                    img_para.paragraph_format.space_after = Pt(8)
                except Exception as e:
                    print(f"[WARNING] 添加图片失败: {e}")
        
        # 链接 - 更美观的样式
        link = article.get('link', '')
        if link:
            link_para = doc.add_paragraph()
            label_run = link_para.add_run('阅读全文：')
            set_font(label_run, '宋体', 10)
            label_run.font.italic = True
            label_run.font.color.rgb = RGBColor(100, 100, 100)
            
            link_run = link_para.add_run(link)
            link_run.font.color.rgb = RGBColor(0, 102, 204)
            link_run.font.underline = True
            link_run.font.name = 'Courier New'  # 链接用等宽字体
            link_run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Courier New')
            link_run.font.size = Pt(9)
        
        # 添加空行分隔
        spacer = doc.add_paragraph('')
        spacer.paragraph_format.space_after = Pt(10)
    
    # 添加分隔线
    divider2 = doc.add_paragraph()
    divider2.paragraph_format.space_before = Pt(15)
    p2 = divider2._element
    pPr2 = p2.get_or_add_pPr()
    pBdr2 = OxmlElement('w:pBdr')
    top2 = OxmlElement('w:top')
    top2.set(qn('w:val'), 'single')
    top2.set(qn('w:sz'), '4')
    top2.set(qn('w:space'), '1')
    top2.set(qn('w:color'), '0066CC')
    pBdr2.append(top2)
    pPr2.append(pBdr2)
    
    # 4. 添加全文总结部分
    sec3_title = doc.add_heading('三、全文总结', level=2)
    for run in sec3_title.runs:
        set_font(run, '宋体', 14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102)
    sec3_title.paragraph_format.space_before = Pt(15)
    
    conclusion = structured_content.get('conclusion', '')
    for para_text in conclusion.split('\n'):
        if para_text.strip():
            p = doc.add_paragraph(para_text)
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.first_line_indent = Pt(21)
            for run in p.runs:
                set_font(run, '宋体', 10.5)
                run.font.color.rgb = RGBColor(30, 30, 30)
    
    doc.save(output_path)
    
    # 清理临时图片
    for img in temp_images:
        try:
            os.remove(img)
        except:
            pass
    
    print(f"[SUCCESS] Word 文档已生成: {output_path}")
    return output_path

def send_email_with_attachment(subject, body, attachment_path, recipient_emails=None):
    """发送带附件的邮件
    
    Args:
        subject: 邮件主题
        body: 邮件正文
        attachment_path: 附件路径
        recipient_emails: 收件人邮箱列表（单个字符串或多个邮箱的列表）
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[WARNING] 未配置 SMTP_USER 或 SMTP_PASSWORD，跳过邮件发送")
        return False
    
    # 如果没有指定收件人，使用默认配置
    if recipient_emails is None:
        recipient_emails = RECIPIENT_EMAILS
    # 如果是单个字符串，转换为列表
    elif isinstance(recipient_emails, str):
        recipient_emails = [email.strip() for email in recipient_emails.split(",") if email.strip()]
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = ", ".join(recipient_emails)
        msg['Subject'] = subject
        
        # 添加邮件正文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加附件
        with open(attachment_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)
        
        # 发送邮件
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"[OK] 邮件已成功发送到: {', '.join(recipient_emails)}")
        return True
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")
        traceback.print_exc()
        return False

def run_task():
    """执行完整任务"""
    print("=" * 50)
    print(f"开始执行任务: {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    today_str = today_date().strftime("%Y-%m-%d")
    
    # 1. 获取并处理新闻
    articles_data, all_articles = fetch_rss_articles(rss_feeds)
    
    # 2. AI 生成结构化内容（分析 + 重要新闻筛选）
    structured_content = generate_structured_content(all_articles)
    summary = structured_content.get('summary', '')
    
    # 3. 生成 Word 文档
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    word_path = os.path.join(output_dir, f"{today_str}_财经新闻摘要.docx")
    generate_word_doc(today_str, structured_content, word_path)
    
    # 4. 发送邮件
    email_subject = f"{today_str} 财经新闻摘要"
    email_body = f"附件是 {today_str} 的财经新闻摘要文档。\n\n今日分析总结：\n{summary}"
    send_email_with_attachment(email_subject, email_body, word_path, RECIPIENT_EMAILS)
    
    # 5. 推送到 Server酱（保留原有功能）
    final_summary = f"{today_str} 财经新闻摘要\n\n今日分析总结：\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"{category}\n{content}\n\n"
    send_to_wechat(title=f"{today_str} 财经新闻摘要", content=final_summary)
    
    print("=" * 50)
    print("任务完成！")

def start_http_server():
    """启动简单的HTTP服务器用于手动触发任务"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = """
                <html>
                <head>
                    <title>财经新闻采集机器人</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: "Microsoft YaHei", Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                        h1 { color: #333; }
                        .btn { background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-size: 18px; margin: 20px 0; }
                        .btn:hover { background: #0056b3; }
                        .info { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    </style>
                </head>
                <body>
                    <h1>财经新闻采集机器人</h1>
                    <div class="info">
                        <p><strong>定时任务时间：</strong>""" + SCHEDULE_TIME + """</p>
                        <p><strong>收件人：</strong>""" + ', '.join(RECIPIENT_EMAILS) + """</p>
                    </div>
                    <a href="/run" class="btn">立即执行一次任务</a>
                    <p>点击按钮后，程序将立即采集新闻、生成Word文档并发送邮件。</p>
                </body>
                </html>
                """.encode('utf-8')
                self.wfile.write(html)
            elif parsed_path.path == '/run':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = """
                <html>
                <head>
                    <title>任务执行中</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: "Microsoft YaHei", Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                        .loading { color: #007bff; font-size: 20px; }
                    </style>
                </head>
                <body>
                    <h1>任务执行中...</h1>
                    <p class="loading">正在后台执行，请稍候... 任务完成后将自动发送邮件。</p>
                    <p><a href="/">返回首页</a></p>
                </body>
                </html>
                """.encode('utf-8')
                self.wfile.write(html)
                # 在后台执行任务
                import threading
                task_thread = threading.Thread(target=run_task)
                task_thread.start()
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not Found')
        
        def log_message(self, format, *args):
            # 简化日志输出
            print(f"[HTTP] {self.address_string()} - {format % args}")
    
    try:
        server = HTTPServer(('0.0.0.0', HTTP_PORT), Handler)
        print(f"\n[INFO] HTTP服务已启动: http://localhost:{HTTP_PORT}")
        print(f"[INFO] 浏览器打开上述地址，点击按钮可手动触发推送")
        return server
    except Exception as e:
        print(f"[WARNING] HTTP服务启动失败: {e}")
        return None

if __name__ == "__main__":
    import argparse
    import threading
    parser = argparse.ArgumentParser(description='财经新闻采集机器人')
    parser.add_argument('--once', action='store_true', help='立即执行一次任务，不启动定时模式')
    parser.add_argument('--now', action='store_true', help='立即执行一次任务，然后退出')
    args = parser.parse_args()
    
    if args.once or args.now:
        print("[INFO] 单次执行模式")
        run_task()
    else:
        print(f"[INFO] 定时任务模式，将在每天 {SCHEDULE_TIME} 执行")
        print("按 Ctrl+C 退出程序")
        
        # 启动HTTP服务（如果启用）
        http_server = None
        if ENABLE_HTTP:
            http_server = start_http_server()
        
        # 设置定时任务
        schedule.every().day.at(SCHEDULE_TIME).do(run_task)
        
        # 立即执行一次
        print("\n立即执行第一次任务...")
        run_task()
        
        # 主循环
        try:
            if http_server:
                # 使用HTTP服务的循环
                http_server.serve_forever()
            else:
                # 使用简单的定时循环
                while True:
                    schedule.run_pending()
                    time.sleep(60)
        except KeyboardInterrupt:
            if http_server:
                http_server.shutdown()
            print("\n程序已停止")
