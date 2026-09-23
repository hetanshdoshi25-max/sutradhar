"""
SUTRADHAR - Simulated marketplace network generator
--------------------------------------------------------
Generates a LARGE, realistic-looking network of simulated dark-web
marketplaces/forums for the live-crawler demo: multiple distinct sites,
each with its own theme, vendor listings, product categories, forum
threads and reviews - hundreds of pages of procedurally generated decoy
content, with our 5 target personas' real posts seeded naturally inside.

This is still a LOCAL, LABELLED simulation (see crawler.py's module
docstring for why) - it is made large and varied so the crawler has a
genuinely non-trivial network to traverse, not a toy 4-page site.
"""

import random
import os

random.seed(2026)

MARKETS = [
    {"slug": "obsidian", "name": "Obsidian Market", "onion": "obsdnmktqx7h4vrpz2klm5tn8w.onion", "accent": "#8a3aff"},
    {"slug": "redgate",  "name": "RedGate Exchange", "onion": "rdgt3exch9nqp5vlz8xkmr2tw.onion", "accent": "#e0433c"},
    {"slug": "silvermkt","name": "Silver Circuit",   "onion": "slvrct5wkq9xnh4mzpv7ltbjr.onion", "accent": "#8fa5c4"},
    {"slug": "nightbay",  "name": "NightBay Trading", "onion": "ngbay8mzqk3xvhp5wltnc7rjy.onion", "accent": "#2fa66a"},
    {"slug": "cinder",   "name": "Cinder Board",     "onion": "cndrbrd4wqm9xhlv6ptzk2njs.onion", "accent": "#e08a2e"},
]

CATEGORIES = ["Digital Goods", "Accounts & Access", "Documents", "Electronics",
              "Software", "Services", "Miscellaneous"]

VENDOR_ADJ = ["Silent", "Iron", "Ghost", "Velvet", "Quiet", "North", "Grey", "Deep",
              "Steel", "Hollow", "Crimson", "Static", "Dusk", "Frost"]
VENDOR_NOUN = ["Fox", "Wolf", "Raven", "Serpent", "Hawk", "Wren", "Badger", "Crow",
               "Lynx", "Otter", "Falcon", "Marten", "Heron", "Viper"]

LISTING_TITLES = [
    "Premium account bundle - verified", "Bulk digital delivery - instant",
    "Escrow-protected service package", "Long-term vendor - established 2023",
    "Fast shipping, stealth packaging", "Software license - lifetime key",
    "Data access - limited slots", "Consultation service - by appointment",
]

REVIEW_LINES = [
    "Fast delivery, exactly as described.", "Communication could be better but product was fine.",
    "Solid vendor, will reorder.", "Slight delay but resolved quickly via escrow.",
    "Package arrived intact, no issues.", "Good value, would recommend to others.",
    "Vendor was responsive to questions.", "Took a few days longer than expected.",
]

FORUM_TOPICS = [
    "Anyone had issues with the new verification system?",
    "Escrow release times seem inconsistent lately",
    "PSA: watch out for phishing mirrors",
    "Thoughts on the updated fee structure",
    "Best practices for account security discussion",
    "Market downtime - status updates thread",
    "Vendor application process - questions",
    "General discussion - keep it civil",
]

FORUM_REPLIES = [
    "Same here, seems to be affecting multiple users.",
    "Support said it's a known issue, fix incoming.",
    "Thanks for the heads up, appreciate it.",
    "This has been discussed before, use search.",
    "Following this thread for updates.",
    "Can confirm, happened to me too last week.",
]


def _vendor_name(rng):
    return rng.choice(VENDOR_ADJ) + rng.choice(VENDOR_NOUN) + str(rng.randint(1, 99))


def _onion_id(rng, length=16):
    alpha = "abcdefghijklmnopqrstuvwxyz234567"
    return "".join(rng.choice(alpha) for _ in range(length))


