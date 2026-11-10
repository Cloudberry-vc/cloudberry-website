#!/usr/bin/env python3
"""
Static post-page generator for the Cloudberry VC site.

Reads posts/posts.json + each posts/<id>.json and writes a fully static
HTML page per post at news/<slug>/index.html, with per-post SEO:
title, meta description, canonical, Open Graph, Twitter Card, and
NewsArticle JSON-LD. Content is baked into the HTML so Google and social
scrapers (which do not run JavaScript) see everything.

It also keeps three things in step with posts/posts.json and
portfolio/portfolio.json, so crawlers that do not run JavaScript (Bing,
the AI search crawlers, link-preview bots) see the same links a visitor does:

  * the post cards in news.html and the six newest on the homepage,
  * the portfolio cards on the homepage,
  * sitemap.xml, with a <lastmod> date on every URL.

The cards are written between `<!-- static:... -->` markers. The page's own
JavaScript still loads the JSON and replaces them, so what a visitor sees is
unchanged; never edit between the markers by hand.

Run from the repo root after adding or editing a post or a portfolio company:
    python3 generate_posts.py

Then commit the regenerated news/ directory, news.html, index.html and
sitemap.xml.
"""

import json
import html
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
NEWS_DIR = ROOT / "news"
SITE = "https://cloudberry.vc"
DEFAULT_OG_IMAGE = f"{SITE}/assets/og-share.png"
PORTFOLIO_FILE = ROOT / "portfolio" / "portfolio.json"
SITEMAP_FILE = ROOT / "sitemap.xml"
TITLE_SUFFIX = " | Cloudberry VC"
TITLE_MAX = 65  # search results cut a title off around here
HOME_NEWS_CARDS = 6  # must match maxShow in index.html

# Pages listed in the sitemap besides the posts: path -> (changefreq, priority).
STATIC_PAGES = {
    "": ("weekly", "1.0"),
    "news.html": ("weekly", "0.9"),
    "privacy-policy.html": ("yearly", "0.3"),
    "disclosures.html": ("yearly", "0.3"),
}

# Must match categoryIcon() in index.html and news.html.
CATEGORY_ICONS = {
    "Fund News": "\U0001F4E2",
    "Deep Dive": "\U0001F52C",
    "Thesis": "\U0001F9ED",
    "Portfolio": "\U0001F680",
    "Industry": "\u2699\uFE0F",
    "Opinion": "\U0001F4A1",
}

TEMPLATE = (ROOT / "post_template.html").read_text(encoding="utf-8")


def fmt_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    # Cross-platform day without leading zero
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def page_title(post_title):
    """The <title> text: the site name is dropped when it would be cut off."""
    full = post_title + TITLE_SUFFIX
    return full if len(full) <= TITLE_MAX else post_title


def build_head(meta, canonical, og_image):
    title = html.escape(page_title(meta["title"]))
    desc = html.escape(meta.get("summary", ""), quote=True)
    og_title = html.escape(meta["title"])
    jsonld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": meta["title"],
        "description": meta.get("summary", ""),
        "datePublished": meta["date"],
        "dateModified": meta["date"],
        "author": {"@type": "Organization", "name": "Cloudberry VC", "url": SITE},
        "publisher": {
            "@type": "Organization",
            "name": "Cloudberry VC",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/logo_vc_dark.png"},
        },
        "image": og_image,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }
    jsonld_str = json.dumps(jsonld, ensure_ascii=False, indent=2)
    return f"""    <title>{title}</title>
    <meta name="description" content="{desc}">
    <link rel="icon" href="/assets/berry_icon.png" type="image/png">
    <link rel="canonical" href="{canonical}">
    <meta name="google-site-verification" content="1224mTXrhqarxmKMTx8qUroTttgN_f8NBbqr9HDx5N0">
    <meta name="google-site-verification" content="JUj3bKYoaq-nqbGCF6S8_3Cre4F0No1B5f5K7hyidXM">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Cloudberry VC">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:image" content="{og_image}">
    <meta property="article:published_time" content="{meta['date']}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{desc}">
    <meta name="twitter:image" content="{og_image}">
    <script type="application/ld+json">
{jsonld_str}
    </script>"""


def build_article(meta, content):
    date = fmt_date(meta["date"])
    title = html.escape(meta["title"])
    summary = html.escape(meta.get("summary", ""))
    cover = ""
    if meta.get("coverImage"):
        cover = f'<img class="article-cover" src="{meta["coverImage"]}" alt="{title}">'
    return f"""    <article class="article" id="article">
        <p class="article-date">{date}</p>
        <h1>{title}</h1>
        <p class="article-summary">{summary}</p>
        {cover}
        <div class="article-body">{content}</div>
    </article>"""


