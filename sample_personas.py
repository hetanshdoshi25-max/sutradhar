"""
Synthetic personas for the SUTRADHAR demo.

IMPORTANT: fabricated demo text, not real data. Some personas share a hidden
'author' (same writing quirks AND similar active hours under different
aliases) so we can prove the engine links them. 'ground_truth' records who
really wrote what - used only to check accuracy, never shown to the engine.

Two independent signals are baked in per author:
  - writing style (casual / formal / loud)
  - active hours   (evening / daytime / late-night -> hints a timezone)

'hours' = the hours of day (0-23) at which that persona tends to post.
Live-typed personas won't have this, and the system falls back to
stylometry alone for them.
"""

PERSONAS = [
    {
        "alias": "shadowfox",
        "site": "ForumA",
        "hours": [20, 21, 22, 23, 19, 22, 21, 23, 0, 20, 22, 21],
        "text": (
            "tbh the new vendor list looks kinda sketchy... basically half of "
            "them have no reviews and the other half just copy paste the same "
            "description. ngl i wouldnt trust it. been around long enough to know "
            "when something feels off and this feels off. anyway just my two cents "
            "do what you want with it lol. hit me on tg @vendmirror if u need the list"
        ),
    },
    {
        "alias": "nightcrawler",
        "site": "ForumB",
        "hours": [21, 22, 23, 20, 22, 23, 0, 21, 20, 22, 23, 19],
        "text": (
            "basically the mirror been down for like three days now... tbh im not "
            "even surprised at this point. ngl the admins keep saying its fixed but "
            "then it breaks again. been checking every morning and nothing. anyway "
            "if anyone has a working link drop it here i guess lol. same as always @vendmirror on tg"
        ),
    },
    {
        "alias": "cipher9",
        "site": "ForumA",
        "hours": [9, 10, 11, 12, 13, 14, 11, 12, 10, 13, 9, 14],
        "text": (
            "I would advise considerable caution before proceeding; the reputation "
            "of that particular seller has declined significantly over recent weeks. "
            "Furthermore, several established members have raised legitimate concerns "
            "regarding delivery times. However, one must acknowledge that isolated "
            "incidents do not necessarily indicate systemic failure. I recommend "
            "reviewing the archived threads before forming a conclusion. For verification, my PGP is 0x9F3A21BC."
        ),
    },
    {
        "alias": "m4trix",
        "site": "ForumC",
        "hours": [10, 11, 12, 13, 10, 11, 14, 12, 9, 13, 11, 10],
        "text": (
            "The proposed change to the escrow policy warrants careful examination; "
            "it introduces both advantages and notable risks. Furthermore, the "
            "administration has not clarified how disputes will be handled under the "
            "new terms. However, if implemented transparently, it could improve trust "
            "considerably. I would suggest that members request written clarification "
            "before endorsing the update. Signed messages carry PGP key 0x9F3A21BC as always."
        ),
    },
    {
        "alias": "vypr",
        "site": "ForumB",
        "hours": [1, 2, 3, 0, 23, 2, 1, 3, 0, 2, 1, 23],
        "text": (
            "YO this drop is INSANE!! grabbed mine already and its FIRE!! honestly "
            "cant believe the price!! everyone sleeping on this seller BIG mistake!! "
            "restock coming friday DONT miss it!! trust me on this one!! best i seen "
            "all year FR. dm me 9876543210 or vyprdeals@proton.me for early access"
        ),
    },
]

# who actually wrote each alias (index-aligned with PERSONAS)
GROUND_TRUTH = ["A", "A", "B", "B", "C"]