PAGE_CSS = """
body{{background:#0a0a0a;color:#8a8a8a;font-family:Georgia,serif;max-width:900px;margin:24px auto;padding:0 20px}}
.fakebar{{background:#151515;border:1px solid #2a2a2a;padding:6px 12px;font-family:monospace;font-size:11px;color:{accent};margin-bottom:18px;border-radius:3px}}
.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #2a2a2a;padding-bottom:10px;margin-bottom:16px}}
h1{{color:{accent};font-size:19px;margin:0}}
nav{{font-size:11px;margin-bottom:16px}}
nav a{{color:#6a6;text-decoration:none;margin-right:10px}}
.card{{border:1px solid #242424;background:#131313;padding:12px 14px;margin:10px 0;border-radius:3px}}
.card .t{{color:#c9c9c9;font-weight:bold;font-size:13px}}
.card .m{{color:#666;font-size:10.5px;margin-top:3px}}
.post{{border:1px solid #222;background:#111;padding:13px 15px;margin:12px 0;border-radius:3px}}
.post .meta{{color:#666;font-size:11px;margin-bottom:7px}}
.post .alias{{color:{accent};font-weight:bold}}
.post .body{{color:#aaa;line-height:1.6;font-size:13px}}
.grid{{display:flex;flex-wrap:wrap;gap:10px}}
.grid .card{{flex:1;min-width:220px}}
footer{{margin-top:26px;font-size:10.5px;color:#555;border-top:1px solid #222;padding-top:10px}}
"""

PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title}</title>
<style>{css}</style></head><body>
<div class="fakebar">\U0001f9c5 {onion} &nbsp;|&nbsp; SIMULATED HIDDEN SERVICE (local demo target, not real Tor)</div>
<div class="hdr"><h1>{market_name}</h1><span style="font-size:10.5px;color:#555">{page_label}</span></div>
<nav>{nav}</nav>
{body}
<footer>{market_name} &middot; simulated for crawler capability demonstration only</footer>
</body></html>"""

POST_TPL = """<div class="post" data-alias="{alias}" data-site="{site}" data-ts="{ts}">
<div class="meta"><span class="alias">{alias}</span> &middot; {site} &middot; posted {ts}</div>
<div class="body">{text}</div></div>"""


def generate(out_dir, personas, pages_per_market=10):
    """Build `len(MARKETS) * pages_per_market` pages across several themed
    marketplaces. Real target personas are distributed across different
    markets/pages; everything else is procedurally generated decoy content."""
    rng = random.Random(2026)
    os.makedirs(out_dir, exist_ok=True)

    # distribute the real personas across markets/pages so they're findable
    # but not clustered obviously on one page
    persona_slots = list(personas)
    rng.shuffle(persona_slots)

    all_market_index_links = []
    total_pages = 0

    for mi, market in enumerate(MARKETS):
        nav_links = " ".join(
            f'<a href="{market["slug"]}-{p}.html">{p}</a>'
            for p in ["index", "forum", "vendors"]
        )
        all_market_index_links.append(f'<a href="{market["slug"]}-index.html">{market["name"]}</a>')

        # ---- market index: category grid ----
        cats_html = '<div class="grid">' + "".join(
            f'<div class="card"><div class="t">{c}</div><div class="m">{rng.randint(40,900)} active listings</div></div>'
            for c in CATEGORIES
        ) + "</div>"
        open(os.path.join(out_dir, f'{market["slug"]}-index.html'), "w").write(PAGE.format(
            title=f'{market["name"]} - Index', css=PAGE_CSS.format(accent=market["accent"]),
            onion=market["onion"], market_name=market["name"], page_label="market index",
            nav=nav_links, body=cats_html))
        total_pages += 1

        # ---- vendor listing pages (procedural decoys) ----
        vendor_cards = []
        for _ in range(pages_per_market):
            v = _vendor_name(rng)
            title = rng.choice(LISTING_TITLES)
            vendor_cards.append(
                f'<div class="card"><div class="t">{v} &mdash; {title}</div>'
                f'<div class="m">{rng.randint(3,340)} sales &middot; {rng.choice(REVIEW_LINES)}</div></div>')
        open(os.path.join(out_dir, f'{market["slug"]}-vendors.html'), "w").write(PAGE.format(
            title=f'{market["name"]} - Vendors', css=PAGE_CSS.format(accent=market["accent"]),
            onion=market["onion"], market_name=market["name"], page_label="vendor directory",
            nav=nav_links, body="\n".join(vendor_cards)))
        total_pages += 1

        # ---- forum page: mix of decoy threads + (sometimes) a real persona post ----
        forum_posts = []
        # decoy thread starters + replies
        for _ in range(rng.randint(4, 7)):
            topic = rng.choice(FORUM_TOPICS)
            handle = _vendor_name(rng)
            forum_posts.append(POST_TPL.format(
                alias=handle, site=market["name"], ts=f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}",
                text=f"{topic} {rng.choice(FORUM_REPLIES)}"))
        # seed a real target persona post on some markets
        if mi < len(persona_slots):
            p = persona_slots[mi]
            forum_posts.insert(rng.randint(0, len(forum_posts)), POST_TPL.format(
                alias=p["alias"], site=p.get("site", market["name"]),
                ts=f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}", text=p["text"]))
        rng.shuffle(forum_posts)
        open(os.path.join(out_dir, f'{market["slug"]}-forum.html'), "w").write(PAGE.format(
            title=f'{market["name"]} - Forum', css=PAGE_CSS.format(accent=market["accent"]),
            onion=market["onion"], market_name=market["name"], page_label="general discussion",
            nav=nav_links, body="\n".join(forum_posts)))
        total_pages += 1

        # ---- extra sub-forum pages to bulk up crawl depth ----
        for extra_i in range(pages_per_market - 3):
            sub_posts = []
            for _ in range(rng.randint(2, 5)):
                handle = _vendor_name(rng)
                sub_posts.append(POST_TPL.format(
                    alias=handle, site=market["name"], ts=f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}",
                    text=rng.choice(FORUM_REPLIES) + " " + rng.choice(REVIEW_LINES)))
            # occasionally place a remaining real persona here
            if len(persona_slots) > len(MARKETS) and extra_i == 0 and mi < len(persona_slots) - len(MARKETS):
                p = persona_slots[len(MARKETS) + mi]
                sub_posts.insert(0, POST_TPL.format(
                    alias=p["alias"], site=p.get("site", market["name"]),
                    ts=f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}", text=p["text"]))
            fname = f'{market["slug"]}-sub{extra_i}.html'
            open(os.path.join(out_dir, fname), "w").write(PAGE.format(
                title=f'{market["name"]} - Board {extra_i+1}', css=PAGE_CSS.format(accent=market["accent"]),
                onion=market["onion"], market_name=market["name"], page_label=f"sub-board {extra_i+1}",
                nav=nav_links + f' <a href="{market["slug"]}-forum.html">back to forum</a>',
                body="\n".join(sub_posts)))
            total_pages += 1

    # ---- network index linking every market ----
    open(os.path.join(out_dir, "index.html"), "w").write(PAGE.format(
        title="Darknet Directory - Index", css=PAGE_CSS.format(accent="#7c9ac9"),
        onion="dirlnk8xqmzt4wvhp2ncr9jkl.onion", market_name="Darknet Directory", page_label="network index",
        nav="", body='<div class="grid">' + "".join(
            f'<div class="card"><div class="t">{l}</div></div>' for l in all_market_index_links) + "</div>"))
    total_pages += 1

    return {"markets": len(MARKETS), "pages": total_pages}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from sample_personas import PERSONAS
    stats = generate("simsite", PERSONAS, pages_per_market=12)
    print(f"generated {stats['pages']} pages across {stats['markets']} simulated marketplaces")