def generate_page(meta, content):
    slug = meta["id"]
    canonical = f"{SITE}/news/{slug}/"
    og_image = meta["coverImage"] if meta.get("coverImage") else DEFAULT_OG_IMAGE
    if og_image and og_image.startswith("assets/"):
        og_image = f"{SITE}/{og_image}"

    page = TEMPLATE

    # Replace the <head> SEO block: from <title> through the </meta twitter:image> line.
    head_start = page.index("    <title>")
    head_end = page.index("<!-- Google Tag Manager -->")
    page = page[:head_start] + build_head(meta, canonical, og_image) + "\n    " + page[head_end:]

    # Make asset and internal links root-absolute (page lives two levels deep).
    page = page.replace('href="index.html"', 'href="/"')
    page = page.replace('href="index.html#news"', 'href="/#news"')
    page = page.replace('src="assets/', 'src="/assets/')
    page = page.replace('href="assets/', 'href="/assets/')

    # Bake the article in place of the loading spinner.
    loading_block = re.search(
        r'    <article class="article" id="article">.*?</article>',
        page,
        re.DOTALL,
    )
    page = page[: loading_block.start()] + build_article(meta, content) + page[loading_block.end():]

    # Drop the client-side loader script (content is now static).
    page = re.sub(r"    <script>\s*function formatDate.*?</script>\n", "", page, flags=re.DOTALL)

    # post_template.html itself is noindex (it is a served file with no
    # content). That tag sits inside the head block replaced above; if it ever
    # moves, stop rather than publish a post search engines are told to skip.
    if re.search(r'<meta\s+name="robots"[^>]*noindex', page):
        raise SystemExit(f"{slug}: generated page is noindex; check post_template.html")

    out_dir = NEWS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return canonical


def post_url(meta):
    """Site-relative link to a post. Must match getPostUrl() in the pages."""
    if meta.get("type") == "external" and meta.get("url"):
        return meta["url"]
    if meta.get("type") == "html" and meta.get("file"):
        return "posts/" + meta["file"]
    return f"news/{meta['id']}/"


def newest_first(posts):
    return sorted(posts, key=lambda m: m["date"], reverse=True)


def news_card(meta, home, index=0):
    """One post card, the same markup the page's JavaScript builds."""
    title = html.escape(meta["title"], quote=False)
    summary = html.escape(meta.get("summary", ""), quote=False)
    category = html.escape(meta.get("category", ""), quote=False)
    icon = CATEGORY_ICONS.get(meta.get("category"), CATEGORY_ICONS["Deep Dive"])
    cover = html.escape(meta.get("coverImage", ""), quote=True)
    if home:
        css = f"news-card reveal reveal-delay-{(index % 3) + 1}"
        image = (f'<img src="{cover}" alt="" loading="lazy" decoding="async" '
                 f'style="width:100%;height:100%;object-fit:cover;">')
        chip = ('<span style="position:absolute;top:12px;left:12px;background:rgba(255,189,72,0.85);'
                'backdrop-filter:blur(8px);color:var(--space-blue);font-size:0.7rem;font-weight:600;'
                f'letter-spacing:0.1em;text-transform:uppercase;padding:4px 10px;border-radius:6px;">{category}</span>')
    else:
        css = "news-card"
        image = f'<img src="{cover}" alt="{html.escape(meta["title"], quote=True)}" loading="lazy" decoding="async">'
        chip = f'<span class="news-card-category">{category}</span>'
    if not cover:
        image = f'<span style="opacity:1;"><span style="font-size:3rem;opacity:0.25;">{icon}</span></span>'
    if not category:
        chip = ""
    return f"""<a href="{html.escape(post_url(meta), quote=True)}" class="{css}" data-static>
                    <div class="news-card-image">
                        {image}
                        {chip}
                    </div>
                    <div class="news-card-body">
                        <p class="news-card-date">{fmt_date(meta["date"])}</p>
                        <h3>{title}</h3>
                        <p>{summary}</p>
                        <span class="news-card-link">Read more <span>&rarr;</span></span>
                    </div>
                </a>"""


def portfolio_card(company):
    """One portfolio card, the same markup loadPortfolio() builds."""
    esc = lambda value: html.escape(value, quote=False)  # noqa: E731
    attr = lambda value: html.escape(value, quote=True)  # noqa: E731
    name = company["name"]
    founders = "".join(
        f'<a href="{attr(f["linkedin"])}" target="_blank" rel="noopener">{esc(f["name"])} ({esc(f["role"])})</a>'
        for f in company.get("founders", [])
    )
    links = []
    if company.get("website"):
        links.append(f'<a href="{attr(company["website"])}" target="_blank" rel="noopener">Website <span>&rarr;</span></a>')
    thesis = company.get("investmentThesis")
    if thesis:
        links.append(f'<a href="{attr(thesis["url"])}">{esc(thesis["label"])} <span>&rarr;</span></a>')
    press = company.get("pressRelease")
    if press:
        links.append(f'<a href="{attr(press["url"])}" target="_blank" rel="noopener">{esc(press["label"])} <span>&rarr;</span></a>')
    icon = ""
    if company.get("icon"):
        icon = f'<img class="logo-icon" src="{attr(company["icon"])}" alt="{attr(name)} icon" loading="lazy" decoding="async">'
    founded = f'<span>Founded {esc(str(company["founded"]))}</span>' if company.get("founded") else ""
    return f"""<div class="portfolio-card reveal" data-static>
                    <div class="portfolio-logo">
                        <a href="{attr(company.get("website", ""))}" target="_blank" rel="noopener">
                            <img class="logo-text" src="{attr(company["logo"])}" alt="{attr(name)}" loading="lazy" decoding="async">
                            {icon}
                        </a>
                    </div>
                    <div class="portfolio-info">
                        <h3>{esc(name)}</h3>
                        <div class="portfolio-meta">
                            {founded}
                            <span>{esc(company.get("category", ""))}</span>
                        </div>
                        <p class="portfolio-desc">{esc(company["description"])}</p>
                        <div class="portfolio-founders">{founders}</div>
                        <div class="portfolio-links">{"".join(links)}</div>
                    </div>
                </div>"""


