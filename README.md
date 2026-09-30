# SUTRADHAR — Dark-Web Threat-Actor De-anonymization

**SIH 2026 · PS SIH26151 · NTRO · Team INNOVEXA**

SUTRADHAR is a multi-signal attribution engine that links anonymous dark-web
personas to a single suspected identity, scores the confidence of that link
with explainable evidence, and produces a court-ready case file — all
running as a live, working prototype.

**Live prototype:** https://web-production-9880e1.up.railway.app
**Landing page:** https://sutradhar-mu.vercel.app

> Authorized-investigator demo. Runs against a simulated, self-hosted
> marketplace network — never a real `.onion` site — to stay within legal
> boundaries. See "Live crawling" below.

---

## The 8 signals

| # | Signal | What it does |
|---|---|---|
| 1 | **Stylometry** | 19-feature writing fingerprint — char n-gram TF-IDF, function words, hapax legomena, sentence-length variability, lexical richness |
| 2 | **Cognitive Fingerprint** | 7-D behavioural-reasoning vector (hedging, certainty, causal density, risk/opportunity framing, deductive lean) — survives AI-rephrasing, unlike surface stylometry |
| 3 | **Temporal** | 24-bin activity histogram + circadian shape (spread, peakedness, nocturnal index, regularity) |
| 4 | **Persona Reuse** | 10 identifier types — email, BTC, ETH, Monero, PGP, onion, Session ID, Tox ID, Jabber/XMPP, handle |
| 5 | **OPSEC Exposure** | Self-leaked contact details scored by severity (Critical to Low) |
| 6 | **Crypto Flow** | UTXO co-spend clustering; cash-out traced to KYC exchange, mixer, or OFAC-sanctioned VASP |
| 7 | **Infrastructure** | 4 misconfig classes matching an onion service to a clearnet host (server-status leak, SSL cert reuse, default banner, descriptor overlap) |
| 8 | **Evasion Meta-Signal** | Flags too-clean personas — zero-identifier discipline, uniform sentence structure, scheduled posting — as a trained-operator tell |

Plus **trust-link mapping** (vouch / scam-flag / co-mention edges between
personas) and **visual match** (perceptual-hash avatar matching across aliases).

## ML classifier

RandomForest trained on **58,240 labeled pairs** across **14 synthetic
authors**, using **26 engineered features** (stylometric + cognitive
differences and similarities). **94.1% accuracy** on held-out test data,
compared against Logistic Regression, Gradient Boosting, and a 3-model
voting ensemble; RandomForest won on accuracy and was deployed.

## Live crawling — real, but legally scoped

The crawler performs genuine HTTP requests, HTML parsing, and breadth-first
link discovery, no hardcoded data. Its target is a **61-page simulated
marketplace network** (5 distinct markets, built for this project) rather
than a live `.onion` site, because unauthorized dark-web access carries
real legal risk. In production, the same crawler points at authorized
OSINT feeds, a config change, not an architecture change.

## Persistent storage & analytical front end

Every analysis is saved to a local **SQLite database** (`storage.py`),
actor profiles, category, source, last-scan date, and links survive
restarts. The console's **Actor Database** panel queries stored actors by
category or timeline, satisfying the "query across a chosen timeline"
requirement. Autonomous monitoring polls sources on a schedule and
persists newly discovered actors on its own.

## AI, encryption, and audit trail

- **Local offline AI analyst** (`local_ai.py`), auto-triage and
  plain-language narratives generated from signal evidence, no external
  API call, fully air-gapped.
- **AES-256 encryption vault** (`crypto_vault.py`), Fernet (AES-CBC +
  HMAC-SHA256), PBKDF2-HMAC-SHA256 at 390,000 iterations. The console's
  "Prove Encryption" panel shows plaintext vs. on-disk ciphertext live.
- **SHA-256 hash-chained audit log** (`audit_log.py`), every action is
  cryptographically linked; tampering is detectable, not silently accepted.

## Exports

One click produces:
- **Court-ready PDF** — cover, executive summary, legal basis (Bharatiya
  Sakshya Adhiniyam Sec 63, IT Act 65B, ISO/IEC 27037), per-signal
  methodology, per-actor evidence table, audit trail, certification.
- **JSON** — full attribution schema for I4C dashboards / SIEM integration.
- **CSV** — one row per link plus a per-actor profile block (alias,
  category, source, OPSEC/evasion level, identifiers, last-scan date).

## Console

A 3D investigation console (Three.js), glowing knowledge-graph nodes,
curved evidence-linked edges, click-through evidence panels, live crawl
progress, autonomous-monitoring feed, OSINT footprint scanner, identity
lookup, visual-match scanner, and the actor database/timeline query panel.

---

## Folder structure

```
sutradhar/
├── app.py                 # FastAPI backend, serves the console + all endpoints
├── correlation.py         # fuses all 8 signals into the knowledge graph
├── stylometry.py          # signal 1, writing-style fingerprint
├── cognitive.py           # signal 2, behavioural-reasoning fingerprint
├── temporal.py            # signal 3, activity-pattern fingerprint
├── persona_reuse.py       # signal 4, identifier extraction (10 types)
├── opsec.py               # signal 5, leaked-identifier exposure scoring
├── crypto_flow.py         # signal 6, wallet clustering + cash-out risk
├── infra.py               # signal 7, onion-to-clearnet misconfig matching
├── evasion.py             # signal 8, anti-forensic discipline meta-signal
├── trust_links.py         # vouch / scam-flag / co-mention relationship graph
├── image_match.py         # perceptual-hash avatar/visual matching
├── storage.py              # SQLite persistence + timeline/category query
├── local_ai.py              # offline rule-based AI analyst
├── crypto_vault.py         # AES-256 encryption vault + live proof
├── audit_log.py             # SHA-256 hash-chained audit trail
├── monitor.py                # autonomous source polling
├── crawler.py                 # real HTTP crawler (breadth-first)
├── build_simsite.py          # generates the 61-page simulated marketplace network
├── train_model.py             # trains + compares the ML classifiers
├── build_dataset.py           # synthetic 14-author training corpus generator
├── author_model.pkl            # trained RandomForest model (94.1% accuracy)
├── training_pairs.json         # 58,240 labeled training pairs
├── report_pdf.py                # court-ready PDF generator
├── export_data.py                # CSV / JSON export
├── username_enum.py              # public-platform username OSINT
├── identity_lookup.py             # email/phone lookup (Gravatar, phonenumbers)
├── sample_personas.py              # demo dataset
├── test_engine.py                   # CLI smoke test
├── requirements.txt
├── Procfile / railway.json / runtime.txt   # Railway deployment config
├── simsite/                           # generated simulated marketplace (61 pages)
├── static/
│   ├── index.html                     # the 3D investigation console
│   └── lib/three.min.js               # bundled for offline use
└── site/
    └── index.html                      # landing page (Vercel)
```

## Run it locally

```bash
pip install -r requirements.txt        # add --break-system-packages if needed
python app.py
```
Open **http://localhost:8000** in a browser. The simulated marketplace
network starts automatically in the background on port 8010.

## Deploy

Live on **Railway** (backend, `Procfile` + `railway.json`) and **Vercel**
(landing page, `site/index.html`). Push to `main` auto-deploys both.

## Legal & ethical scope

- No real dark-web site is crawled or accessed.
- All demo personas and marketplace content are synthetic/fabricated.
- Visual match compares only operator-published avatars, never facial
  recognition against live camera feeds or external databases.
- Encryption, audit-logging, and RBAC design follow Bharatiya Sakshya
  Adhiniyam Sec 63, IT Act Sec 65B, and ISO/IEC 27037.
