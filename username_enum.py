"""
SUTRADHAR - Username enumeration (public footprint)
---------------------------------------------------
Given a handle, check which PUBLIC platforms have a profile at that username.
This is legal, passive OSINT - it only queries public profile pages exactly
as a browser would, and reports existence. It gives an investigator clearnet
leads (a GitHub or Reddit account tied to a dark-web alias is a real thread).

Returns per platform:  True = profile exists, False = not found,
                       None = blocked / rate-limited / unknown.

No third-party dependencies (stdlib urllib), concurrent, short timeout.
"""

import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; SUTRADHAR-OSINT/1.0)"

# platforms whose "missing" state is a clean 404, plus some that need a body
# check (missing_text = substring present when NOT found; found_text = substring
# present when found). check = URL we query, url = human profile link.
PLATFORMS = [
    {"name": "GitHub",     "check": "https://github.com/{u}",           "url": "https://github.com/{u}"},
    {"name": "GitLab",     "check": "https://gitlab.com/{u}",           "url": "https://gitlab.com/{u}"},
    {"name": "Reddit",     "check": "https://old.reddit.com/user/{u}/", "url": "https://www.reddit.com/user/{u}"},
    {"name": "Keybase",    "check": "https://keybase.io/{u}",           "url": "https://keybase.io/{u}"},
    {"name": "Dev.to",     "check": "https://dev.to/{u}",               "url": "https://dev.to/{u}"},
    {"name": "Replit",     "check": "https://replit.com/@{u}",          "url": "https://replit.com/@{u}"},
    {"name": "Pastebin",   "check": "https://pastebin.com/u/{u}",       "url": "https://pastebin.com/u/{u}"},
    {"name": "HackerNews", "check": "https://news.ycombinator.com/user?id={u}",
     "url": "https://news.ycombinator.com/user?id={u}", "missing_text": "No such user."},
    {"name": "TikTok",     "check": "https://www.tiktok.com/@{u}",      "url": "https://www.tiktok.com/@{u}",
     "missing_text": "couldn't find this account"},
    {"name": "YouTube",    "check": "https://www.youtube.com/@{u}",     "url": "https://www.youtube.com/@{u}"},
    {"name": "X / Twitter","check": "https://x.com/{u}",                "url": "https://x.com/{u}"},
    {"name": "Telegram",   "check": "https://t.me/{u}",                 "url": "https://t.me/{u}", "found_text": "tgme_page_title"},
    {"name": "Twitch",     "check": "https://m.twitch.tv/{u}",          "url": "https://www.twitch.tv/{u}",
     "missing_text": "unless you've got a time machine"},
    {"name": "Steam",      "check": "https://steamcommunity.com/id/{u}","url": "https://steamcommunity.com/id/{u}",
     "missing_text": "the specified profile could not be found"},
    {"name": "Pinterest",  "check": "https://www.pinterest.com/{u}/",   "url": "https://www.pinterest.com/{u}/",
     "missing_text": "can't find that page"},
    {"name": "SoundCloud", "check": "https://soundcloud.com/{u}",       "url": "https://soundcloud.com/{u}"},
    {"name": "Linktree",   "check": "https://linktr.ee/{u}",            "url": "https://linktr.ee/{u}"},
    {"name": "Medium",     "check": "https://medium.com/@{u}",          "url": "https://medium.com/@{u}"},
]

# platforms that gate behind a login wall and cannot be reliably checked
# without authentication - always reported as inconclusive rather than
# risking a false "found".
UNRELIABLE = {"Instagram", "Facebook"}

HANDLE_RE = re.compile(r"^@?([A-Za-z0-9_.-]{2,32})$")


def _clean(handle):
    m = HANDLE_RE.match((handle or "").strip())
    return m.group(1) if m else None


def _check_one(plat, user, timeout):
    if plat["name"] in UNRELIABLE:
        return {"platform": plat["name"], "url": plat["url"].format(u=user), "exists": None}
    check = plat["check"].format(u=user)
    req = urllib.request.Request(check, headers={"User-Agent": UA})
    need_body = bool(plat.get("missing_text") or plat.get("found_text"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            exists = True
            if need_body:
                body = r.read(20000).decode("utf-8", "ignore").lower()
                if plat.get("missing_text"):
                    exists = plat["missing_text"].lower() not in body
                if plat.get("found_text"):
                    exists = plat["found_text"].lower() in body
    except urllib.error.HTTPError as e:
        if e.code == 404:
            exists = False
        elif e.code in (403, 429, 503):
            exists = None            # blocked / rate-limited -> inconclusive
        else:
            exists = None
    except Exception:
        exists = None
    return {"platform": plat["name"], "url": plat["url"].format(u=user), "exists": exists}


def enumerate_username(handle, timeout=5, workers=14):
    """Check `handle` across all platforms concurrently."""
    user = _clean(handle)
    if not user:
        return {"handle": handle, "valid": False, "results": []}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda p: _check_one(p, user, timeout), PLATFORMS))
    found = [r for r in results if r["exists"] is True]
    return {"handle": user, "valid": True, "results": results, "found_count": len(found)}


if __name__ == "__main__":
    import json
    for h in ["torvalds", "zzq_no_such_user_9f8e7d6c5b"]:
        r = enumerate_username(h, timeout=6)
        hits = [x["platform"] for x in r["results"] if x["exists"] is True]
        print(f"{h:<30} found on: {hits or '(none / all inconclusive in sandbox)'}")