def bake(page_path, name, cards):
    """Replace what sits between the static:<name> markers in a page."""
    text = page_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(<!-- static:{name}:start[^>]*-->)(.*?)(<!-- static:{name}:end -->)", re.DOTALL
    )
    if not pattern.search(text):
        raise SystemExit(f"{page_path.name}: no static:{name} markers found")
    body = "".join(f"\n                {card}" for card in cards) + "\n                "
    updated = pattern.sub(lambda m: m.group(1) + body + m.group(3), text)
    if updated != text:
        page_path.write_text(updated, encoding="utf-8")
        print(f"  baked {len(cards)} {name} cards into {page_path.name}")


def last_changed(path):
    """ISO date a file last changed: today if it has uncommitted edits."""
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if dirty:
            return date.today().isoformat()
        committed = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return committed or date.today().isoformat()
    except (OSError, subprocess.CalledProcessError):
        return date.today().isoformat()


def write_sitemap(posts):
    """Rewrite sitemap.xml from the page list and the posts, with lastmod.

    A changefreq or priority already set by hand for a URL is kept.
    """
    existing = {}
    if SITEMAP_FILE.exists():
        for entry in re.findall(r"<url>(.*?)</url>", SITEMAP_FILE.read_text(encoding="utf-8"), re.DOTALL):
            loc = re.search(r"<loc>\s*(\S+?)\s*</loc>", entry)
            freq = re.search(r"<changefreq>\s*(\S+?)\s*</changefreq>", entry)
            prio = re.search(r"<priority>\s*(\S+?)\s*</priority>", entry)
            if loc:
                existing[loc.group(1)] = (freq.group(1) if freq else None, prio.group(1) if prio else None)

    newest_post = max((m["date"] for m in posts), default=date.today().isoformat())
    rows = []
    for path, (freq, prio) in STATIC_PAGES.items():
        file_path = ROOT / (path or "index.html")
        lastmod = last_changed(file_path)
        if path in ("", "news.html"):  # both list the posts
            lastmod = max(lastmod, newest_post)
        rows.append((f"{SITE}/{path}", lastmod, freq, prio))
    for meta in newest_first(posts):
        if meta.get("type") == "external":
            continue
        lastmod = meta.get("updated") or meta["date"]
        rows.append((f"{SITE}/{post_url(meta)}", lastmod, "monthly", "0.7"))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, freq, prio in rows:
        kept_freq, kept_prio = existing.get(loc, (None, None))
        out += ["    <url>",
                f"        <loc>{loc}</loc>",
                f"        <lastmod>{lastmod}</lastmod>",
                f"        <changefreq>{kept_freq or freq}</changefreq>",
                f"        <priority>{kept_prio or prio}</priority>",
                "    </url>"]
    out.append("</urlset>")
    text = "\n".join(out) + "\n"
    if not SITEMAP_FILE.exists() or SITEMAP_FILE.read_text(encoding="utf-8") != text:
        SITEMAP_FILE.write_text(text, encoding="utf-8")
        print(f"  wrote sitemap.xml ({len(rows)} URLs)")


def main():
    posts = json.loads((POSTS_DIR / "posts.json").read_text(encoding="utf-8"))
    generated = []
    for meta in posts:
        if meta.get("type") == "html" and meta.get("file"):
            continue  # standalone HTML posts render themselves
        content_file = POSTS_DIR / f"{meta['id']}.json"
        if content_file.exists():
            content = json.loads(content_file.read_text(encoding="utf-8")).get("content", "")
        else:
            # No dedicated content file: fall back to the summary (matches the
            # old client-side behaviour) so the post still gets a static page.
            content = f"<p>{html.escape(meta.get('summary', ''))}</p>"
            print(f"  note {meta['id']}: no content file, using summary")
        url = generate_page(meta, content)
        generated.append((meta["id"], url))
        print(f"  wrote news/{meta['id']}/index.html")
    print(f"\nGenerated {len(generated)} post pages.")

    ordered = newest_first(posts)
    bake(ROOT / "news.html", "news", [news_card(m, home=False) for m in ordered])
    bake(ROOT / "index.html", "news",
         [news_card(m, home=True, index=i) for i, m in enumerate(ordered[:HOME_NEWS_CARDS])])
    if PORTFOLIO_FILE.exists():
        companies = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
        bake(ROOT / "index.html", "portfolio", [portfolio_card(c) for c in companies])
    write_sitemap(posts)


if __name__ == "__main__":
    main()
