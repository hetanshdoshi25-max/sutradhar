# SUTRADHAR — Dark web threat-actor de-anonymization (prototype)

Links anonymous personas to a single suspected author using **stylometry**
(writing-style fingerprinting), then shows the result as a knowledge graph
with a confidence score and an explainable evidence breakdown.

> Authorized-investigator demo. Uses only fabricated/consented text.
> Not for de-anonymizing real people without consent.

## Folder structure
```
sutradhar/
├── stylometry.py        # the fingerprint engine (3 feature groups)
├── correlation.py       # scores -> graph nodes / edges / clusters
├── sample_personas.py   # demo data (2 hidden author-pairs)
├── test_engine.py       # CLI proof it works
├── app.py               # FastAPI backend (serves UI + /analyze)
├── requirements.txt
└── static/
    ├── index.html       # the investigation console (graph UI)
    └── lib/
        └── vis-network.min.js   # graph library, bundled for offline use
```

## Run it
```bash
pip install -r requirements.txt        # add --break-system-packages if needed
python app.py
```
Open **http://localhost:8000** in a browser.

- **Load sample** → fills in the 5 demo personas
- **Analyze ▶** → draws the graph; same-author aliases share a colour
- Click any **link** → see the evidence (char n-grams / function words / style)
- **+ Add person** → paste live text (e.g. an audience volunteer) and re-analyze
- **Link threshold** slider → how strict a match must be to draw a link

## CLI check (no browser)
```bash
python test_engine.py     # prints the similarity matrix + verdicts
```

## Demo tip
Stylometry needs ~40+ words per person to be reliable. The input boxes show a
word counter and warn below 40. Keep a pre-recorded run of the sample data as a
backup in case a live volunteer writes too little.
