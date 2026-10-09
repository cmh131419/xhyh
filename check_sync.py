# -*- coding: utf-8 -*-
"""xhyh.work 发布前一致性检查（放进仓库根目录，随每次发布运行）

检查项：
  1. sitemap.xml 里每个 URL 都能在仓库里找到对应文件
  2. 仓库里每个「应公开」的页面都在 sitemap 里（文章页/问题库页/固定入口页）
  3. llms.txt 与 sitemap.xml 的 URL 集合完全一致
  4. data/articles.json 里每条记录：有对应页面 + 在 sitemap 里
  5. 每个文章页：canonical 与路径一致、含 FAQPage 结构化数据（警告级）
  6. 首页是否链接到每个文章页（警告级，问题库不计）

用法：python check_sync.py      退出码 0=通过，1=有错误
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
errors, warns = [], []


def url_to_file(url):
    """把一个 xhyh.work URL 映射为仓库内相对路径；无法映射返回 None"""
    m = re.match(r"^https://xhyh\.work/(.*)$", url)
    if not m:
        return None
    path = m.group(1)
    if path == "" or path.endswith("/"):
        return os.path.join(path, "index.html").replace("\\", "/") or "index.html"
    return path


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep)))


def main():
    # --- sitemap ---
    sm_path = os.path.join(ROOT, "sitemap.xml")
    tree = ET.parse(sm_path)
    locs = [e.text.strip() for e in tree.getroot().iter(NS + "loc")]
    if len(locs) != len(set(locs)):
        errors.append("sitemap.xml 存在重复 URL")
    sm_set = set(locs)

    for u in locs:
        rel = url_to_file(u)
        if rel is None:
            errors.append("sitemap 里的 URL 不是 xhyh.work 域名：%s" % u)
        elif not exists(rel):
            errors.append("sitemap 列了但仓库没有该文件：%s → %s" % (u, rel))

    # --- 仓库页面是否漏进 sitemap（故意 noindex 的兼容页不算） ---
    info = []

    def dirs_with_index(sub):
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            return []
        return sorted(d for d in os.listdir(base)
                      if os.path.isfile(os.path.join(base, d, "index.html")))

    def is_noindex(rel):
        html = open(os.path.join(ROOT, rel.replace("/", os.sep)), encoding="utf-8",
                    errors="ignore").read(4000)
        return "noindex" in html

    for sub in ("articles", "question-bank"):
        for slug in dirs_with_index(sub):
            rel = "%s/%s/index.html" % (sub, slug)
            if is_noindex(rel):
                info.append("noindex 兼容页，按设计不进 sitemap：%s" % rel)
                continue
            u = "https://xhyh.work/%s/%s/" % (sub, slug)
            if u not in sm_set:
                errors.append("%s/%s/ 有页面但不在 sitemap.xml" % (sub, slug))

    # --- llms.txt ---
    ll_path = os.path.join(ROOT, "llms.txt")
    ll = open(ll_path, encoding="utf-8").read()
    ll_set = set(re.findall(r"https://xhyh\.work[^\s\)\]]*", ll))
    ll_set = {u.rstrip(".,)") for u in ll_set}
    for u in sorted(sm_set - ll_set):
        errors.append("sitemap 有、llms.txt 缺：%s" % u)
    for u in sorted(ll_set - sm_set):
        errors.append("llms.txt 有、sitemap 没有：%s" % u)

    # --- data/articles.json ---
    arts = json.load(open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8"))
    ids = [a.get("id") for a in arts]
    if len(ids) != len(set(ids)):
        errors.append("data/articles.json 存在重复 id")
    for a in arts:
        u = "https://xhyh.work" + a["url"]
        if u not in sm_set:
            errors.append("articles.json 记录未进 sitemap：%s" % u)
        rel = url_to_file(u)
        if rel and not exists(rel):
            errors.append("articles.json 记录没有对应页面：%s" % u)

    # --- 文章页质量（警告级；noindex 兼容页跳过） ---
    home = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    for slug in dirs_with_index("articles"):
        rel = "articles/%s/index.html" % slug
        if is_noindex(rel):
            continue
        html = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        want = 'rel="canonical" href="https://xhyh.work/articles/%s/"' % slug
        if want not in html:
            warns.append("canonical 缺失或不匹配：%s" % rel)
        if "FAQPage" not in html:
            warns.append("缺少 FAQPage 结构化数据：%s" % rel)
        if 'class="card article-card" href="/articles/%s/"' % slug not in home:
            warns.append("首页未链接该文章：/articles/%s/" % slug)
    for slug in dirs_with_index("question-bank"):
        rel = "question-bank/%s/index.html" % slug
        html = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        if "FAQPage" not in html:
            warns.append("问题库页缺少 FAQPage 结构化数据：%s" % rel)
        if 'rel="canonical"' not in html:
            warns.append("问题库页缺少 canonical：%s" % rel)

    # --- 输出 ---
    print("=" * 72)
    print("xhyh.work 一致性检查")
    print("  sitemap URL      : %d 条" % len(locs))
    print("  llms.txt URL     : %d 条" % len(ll_set))
    print("  articles.json    : %d 条" % len(arts))
    print("  文章页 / 问题库页 : %d / %d"
          % (len(dirs_with_index("articles")), len(dirs_with_index("question-bank"))))
    print("=" * 72)
    if errors:
        print("错误 %d 项：" % len(errors))
        for e in errors:
            print("  ✗ %s" % e)
    else:
        print("错误 0 项 ✅")
    if warns:
        print("警告 %d 项（不阻断发布）：" % len(warns))
        for w in warns:
            print("  ! %s" % w)
    else:
        print("警告 0 项 ✅")
    if info:
        print("提示 %d 项：" % len(info))
        for i in info:
            print("  · %s" % i)
    print("=" * 72)
    print("结果：%s" % ("FAIL" if errors else "PASS"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
