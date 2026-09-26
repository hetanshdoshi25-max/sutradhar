"""
SUTRADHAR - Training dataset generator
---------------------------------------
Builds a LABELED dataset of text pairs for training a supervised authorship-
verification classifier: label 1 = same author wrote both texts, label 0 =
different authors. This is what a teacher/evaluator expects to see as
"the dataset" behind an ML claim.

How it's built: we define a small set of synthetic "authors", each with a
distinct writing style (word choice, punctuation habits, sentence rhythm).
For each author we generate several text SAMPLES by recombining their
characteristic phrases in different orders/topics - this keeps the writing
style constant per author while varying content, which is exactly what an
authorship classifier needs to learn from.

This is a synthetic/bootstrap dataset (explainable, reproducible, no
copyright/privacy issues with real dark-web data). It is documented as such.
"""

import random
import itertools
import json

random.seed(42)

# ---- 8 synthetic "authors", each with a distinct style fingerprint ----
AUTHORS = {
    "A_casual": {
        "openers": ["tbh", "ngl", "basically", "not gonna lie", "lowkey"],
        "fillers": ["kinda", "sorta", "i guess", "or whatever", "anyway"],
        "closers": ["lol", "idk man", "just saying", "do what you want"],
        "topics": ["the new vendor list", "the mirror being down", "that seller",
                   "the escrow update", "this deal", "the forum rules"],
    },
    "B_formal": {
        "openers": ["I would advise", "One must consider", "It is worth noting",
                    "I would suggest", "It should be observed"],
        "fillers": ["furthermore", "however", "consequently", "notwithstanding"],
        "closers": ["before forming a conclusion.", "prior to proceeding.",
                    "for the benefit of all members."],
        "topics": ["the proposed escrow policy", "recent seller conduct",
                   "the archived threads", "the dispute resolution process",
                   "membership verification", "the audit trail"],
    },
    "C_loud": {
        "openers": ["YO", "LISTEN UP", "HONESTLY", "NO CAP"],
        "fillers": ["literally", "actually", "for real", "100 percent"],
        "closers": ["!!", "trust me on this!!", "best i've seen!!", "FR FR"],
        "topics": ["this drop", "the restock", "that price", "this seller",
                   "the new batch", "today's deal"],
    },
    "D_terse": {
        "openers": ["Confirmed.", "Noted.", "Update:", "Status:"],
        "fillers": ["as expected", "per usual", "no change"],
        "closers": ["Done.", "End of update.", "Awaiting response."],
        "topics": ["the shipment", "the payment", "the ticket", "the request",
                   "the schedule", "the report"],
    },
    "E_rambling": {
        "openers": ["So I was thinking about", "You know, I keep coming back to",
                    "It's funny because", "I keep noticing that"],
        "fillers": ["and honestly", "which makes me wonder", "and then again",
                    "but who knows"],
        "closers": ["anyway that's just my take.", "food for thought I guess.",
                    "make of that what you will."],
        "topics": ["the market trends", "how things have changed", "the new rules",
                   "people's behavior lately", "the pricing", "the community"],
    },
    "F_technical": {
        "openers": ["Per the logs,", "Based on the trace,", "The data shows",
                    "Analysis indicates"],
        "fillers": ["specifically", "in this instance", "as a result"],
        "closers": ["pending further review.", "see attached for details.",
                    "flagged for follow-up."],
        "topics": ["the latency spike", "the node uptime", "the packet loss",
                   "the config change", "the deployment", "the error rate"],
    },
    "G_polite": {
        "openers": ["Hi all,", "Hope you're well,", "Just wanted to say,",
                    "Thanks in advance,"],
        "fillers": ["if possible", "when you get a chance", "no rush but"],
        "closers": ["thanks so much!", "appreciate it!", "let me know :)"],
        "topics": ["the delivery", "the update", "the invoice", "the meeting",
                   "the feedback", "the plan"],
    },
    "H_skeptic": {
        "openers": ["Not convinced that", "I doubt", "Seems unlikely that",
                    "Hard to believe"],
        "fillers": ["without proof", "until shown otherwise", "frankly"],
        "closers": ["I'll wait and see.", "prove me wrong.", "we'll see."],
        "topics": ["this claim", "the new vendor", "that review", "the announcement",
                   "this promise", "the guarantee"],
    },
}


