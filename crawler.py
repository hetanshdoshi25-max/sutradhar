"""
SUTRADHAR - Live crawler (simulated hidden-service environment)
-------------------------------------------------------------------
Performs REAL crawling - HTTP requests, HTML parsing, link discovery -
against a small self-hosted "marketplace" that mimics a Tor hidden
service's structure (index page -> forum boards -> posts with
alias/site/body markup).

WHY SIMULATED, NOT A REAL .onion: standing up and publicly crawling a real
Tor hidden service for a student demo carries real legal/safety exposure
(the crawler cannot distinguish authorized target from any other .onion it
might stumble onto, and Tor infrastructure work is out of scope for the
time available). This module proves the CRAWLING CAPABILITY itself -
fetching, parsing, following links, extracting structured posts - end to
end and honestly, against a labelled local target. Pointing it at a real
.onion address in production is a target-configuration change, not an
architecture change.
"""

import re
import time
import urllib.request
from urllib.parse import urljoin

LINK_RE = re.compile(r'href="([^"]+\.html)"')
POST_RE = re.compile(
    r'<div class="post" data-alias="([^"]*)" data-site="([^"]*)"[^>]*>.*?'
    r'<div class="body">(.*?)</div>\s*</div>', re.S)


def _fetch(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "SUTRADHAR-Crawler/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def crawl(base_url, max_pages=80, on_page=None, delay=0.08):
    """Breadth-first crawl starting at base_url's index. Returns a list of
    discovered posts: {alias, site, text, source_page}. `on_page` is an
    optional callback(url, posts_found) fired after each page - used to
    stream live progress to the console."""
    seen_pages = set()
    queue = [urljoin(base_url, "index.html")]
    posts = []

    while queue and len(seen_pages) < max_pages:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)

        try:
            html = _fetch(url)
        except Exception as e:
            if on_page:
                on_page(url, [], error=str(e))
            continue

        # discover new links on this page (breadth-first traversal)
        for href in LINK_RE.findall(html):
            full = urljoin(url, href)
            if full not in seen_pages and full not in queue:
                queue.append(full)

        # extract structured posts from this page
        page_posts = []
        for alias, site, text in POST_RE.findall(html):
            text = re.sub(r"\s+", " ", text).strip()
            entry = {"alias": alias, "site": site, "text": text, "source_page": url}
            page_posts.append(entry)
            posts.append(entry)

        if on_page:
            on_page(url, page_posts)
        time.sleep(delay)  # polite crawl delay, also makes progress visible live

    return {"pages_crawled": len(seen_pages), "posts_found": len(posts), "posts": posts}


if __name__ == "__main__":
    result = crawl("http://127.0.0.1:8010/", on_page=lambda u, p, error=None:
                   print(f"  [{'ERR' if error else 'OK'}] {u} -> {len(p)} post(s)" + (f" ({error})" if error else "")))
    print(f"\nCrawl complete: {result['pages_crawled']} pages, {result['posts_found']} posts")
    for p in result["posts"]:
        print(f"  {p['alias']:<14} ({p['site']}) - {p['text'][:60]}...")
