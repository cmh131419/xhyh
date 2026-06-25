#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成静态文章页和案例页，供搜索引擎和AI爬虫直接抓取
每个页面首屏HTML包含完整内容、唯一title/description/canonical/JSON-LD
"""

import json
import os
import re
from datetime import date

# ── 配置 ────────────────────────────────────────────────────────────────────
ARTICLES_JSON = "data/articles.json"
CASES_JSON    = "data/cases.json"
OUTPUT_DIR    = "."   # 静态文件输出到根目录
DOMAIN        = "https://xhyh.work"

# ── 工具函数 ─────────────────────────────────────────────────────────────────

def markdown_to_html(text: str) -> str:
    """将文章 content 字段（markdown风格）转为静态HTML"""
    # 已经是HTML片段的就直接返回（content里已有 <p> <h3> 等标签）
    # 只处理纯文本段落：用 <p> 包裹没有标签的行
    lines = text.split("\n")
    out = []
    buf = []
    for line in lines:
        stripped = line.strip()
        # 已经是HTML标签开头，刷新缓冲区
        if stripped.startswith(("<p", "<h", "<table", "<tr", "<td", "<th", "<ul", "<ol", "<li",
                               "<div", "<span", "<a ", "<strong", "<em", "<code", "<pre",
                               "<blockquote", "<hr", "<br", "<!--", "</")):
            if buf:
                para = " ".join(buf).strip()
                if para:
                    out.append(f"<p>{para}</p>")
                buf = []
            out.append(line)
        elif stripped == "":
            if buf:
                para = " ".join(buf).strip()
                if para:
                    out.append(f"<p>{para}</p>")
                buf = []
            out.append("")
        else:
            buf.append(stripped)
    if buf:
        para = " ".join(buf).strip()
        if para:
            out.append(f"<p>{para}</p>")
    return "\n".join(out)


def build_article_html(article: dict) -> str:
    """为单篇文章生成完整静态HTML"""
    aid       = article["id"]
    title     = article["title"]
    category  = article["category"]
    date_str  = article["date"]
    summary   = article["summary"]
    tags      = ", ".join(article.get("tags", []))
    content   = markdown_to_html(article.get("content", ""))

    page_title   = f"{title} | 星禾元亨 · AI自动化"
    page_desc    = summary[:120] + ("..." if len(summary) > 120 else "")
    canonical    = f"{DOMAIN}/article-{aid}.html"
    og_image     = f"{DOMAIN}/images/og-image.png"

    # FAQ 数据（从文章内容提取，或生成通用FAQ）
    faq_schema = build_faq_schema(article)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{page_title}</title>
<meta name="description" content="{page_desc}" />
<meta name="keywords" content="{tags},{category},星禾元亨,AI自动化" />
<link rel="canonical" href="{canonical}" />
<meta name="google-site-verification" content="X4GB4L_W_sGID3pymBNODfn6bTX2UU99N_1yR1ZkntU" />

<!-- Open Graph -->
<meta property="og:type" content="article" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{page_desc}" />
<meta property="og:url" content="{canonical}" />
<meta property="og:image" content="{og_image}" />
<meta property="og:site_name" content="星禾元亨" />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{page_desc}" />
<meta name="twitter:image" content="{og_image}" />

<!-- Google Analytics（统一）-->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXX"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-XXXXXXX');
</script>

<!-- 百度统计 -->
<script>
var _hmt = _hmt || [];
(function() {{
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?c8b7c967271105ca9d54b4d125df2299";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
}})();
</script>

<style>
*:{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#06080D;color:#e6edf8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8}}
a{{color:#00d4ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
header{{background:#0d1321;border-bottom:1px solid #1a2236;padding:16px 24px;display:flex;align-items:center;gap:16px}}
header a{{color:#8892a4;font-size:14px}}
header a:hover{{color:#00e67a}}
.article-container{{max-width:780px;margin:0 auto;padding:48px 24px 80px}}
.article-meta{{display:flex;gap:12px;align-items:center;margin-bottom:8px;flex-wrap:wrap}}
.article-tag{{background:#00e67a;color:#06080D;font-size:12px;font-weight:700;padding:3px 10px;border-radius:4px}}
.article-date{{color:#8892a4;font-size:13px}}
.article-title{{font-size:28px;font-weight:800;color:#f0f6fc;margin:12px 0 16px;line-height:1.4}}
.article-summary{{color:#8892a4;font-size:15px;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid #1a2236}}
.article-body{{font-size:15.5px;color:#c9d1d9;line-height:1.9}}
.article-body h2{{font-size:20px;color:#f0f6fc;margin:32px 0 12px;padding-left:12px;border-left:3px solid #00e67a}}
.article-body h3{{font-size:17px;color:#00e67a;margin:24px 0 10px}}
.article-body p{{margin-bottom:16px}}
.article-body ul,.article-body ol{{margin:12px 0 12px 24px}}
.article-body li{{margin-bottom:8px}}
.article-body table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}}
.article-body th{{background:#1a2236;color:#00e67a;padding:8px 12px;text-align:left}}
.article-body td{{padding:8px 12px;border-bottom:1px solid #1a2236}}
.article-body code{{background:#1a2236;color:#00e67a;padding:2px 6px;border-radius:3px;font-size:13px}}
.article-body pre{{background:#1a2236;padding:16px;border-radius:8px;overflow-x:auto;margin:16px 0;font-size:13px;line-height:1.6}}
.article-body blockquote{{border-left:3px solid #00e67a;padding:12px 16px;background:#0d1321;margin:16px 0;color:#8b949e;font-style:italic}}
.related{{margin-top:40px;padding:16px 20px;background:#0d1321;border-left:3px solid #00e67a;border-radius:6px;font-size:14px;color:#8892a4}}
.related strong{{color:#00e67a}}
.footer{{text-align:center;padding:40px 24px;color:#57606a;font-size:13px;border-top:1px solid #1a2236;max-width:780px;margin:0 auto}}
@media(max-width:600px){{.article-title{{font-size:22px}}}}
</style>
</head>
<body>

<header>
  <a href="/">← 首页</a>
  <span style="color:#1a2236">|</span>
  <a href="/">星禾元亨 · AI自动化</a>
</header>

<main class="article-container">
  <div class="article-meta">
    <span class="article-tag">{category}</span>
    <span class="article-date">{date_str}</span>
  </div>
  <h1 class="article-title">{title}</h1>
  <p class="article-summary">{summary}</p>

  <article class="article-body">
{content}
  </article>

  <div class="related">
    <strong>📎 相关阅读</strong><br/>
    <a href="/">返回首页查看更多文章 →</a>
  </div>
</main>

<footer class="footer">
  © 2026 深圳市星禾元亨智能科技有限公司 &nbsp;|&nbsp;
  <a href="/" style="color:#57606a">xhyh.work</a> &nbsp;|&nbsp; 粤ICP备XXXXXXXX号
</footer>

<!-- Article JSON-LD -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{page_desc}",
  "author": {{
    "@type": "Person",
    "name": "司远",
    "jobTitle": "星禾元亨创始人"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "星禾元亨",
    "logo": {{
      "@type": "ImageObject",
      "url": "{DOMAIN}/images/favicon.png"
    }}
  }},
  "datePublished": "{date_str}",
  "dateModified": "{date_str}",
  "mainEntityOfPage": "{canonical}",
  "keywords": "{tags}"
}}
</script>

<!-- FAQ JSON-LD (if applicable) -->
{faq_schema}

</body>
</html>"""
    return html


