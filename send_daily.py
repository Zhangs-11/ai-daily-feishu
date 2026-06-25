#!/usr/bin/env python3
"""AI HOT 日报推送飞书"""

import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE = "https://aihot.virxact.com"
WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")


def fetch_daily():
    resp = requests.get(f"{BASE}/api/public/daily", headers={"User-Agent": UA})
    resp.raise_for_status()
    return resp.json()


def fetch_items(mode="selected", since_hours=72, take=50):
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = requests.get(
        f"{BASE}/api/public/items",
        headers={"User-Agent": UA},
        params={"mode": mode, "since": since, "take": take},
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def build_daily_card(data):
    """日报卡片"""
    date = data["date"]
    sections = data.get("sections", [])
    elements = [
        {
            "tag": "markdown",
            "content": f"🌅 **AI HOT 日报 · {date}**\n数据来源：aihot.virxact.com",
        }
    ]

    for section in sections:
        label = section["label"]
        items = section.get("items", [])
        if not items:
            continue

        elements.append({"tag": "hr"})
        lines = [f"**{label}**"]
        for idx, item in enumerate(items):
            summary = item.get("summary", "")
            line = f"{idx+1}. **{item['title']}** — {item['sourceName']}"
            if summary:
                summary_short = summary[:100] + ("..." if len(summary) > 100 else "")
                line += f"\n{summary_short}"
            if item.get("sourceUrl"):
                markdown_url = item["sourceUrl"].replace(")", "%29")
                line += f"\n[🔗 原文]({markdown_url})"
            lines.append(line)
        elements.append({"tag": "markdown", "content": "\n\n".join(lines)})

    if not elements:
        elements.append({"tag": "markdown", "content": "今日暂无内容"})

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🤖 AI HOT 日报 · {date}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def build_summary_card(items):
    """周一近三日汇总卡片"""
    elements = [
        {
            "tag": "markdown",
            "content": "📊 **近三日 AI 动态汇总**（周一特供）\n过去 3 天 AI 圈重要动态一览。",
        }
    ]

    category_map = {
        "ai-models": "模型发布/更新",
        "ai-products": "产品发布/更新",
        "industry": "行业动态",
        "paper": "论文研究",
        "tip": "技巧与观点",
    }

    grouped = {}
    for item in items:
        cat = item.get("category") or "industry"
        grouped.setdefault(cat, []).append(item)

    global_idx = 0
    for cat_slug, cat_name in category_map.items():
        cat_items = grouped.get(cat_slug, [])
        if not cat_items:
            continue
        elements.append({"tag": "hr"})
        lines = [f"**{cat_name}**"]
        for item in cat_items[:8]:  # 每类最多8条，避免炸消息
            global_idx += 1
            summary = item.get("summary", "")
            line = f"{global_idx}. **{item['title']}** — {item['source']}"
            if summary:
                summary_short = summary[:80] + ("..." if len(summary) > 80 else "")
                line += f"\n{summary_short}"
            if item.get("url"):
                markdown_url = item["url"].replace(")", "%29")
                line += f"\n[🔗 原文]({markdown_url})"
            lines.append(line)
        elements.append({"tag": "markdown", "content": "\n\n".join(lines)})

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📊 近三日 AI 动态汇总"},
                "template": "indigo",
            },
            "elements": elements,
        },
    }


# 飞书频控类错误码，遇到这些就退避重试（11232 / 9499 都是 frequency limited）
FREQ_LIMIT_CODES = {11232, 9499}
MAX_RETRIES = 3
BACKOFF_SECONDS = [5, 10, 20]


def send_feishu(message):
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(WEBHOOK_URL, json=message, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            code = result.get("code")
            if code == 0:
                return
            # 频控错误：退避后重试；其它业务错误直接抛
            if code in FREQ_LIMIT_CODES and attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECONDS[attempt]
                print(f"⚠️ 飞书频控 {code}，{wait}s 后重试（第 {attempt + 1}/{MAX_RETRIES} 次）")
                time.sleep(wait)
                last_err = Exception(f"飞书 API 错误: {result}")
                continue
            raise Exception(f"飞书 API 错误: {result}")
        except requests.RequestException as e:
            # 网络/超时类错误也退避重试
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
        raise ValueError("环境变量 FEISHU_WEBHOOK_URL 未设置")

    # 推日报
    daily = fetch_daily()
    card = build_daily_card(daily)
    send_feishu(card)
    print(f"✅ 日报 {daily['date']} 已推送")

    # 周一额外推近三日汇总
    now_bj = datetime.now(timezone.utc) + timedelta(hours=8)
    if now_bj.weekday() == 0:
        items = fetch_items(since_hours=72)
        summary = build_summary_card(items)
        send_feishu(summary)
        print(f"✅ 周一汇总已推送（共 {len(items)} 条）")


if __name__ == "__main__":
    main()