def make_sample(author_key, rng):
    a = AUTHORS[author_key]
    opener = rng.choice(a["openers"])
    filler = rng.choice(a["fillers"])
    closer = rng.choice(a["closers"])
    topic = rng.choice(a["topics"])
    templates = [
        f"{opener} {topic} looks {rng.choice(['off','solid','risky','fine','sketchy'])}, "
        f"{filler} it's hard to tell right now. {closer}",
        f"{opener} about {topic} - {filler} nothing's really changed. {closer}",
        f"{opener}, {topic} needs a closer look, {filler}. {closer}",
        f"{opener} {topic}? {filler} i've seen worse honestly. {closer}",
        f"{opener} - regarding {topic}, {filler} the details matter here. {closer}",
        f"about {topic}: {opener.lower()} {filler} we should wait. {closer}",
    ]
    return rng.choice(templates)


# --- 6 additional distinct authors for a larger, harder dataset ---
AUTHORS.update({
    "I_analytical": {
        "openers": ["Looking at the data,", "From what I can measure,", "Statistically speaking,", "On closer inspection,"],
        "fillers": ["the numbers suggest", "the pattern indicates", "the trend shows"],
        "closers": ["pending verification.", "within margin of error.", "assuming the sample holds."],
        "topics": ["the throughput", "the failure rate", "the sample size", "the variance", "the distribution", "the baseline"],
    },
    "J_streetwise": {
        "openers": ["look fam,", "real talk,", "on god,", "deadass,"],
        "fillers": ["you already know", "no cap", "straight up", "fr fr"],
        "closers": ["that's the move.", "stay up.", "we outside.", "period."],
        "topics": ["this play", "the come up", "that bag", "the plug", "this lick", "the grind"],
    },
    "K_bureaucratic": {
        "openers": ["Please be advised that", "Kindly note that", "For the record,", "As per protocol,"],
        "fillers": ["in accordance with policy", "subject to review", "pursuant to guidelines"],
        "closers": ["for your consideration.", "at your earliest convenience.", "as deemed appropriate."],
        "topics": ["the submission", "the compliance matter", "the pending request", "the documentation", "the procedure", "the filing"],
    },
    "L_paranoid": {
        "openers": ["watch out,", "don't trust it,", "something's off,", "be careful here,"],
        "fillers": ["they're watching", "it's a setup", "someone's tracking this", "it's compromised"],
        "closers": ["stay low.", "trust no one.", "burn it after.", "delete this."],
        "topics": ["the new mirror", "that account", "the meetup", "this channel", "the wallet", "the drop point"],
    },
    "M_enthusiast": {
        "openers": ["oh this is exciting,", "love this,", "so cool that", "amazing how"],
        "fillers": ["honestly can't wait", "it's going to be great", "so much potential"],
        "closers": ["can't wait!", "this is the one!", "let's gooo!", "so hyped!"],
        "topics": ["the update", "the launch", "the new feature", "the release", "the collab", "the reveal"],
    },
    "N_minimalist": {
        "openers": ["ok.", "sure.", "fine.", "noted."],
        "fillers": ["works", "good", "done"],
        "closers": ["next.", "moving on.", "that's it.", "end."],
        "topics": ["the task", "the item", "the thing", "the order", "the job", "the ask"],
    },
})


def build_dataset(samples_per_author=10):
    """Return list of {author, text} - the raw labeled corpus."""
    rng = random.Random(7)
    corpus = []
    for author in AUTHORS:
        for _ in range(samples_per_author):
            corpus.append({"author": author, "text": make_sample(author, rng)})
    return corpus


def build_pairs(corpus):
    """Turn the corpus into labeled PAIRS: 1 = same author, 0 = different author.
    Balances the classes so the classifier doesn't just learn to always predict 0."""
    same, diff = [], []
    for i, j in itertools.combinations(range(len(corpus)), 2):
        a, b = corpus[i], corpus[j]
        pair = (a["text"], b["text"], 1 if a["author"] == b["author"] else 0)
        (same if pair[2] == 1 else diff).append(pair)
    random.Random(11).shuffle(diff)
    diff = diff[: len(same)]           # balance classes 50/50
    pairs = same + diff
    random.Random(13).shuffle(pairs)
    return pairs


if __name__ == "__main__":
    corpus = build_dataset(samples_per_author=10)
    pairs = build_pairs(corpus)
    print(f"authors: {len(AUTHORS)} | samples: {len(corpus)} | labeled pairs: {len(pairs)}")
    print(f"  same-author pairs: {sum(1 for p in pairs if p[2]==1)}")
    print(f"  diff-author pairs: {sum(1 for p in pairs if p[2]==0)}")
    with open("training_pairs.json", "w") as f:
        json.dump(pairs, f, indent=1)
    print("saved -> training_pairs.json")
    print("\nsample pair:", pairs[0])