def build_case_html(case: dict) -> str:
    """为单个案例生成完整静态HTML"""
    cid        = case["id"]
    tag        = case.get("tag", "")
    emoji      = case.get("emoji", "")
    title      = case["title"]
    desc       = case["desc"]
    kpis       = case.get("kpi", [])
    detail     = markdown_to_html(case.get("detail", ""))

    page_title = f"{title} | 星禾元亨 · 客户案例"
    page_desc  = desc[:120] + ("..." if len(desc) > 120 else "")
    canonical  = f"{DOMAIN}/case-{cid}.html"
    og_image   = f"{DOMAIN}/images/og-image.png"

    # KPI 展示
    kpi_html = ""
    if kpis:
        kpi_items = "".join(
            f'<div style="text-align:center;padding:16px">'
            f'<div style="font-size:28px;font-weight:800;color:#00e67a">{k["value"]}</div>'
            f'<div style="font-size:13px;color:#8892a4;margin-top:4px">{k["label"]}</div>'
            f'</div>'
            for k in kpis
        )
        kpi_html = (
            f'<div style="display:grid;grid-template-columns:repeat({len(kpis)},1fr);'
            f'gap:16px;margin:24px 0;padding:20px;background:#0d1321;border-radius:10px">'
            f'{kpi_items}</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{page_title}</title>
<meta name="description" content="{page_desc}" />
<meta name="keywords" content="{tag},客户案例,星禾元亨,AI自动化" />
<link rel="canonical" href="{canonical}" />
<meta name="google-site-verification" content="X4GB4L_W_sGID3pymBNODfn6bTX2UU99N_1yR1ZkntU" />

<!-- Open Graph -->
<meta property="og:type" content="article" />
<meta property="og:title" content="{title} - 星禾元亨客户案例" />
<meta property="og:description" content="{page_desc}" />
<meta property="og:url" content="{canonical}" />
<meta property="og:image" content="{og_image}" />
<meta property="og:site_name" content="星禾元亨" />

<!-- 百度统计 -->
<script>
var _hmt = _hmt || [];
(function() {{
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?c8b7c967271105ca9d54b4d125df2299";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
}})();
</script>

<style>
*:{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#06080D;color:#e6edf8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8}}
a{{color:#00d4ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
header{{background:#0d1321;border-bottom:1px solid #1a2236;padding:16px 24px;display:flex;align-items:center;gap:16px}}
header a{{color:#8892a4;font-size:14px}}
header a:hover{{color:#00e67a}}
.case-container{{max-width:780px;margin:0 auto;padding:48px 24px 80px}}
.case-tag{{background:#00e67a;color:#06080D;font-size:12px;font-weight:700;padding:3px 10px;border-radius:4px;display:inline-block;margin-bottom:12px}}
.case-title{{font-size:28px;font-weight:800;color:#f0f6fc;margin-bottom:16px;line-height:1.4}}
.case-desc{{color:#8892a4;font-size:15px;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid #1a2236}}
.case-body{{font-size:15.5px;color:#c9d1d9;line-height:1.9}}
.case-body h3{{font-size:17px;color:#00e67a;margin:24px 0 10px}}
.case-body h4{{font-size:15px;color:#f0f6fc;margin:16px 0 8px}}
.case-body p{{margin-bottom:16px}}
.case-body table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}}
.case-body th{{background:#1a2236;color:#00e67a;padding:8px 12px;text-align:left}}
.case-body td{{padding:8px 12px;border-bottom:1px solid #1a2236}}
.footer{{text-align:center;padding:40px 24px;color:#57606a;font-size:13px;border-top:1px solid #1a2236;max-width:780px;margin:0 auto}}
@media(max-width:600px){{.case-title{{font-size:22px}}}}
</style>
</head>
<body>

<header>
  <a href="/">← 首页</a>
  <span style="color:#1a2236">|</span>
  <a href="/">星禾元亨 · AI自动化</a>
</header>

<main class="case-container">
  <div class="case-tag">{emoji} {tag}</div>
  <h1 class="case-title">{title}</h1>
  <p class="case-desc">{desc}</p>

  {kpi_html}

  <article class="case-body">
{detail}
  </article>
</main>

<footer class="footer">
  © 2026 深圳市星禾元亨智能科技有限公司 &nbsp;|&nbsp;
  <a href="/" style="color:#57606a">xhyh.work</a>
</footer>

<!-- CaseStudy JSON-LD -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CaseStudy",
  "name": "{title}",
  "description": "{page_desc}",
  "author": {{
    "@type": "Organization",
    "name": "星禾元亨"
  }},
  "datePublished": "2026-06-24",
  "url": "{canonical}"
}}
</script>

</body>
</html>"""
    return html


def build_faq_schema(article: dict) -> str:
    """根据文章内容生成 FAQ JSON-LD（简单实现：提取含?的段落）"""
    content = article.get("content", "")
    # 查找内容中的问答对
    qs = re.findall(r"(?:^|\n)#+\s*(.*?\?)\s*\n", content)
    if not qs:
        return ""
    faq_items = []
    for q in qs[:5]:  # 最多5个
        faq_items.append(
            f'{{"@type":"Question","name":"{q}","acceptedAnswer"'
            f'{{"@type":"Answer","text":"详见文章内容"}}}}'
        )
    if not faq_items:
        return ""
    return (
        f'<script type="application/ld+json">\n'
        f'{{"@context":"https://schema.org","@type":"FAQPage",'
        f'"mainEntity":[{",".join(faq_items)}]}}\n'
        f'</script>'
    )


def main():
    # 读取数据
    with open(ARTICLES_JSON, "r", encoding="utf-8") as f:
        articles = json.load(f)
    with open(CASES_JSON, "r", encoding="utf-8") as f:
        cases = json.load(f)

    os.chdir(OUTPUT_DIR)

    # 生成文章页
    for article in articles:
        aid   = article["id"]
        html  = build_article_html(article)
        fname = f"article-{aid}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ 生成文章页: {fname} — {article['title'][:30]}")

    # 生成案例页
    for case in cases:
        cid   = case["id"]
        html  = build_case_html(case)
        fname = f"case-{cid}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ 生成案例页: {fname} — {case['title'][:30]}")

    print(f"\n共生成 {len(articles)} 篇静态文章 + {len(cases)} 篇静态案例")


if __name__ == "__main__":
    main()
