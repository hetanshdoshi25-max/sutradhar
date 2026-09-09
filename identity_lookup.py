"""
SUTRADHAR - Identity lookup (email / phone)
-------------------------------------------
Two legal, reliable OSINT lookups:

  EMAIL -> Gravatar public profile. Hashing an email and querying Gravatar's
           public API can return a real name, photo and the social accounts
           the owner linked themselves. This is public data the person chose
           to publish - no scraping, no auth bypass.

  PHONE -> carrier / region / line-type via Google's libphonenumber metadata
           (offline). This does NOT find "which apps a number is on" - that
           isn't reliably or legally doable - it validates and geolocates the
           number, which is the real, defensible phone-OSINT capability.

Breach lookup (email -> which data breaches) needs a HaveIBeenPwned API key;
plug your key into hibp_note() to enable it.
"""

import hashlib
import json
import re
import urllib.request
import urllib.error

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
UA = "Mozilla/5.0 (compatible; SUTRADHAR-OSINT/1.0)"


def _is_email(v):
    return bool(EMAIL_RE.match((v or "").strip()))


def lookup_email(email):
    email = email.strip().lower()
    md5 = hashlib.md5(email.encode()).hexdigest()
    out = {
        "kind": "email", "value": email,
        "username_guess": email.split("@")[0],
        "gravatar": {"found": False},
        "avatar_url": f"https://www.gravatar.com/avatar/{md5}?d=404",
    }
    try:
        req = urllib.request.Request(
            f"https://www.gravatar.com/{md5}.json",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        entry = (data.get("entry") or [{}])[0]
        out["gravatar"] = {
            "found": True,
            "name": (entry.get("name") or {}).get("formatted") or entry.get("displayName"),
            "location": entry.get("currentLocation"),
            "about": entry.get("aboutMe"),
            "photo": (entry.get("thumbnailUrl") or out["avatar_url"]),
            "accounts": [
                {"service": a.get("shortname") or a.get("display"),
                 "url": a.get("url"), "username": a.get("username"),
                 "verified": a.get("verified") in (True, "true")}
                for a in (entry.get("accounts") or [])
            ],
        }
    except urllib.error.HTTPError as e:
        out["gravatar"] = {"found": False, "status": e.code}
    except Exception as e:
        out["gravatar"] = {"found": False, "error": type(e).__name__}
    return out


def lookup_phone(phone):
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone, number_type, PhoneNumberType
    types = {
        PhoneNumberType.MOBILE: "Mobile",
        PhoneNumberType.FIXED_LINE: "Fixed line",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed / mobile",
        PhoneNumberType.VOIP: "VoIP",
        PhoneNumberType.TOLL_FREE: "Toll-free",
    }
    out = {"kind": "phone", "value": phone, "valid": False}
    try:
        n = phonenumbers.parse(phone, None)   # phone must include +country code
        out["valid"] = phonenumbers.is_valid_number(n)
        out["region"] = geocoder.description_for_number(n, "en") or None
        out["carrier"] = carrier.name_for_number(n, "en") or None
        out["timezones"] = list(timezone.time_zones_for_number(n))
        out["line_type"] = types.get(number_type(n), "Unknown")
        out["e164"] = phonenumbers.format_number(
            n, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        out["error"] = f"Could not parse - include country code, e.g. +91... ({type(e).__name__})"
    return out


def identity_lookup(value):
    value = (value or "").strip()
    if _is_email(value):
        return lookup_email(value)
    if value.startswith("+") or re.fullmatch(r"[\d\s()+-]{7,}", value):
        return lookup_phone(value)
    return {"kind": "unknown", "value": value,
            "error": "Enter an email, or a phone number with country code (+91...)."}


if __name__ == "__main__":
    print(json.dumps(lookup_phone("+919876543210"), indent=2))
