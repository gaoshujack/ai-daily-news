#!/usr/bin/env python3
"""
AI 行业日报自动生成脚本
使用 Tavily 搜索中文资讯，无需 OpenAI 也能生成格式良好的日报
"""

import os
import json
import datetime
import requests
from pathlib import Path

SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TODAY = datetime.date.today().strftime("%Y-%m-%d")
DATE_CN = datetime.datetime.strptime(TODAY, "%Y-%m-%d").strftime("%Y年%m月%d日")
NEWS_DIR = Path("news")
INDEX_FILE = NEWS_DIR / "index.json"

# 中文搜索关键词，按分类
SEARCH_QUERIES = [
    {"q": f"OpenAI GPT 最新动态 {TODAY}", "section": "OpenAI", "badge": "badge-openai", "card": ""},
    {"q": f"Anthropic Claude 最新消息 {TODAY}", "section": "Anthropic", "badge": "badge-anthropic", "card": ""},
    {"q": f"xAI Grok 马斯克 AI {TODAY}", "section": "xAI · Grok", "badge": "badge-xai", "card": "grok"},
    {"q": f"Google Gemini 最新动态 {TODAY}", "section": "Google Gemini", "badge": "badge-google", "card": ""},
    {"q": f"DeepSeek 字节跳动 阿里 国内AI大模型 {TODAY}", "section": "国内 AI", "badge": "badge-cn", "card": "cn"},
]

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def get_weekday():
    return WEEKDAYS[datetime.date.today().weekday()]

def search(query: str) -> list:
    if not SEARCH_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": SEARCH_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 4,
                "days": 2,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"  搜索失败 [{query[:30]}]: {e}")
        return []

def clean_title(title: str) -> str:
    """清理标题，去掉网站名等噪音"""
    for sep in [" | ", " - ", " – ", " — ", "｜"]:
        if sep in title:
            parts = title.split(sep)
            # 取最长的部分
            title = max(parts, key=len).strip()
    return title[:80]

def clean_summary(text: str, max_len=150) -> str:
    """截取摘要"""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text[:max_len] + "..." if len(text) > max_len else text

def render_card(item: dict, badge_class: str, card_class: str) -> str:
    title = clean_title(item.get("title", ""))
    summary = clean_summary(item.get("content", ""))
    url = item.get("url", "#")
    published = item.get("published_date", "")[:10] or "今日"

    if not title or not summary:
        return ""

    # 从 URL 提取来源域名
    try:
        from urllib.parse import urlparse
        source = urlparse(url).netloc.replace("www.", "")
    except Exception:
        source = ""

    return f'''
            <div class="news-card {card_class}">
                <div class="news-card-top">
                    <span class="company-badge {badge_class}">{source}</span>
                    <span class="news-time">{published}</span>
                </div>
                <h2>{title}</h2>
                <div class="summary">{summary}</div>
                <a href="{url}" class="source-link" target="_blank">阅读原文 →</a>
            </div>'''

def render_section(section_title: str, icon: str, icon_class: str,
                   items: list, badge_class: str, card_class: str) -> str:
    cards_html = ""
    count = 0
    for item in items:
        card = render_card(item, badge_class, card_class)
        if card:
            cards_html += card
            count += 1
    if count == 0:
        return ""
    return f'''
        <div class="section">
            <div class="section-header">
                <div class="section-icon {icon_class}">{icon}</div>
                <div class="section-title">{section_title}</div>
                <span class="section-count">{count} 条资讯</span>
            </div>
            <div class="news-grid">{cards_html}
            </div>
        </div>'''

def generate_html(sections_data: list) -> str:
    total = sum(len(s["results"]) for s in sections_data)
    weekday = get_weekday()

    sections_html = ""
    for s in sections_data:
        if not s["results"]:
            continue
        icon_class = "cn" if s["card"] == "cn" else "us"
        icon = "🇨🇳" if s["card"] == "cn" else ("🔍" if "Gemini" in s["section"] else "🇺🇸")
        sections_html += render_section(
            s["section"], icon, icon_class,
            s["results"], s["badge"], s["card"]
        )

    return f'''<div class="container">
    <div class="header">
        <div class="header-content">
            <div class="header-badge">🌐 GLOBAL AI INTELLIGENCE REPORT</div>
            <h1>🤖 全球AI行业资讯日报</h1>
            <div class="subtitle">聚焦 OpenAI · Anthropic · Google Gemini · xAI Grok · 国内大模型</div>
            <div class="date">{DATE_CN} {weekday} · 精选今日最重磅动态</div>
        </div>
    </div>
    <div class="stats-bar">
        <div class="stat-item"><span class="stat-number">{total}</span><span class="stat-label">精选资讯</span></div>
        <div class="stat-item"><span class="stat-number">5</span><span class="stat-label">重点企业</span></div>
        <div class="stat-item"><span class="stat-number">24h</span><span class="stat-label">时效范围</span></div>
    </div>
    <div class="content">{sections_html}
    </div>
    <div class="footer">
        <p>🤖 由 <strong>WorkBuddy</strong> 智能整理生成 · 数据来源于 Tavily 实时搜索</p>
        <p>本报告仅供参考，不构成任何投资建议 · 信息截止时间：{DATE_CN}</p>
    </div>
</div>'''

def update_index():
    data = {"latest": "", "dates": []}
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            data = json.load(f)
    if TODAY not in data["dates"]:
        data["dates"].insert(0, TODAY)
    data["latest"] = data["dates"][0]
    with open(INDEX_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 更新 index.json，共 {len(data['dates'])} 天")

def main():
    print(f"📅 开始生成 {TODAY} 日报...")
    NEWS_DIR.mkdir(exist_ok=True)

    sections_data = []
    for q in SEARCH_QUERIES:
        print(f"  🔍 搜索：{q['q']}")
        results = search(q["q"])
        print(f"     获取 {len(results)} 条")
        sections_data.append({**q, "results": results})

    html = generate_html(sections_data)
    out = NEWS_DIR / f"{TODAY}.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 已写入 {out}（{len(html)} 字节）")

    update_index()
    print("🎉 完成！")

if __name__ == "__main__":
    main()
