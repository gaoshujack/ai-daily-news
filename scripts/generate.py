#!/usr/bin/env python3
"""
AI 行业日报自动生成脚本
每天由 GitHub Actions 自动触发，搜索最新资讯并生成 HTML 片段
"""

import os
import json
import datetime
import requests
from pathlib import Path

# ── 配置 ──
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TODAY = datetime.date.today().strftime("%Y-%m-%d")
NEWS_DIR = Path("news")
INDEX_FILE = NEWS_DIR / "index.json"

SEARCH_QUERIES = [
    "OpenAI GPT latest news today",
    "Anthropic Claude latest news today",
    "xAI Grok latest news today",
    "Google Gemini latest news today",
    "中国AI大模型 DeepSeek 字节跳动 阿里 最新动态",
]

# ── 搜索资讯（Tavily API）──
def search_news(query: str) -> list[dict]:
    if not SEARCH_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": SEARCH_API_KEY, "query": query,
                  "search_depth": "basic", "max_results": 5,
                  "days": 1},
            timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"搜索失败 [{query}]: {e}")
        return []

# ── 调用 OpenAI 生成摘要和 HTML ──
def generate_html_with_llm(raw_results: list[dict]) -> str:
    if not OPENAI_API_KEY:
        return generate_html_fallback(raw_results)
    
    context = "\n\n".join(
        f"标题: {r.get('title','')}\n来源: {r.get('url','')}\n摘要: {r.get('content','')[:300]}"
        for r in raw_results[:15]
    )
    
    prompt = f"""你是一个AI行业资讯编辑，今天是 {TODAY}。
以下是今日搜集的原始资讯，请：
1. 筛选出8-12条最有价值的资讯
2. 按公司分类：OpenAI、Anthropic、Google Gemini、xAI Grok、国内AI
3. 为每条资讯生成50-80字中文摘要
4. 输出严格的 JSON 格式，结构如下：
{{
  "sections": [
    {{
      "title": "OpenAI 动态",
      "icon": "🇺🇸",
      "items": [
        {{
          "company": "OpenAI",
          "badge_class": "badge-openai",
          "title": "新闻标题",
          "tags": ["标签1", "标签2"],
          "summary": "新闻摘要",
          "highlight": "核心要点（可选）",
          "url": "原文链接",
          "time": "时间"
        }}
      ]
    }}
  ]
}}

原始资讯：
{context}
"""
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.3
            },
            timeout=60
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        return render_html(data)
    except Exception as e:
        print(f"LLM 生成失败: {e}")
        return generate_html_fallback(raw_results)

# ── 将结构化数据渲染为 HTML ──
def render_html(data: dict) -> str:
    sections_html = ""
    total = sum(len(s.get("items", [])) for s in data.get("sections", []))

    for section in data.get("sections", []):
        items_html = ""
        for item in section.get("items", []):
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in item.get("tags", []))
            highlight_html = ""
            if item.get("highlight"):
                highlight_html = f'''
                <div class="highlights">
                    <h4>核心亮点</h4>
                    <p>{item["highlight"]}</p>
                </div>'''
            items_html += f'''
            <div class="news-card">
                <div class="news-card-top">
                    <span class="company-badge {item.get('badge_class','')}">{item.get('company','')}</span>
                    <span class="news-time">{item.get('time','今日')}</span>
                </div>
                <h2>{item.get('title','')}</h2>
                <div class="tags">{tags_html}</div>
                <div class="summary">{item.get('summary','')}</div>
                {highlight_html}
                <a href="{item.get('url','#')}" class="source-link" target="_blank">阅读原文 →</a>
            </div>'''

        sections_html += f'''
        <div class="section">
            <div class="section-header">
                <div class="section-icon">{section.get('icon','📰')}</div>
                <div class="section-title">{section.get('title','')}</div>
                <span class="section-count">{len(section.get('items',[]))} 条资讯</span>
            </div>
            <div class="news-grid">{items_html}</div>
        </div>'''

    date_cn = datetime.datetime.strptime(TODAY, "%Y-%m-%d").strftime("%Y年%m月%d日")
    return f'''<div class="container">
    <div class="header">
        <div class="header-content">
            <div class="header-badge">🌐 GLOBAL AI INTELLIGENCE REPORT</div>
            <h1>🤖 全球AI行业资讯日报</h1>
            <div class="subtitle">聚焦 OpenAI · Anthropic · Google Gemini · xAI Grok · 国内大模型</div>
            <div class="date">{date_cn} · 精选今日最重磅动态</div>
        </div>
    </div>
    <div class="stats-bar">
        <div class="stat-item"><span class="stat-number">{total}</span><span class="stat-label">精选资讯</span></div>
        <div class="stat-item"><span class="stat-number">5</span><span class="stat-label">重点企业</span></div>
        <div class="stat-item"><span class="stat-number">24h</span><span class="stat-label">时效范围</span></div>
    </div>
    <div class="content">{sections_html}</div>
    <div class="footer">
        <p>🤖 由 <strong>WorkBuddy</strong> 智能整理生成 · 数据来源于新浪财经、东方财富、IT之家、腾讯新闻等权威媒体</p>
        <p>本报告仅供参考，不构成任何投资建议 · 信息截止时间：{date_cn}</p>
    </div>
</div>'''

# ── 无 API Key 时的降级处理 ──
def generate_html_fallback(raw_results: list[dict]) -> str:
    date_cn = datetime.datetime.strptime(TODAY, "%Y-%m-%d").strftime("%Y年%m月%d日")
    items_html = ""
    for r in raw_results[:10]:
        items_html += f'''
        <div class="news-card">
            <div class="news-card-top">
                <span class="company-badge badge-industry">AI资讯</span>
                <span class="news-time">今日</span>
            </div>
            <h2>{r.get('title','')}</h2>
            <div class="summary">{r.get('content','')[:200]}...</div>
            <a href="{r.get('url','#')}" class="source-link" target="_blank">阅读原文 →</a>
        </div>'''

    return f'''<div class="container">
    <div class="header">
        <div class="header-content">
            <div class="header-badge">🌐 GLOBAL AI INTELLIGENCE REPORT</div>
            <h1>🤖 全球AI行业资讯日报</h1>
            <div class="date">{date_cn}</div>
        </div>
    </div>
    <div class="content">
        <div class="section">
            <div class="section-header">
                <div class="section-icon">📰</div>
                <div class="section-title">今日 AI 资讯</div>
            </div>
            <div class="news-grid">{items_html}</div>
        </div>
    </div>
</div>'''

# ── 更新 index.json ──
def update_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            data = json.load(f)
    else:
        data = {"latest": "", "dates": []}

    if TODAY not in data["dates"]:
        data["dates"].insert(0, TODAY)
    data["latest"] = data["dates"][0]

    with open(INDEX_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 更新 index.json，当前共 {len(data['dates'])} 天")

# ── 主流程 ──
def main():
    print(f"📅 开始生成 {TODAY} 日报...")
    NEWS_DIR.mkdir(exist_ok=True)

    # 搜索资讯
    all_results = []
    for q in SEARCH_QUERIES:
        print(f"  🔍 搜索：{q}")
        all_results.extend(search_news(q))
    print(f"  📥 共获取 {len(all_results)} 条原始资讯")

    # 生成 HTML
    html = generate_html_with_llm(all_results)

    # 写入文件
    out_file = NEWS_DIR / f"{TODAY}.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 已写入 {out_file}")

    # 更新索引
    update_index()
    print("🎉 日报生成完成！")

if __name__ == "__main__":
    main()
