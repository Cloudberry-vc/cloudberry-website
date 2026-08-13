#!/usr/bin/env python3
"""
Static post-page generator for the Cloudberry VC site.

Reads posts/posts.json + each posts/<id>.json and writes a fully static
HTML page per post at news/<slug>/index.html, with per-post SEO:
title, meta description, canonical, Open Graph, Twitter Card, and
NewsArticle JSON-LD. Content is baked into the HTML so Google and social
scrapers (which do not run JavaScript) see everything.

Run from the repo root after adding or editing a post:
    python3 generate_posts.py

Then commit the regenerated news/ directory.
"""

import json
import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
NEWS_DIR = ROOT / "news"
SITE = "https://cloudberry.vc"
DEFAULT_OG_IMAGE = f"{SITE}/assets/og-share.png"

TEMPLATE = (ROOT / "post_template.html").read_text(encoding="utf-8")


def fmt_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    # Cross-platform day without leading zero
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def build_head(meta, canonical, og_image):
    title = html.escape(f"{meta['title']} | Cloudberry VC")
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

    out_dir = NEWS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return canonical


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


if __name__ == "__main__":
    main()
