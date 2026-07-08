#!/usr/bin/env python3
"""选题池日报推送飞书

聚合多个热榜/论坛的当日热门标题（标题 + 原文链接 + 来源），推到独立的飞书群，
作为公众号选题池的每日素材来源。与 AI HOT 日报（send_daily.py）互不影响。

数据源：Hacker News / V2EX / 掘金热榜 / 知乎热榜 / 微博热搜 / Reddit / AI HOT。
单个源抓取失败不影响其余源，失败的源会在卡片底部标注。
"""

import os
import time
import requests
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
AIHOT_BASE = "https://aihot.virxact.com"
WEBHOOK_URL = os.environ.get("XUANTI_FEISHU_WEBHOOK_URL")
TIMEOUT = 15


def fetch_hackernews(limit=10):
    ids = requests.get(
        "https://hacker-news.firebaseio.com/v0/topstories.json",
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()[:limit]
    items = []
    for sid in ids:
        it = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
            headers={"User-Agent": UA}, timeout=TIMEOUT,
        ).json()
        if not it or not it.get("title"):
            continue
        url = it.get("url") or f"https://news.ycombinator.com/item?id={sid}"
        items.append((it["title"], url))
    return items


def fetch_v2ex(limit=10):
    data = requests.get(
        "https://www.v2ex.com/api/topics/hot.json",
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()
    return [(t["title"], t["url"]) for t in data[:limit]]


def fetch_juejin(limit=10):
    data = requests.get(
        "https://api.juejin.cn/content_api/v1/content/article_rank",
        params={"category_id": "1", "type": "hot"},
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()
    items = []
    for entry in data.get("data", [])[:limit]:
        content = entry.get("content", {})
        title = content.get("title")
        cid = content.get("content_id")
        if title and cid:
            items.append((title, f"https://juejin.cn/post/{cid}"))
    return items


def fetch_zhihu(limit=10):
    # 移动端热榜接口，无需登录；若知乎调整接口此源会失败并被标注
    data = requests.get(
        "https://api.zhihu.com/topstory/hot-list",
        params={"limit": limit},
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()
    items = []
    for entry in data.get("data", [])[:limit]:
        target = entry.get("target", {})
        title = target.get("title")
        qid = target.get("id")
        if title and qid:
            items.append((title, f"https://www.zhihu.com/question/{qid}"))
    return items


def fetch_weibo(limit=15):
    # 微博官方接口已全面要求 visitor cookie，改走开源聚合项目 60s（vikiboss/60s）
    data = requests.get(
        "https://60s.viki.moe/v2/weibo",
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()
    items = []
    for entry in data.get("data", [])[:limit]:
        title = entry.get("title")
        link = entry.get("link")
        if title and link:
            items.append((title, link))
    return items


def fetch_reddit(limit=12):
    # 多板块合并热帖；Reddit 对云厂商 IP 偶尔 403，失败会被标注
    data = requests.get(
        "https://www.reddit.com/r/ChatGPT+LocalLLaMA+ClaudeAI+artificial/hot.json",
        params={"limit": limit},
        headers={"User-Agent": f"{UA} xuanti-bot/1.0"}, timeout=TIMEOUT,
    ).json()
    items = []
    for child in data.get("data", {}).get("children", [])[:limit]:
        post = child.get("data", {})
        title = post.get("title")
        permalink = post.get("permalink")
        sub = post.get("subreddit")
        if title and permalink:
            items.append((f"[r/{sub}] {title}", f"https://www.reddit.com{permalink}"))
    return items


def fetch_aihot(limit=8):
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = requests.get(
        f"{AIHOT_BASE}/api/public/items",
        params={"mode": "selected", "since": since, "take": limit},
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    ).json()
    items = []
    for it in data.get("items", []):
        url = it.get("sourceUrl") or AIHOT_BASE
        items.append((it["title"], url))
    return items


SOURCES = [
    ("🔥 微博热搜", fetch_weibo),
    ("💬 知乎热榜", fetch_zhihu),
    ("🤖 AI HOT 精选", fetch_aihot),
    ("🧑‍💻 V2EX 热议", fetch_v2ex),
    ("⛏️ 掘金热榜", fetch_juejin),
    ("🌐 Hacker News", fetch_hackernews),
    ("👽 Reddit AI 板块", fetch_reddit),
]


def build_card(results, failed):
    date = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    elements = [{
        "tag": "markdown",
        "content": f"📮 **选题池日报 · {date}**\n扫一眼，心动的丢进选题池，不筛选、不展开。",
    }]

    for label, items in results:
        if not items:
            continue
        elements.append({"tag": "hr"})
        lines = [f"**{label}**"]
        for idx, (title, url) in enumerate(items):
            safe_url = url.replace(")", "%29")
            lines.append(f"{idx + 1}. [{title}]({safe_url})")
        elements.append({"tag": "markdown", "content": "\n".join(lines)})

    if failed:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": f"⚠️ 今日抓取失败的源：{'、'.join(failed)}",
        })

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📮 选题池日报 · {date}"},
                "template": "green",
            },
            "elements": elements,
        },
    }


# 飞书频控类错误码，遇到这些就退避重试（与 send_daily.py 保持一致）
FREQ_LIMIT_CODES = {11232, 9499}
MAX_RETRIES = 3
BACKOFF_SECONDS = [5, 10, 20]


def send_feishu(message):
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(WEBHOOK_URL, json=message, timeout=TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            code = result.get("code")
            if code == 0:
                return
            if code in FREQ_LIMIT_CODES and attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECONDS[attempt]
                print(f"⚠️ 飞书频控 {code}，{wait}s 后重试（第 {attempt + 1}/{MAX_RETRIES} 次）")
                time.sleep(wait)
                last_err = Exception(f"飞书 API 错误: {result}")
                continue
            raise Exception(f"飞书 API 错误: {result}")
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECONDS[attempt]
                print(f"⚠️ 请求异常 {e}，{wait}s 后重试（第 {attempt + 1}/{MAX_RETRIES} 次）")
                time.sleep(wait)
                last_err = e
                continue
            raise
    if last_err:
        raise last_err


def main():
    if not WEBHOOK_URL:
        raise ValueError("环境变量 XUANTI_FEISHU_WEBHOOK_URL 未设置")

    results, failed = [], []
    for label, fetcher in SOURCES:
        try:
            items = fetcher()
            results.append((label, items))
            print(f"✅ {label}: {len(items)} 条")
        except Exception as e:
            failed.append(label)
            print(f"⚠️ {label} 抓取失败: {e}")

    if not any(items for _, items in results):
        raise Exception("所有数据源均抓取失败，放弃推送")

    send_feishu(build_card(results, failed))
    print("✅ 选题池日报已推送")


if __name__ == "__main__":
    main()
