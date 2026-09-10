"""
SUTRADHAR - web backend (FastAPI)
---------------------------------
Serves the frontend and exposes one endpoint:

    POST /analyze   body: { "personas": [ {alias, site, text}, ... ],
                            "threshold": 0.55 }
            -> returns the knowledge graph (nodes, edges, attributions)

Run:
    pip install -r requirements.txt
    python app.py
    open http://localhost:8000
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from correlation import build_graph
from report_pdf import build_report_pdf
from export_data import build_json_export, build_csv_export
from username_enum import enumerate_username
from identity_lookup import identity_lookup
import audit_log
import monitor
from sample_personas import PERSONAS

app = FastAPI(title="SUTRADHAR")

BASE = Path(__file__).parent
STATIC = BASE / "static"


# ---- request/response shapes ----
class Persona(BaseModel):
    alias: str
    site: str = ""
    text: str
    hours: list[int] = []


class AnalyzeRequest(BaseModel):
    personas: list[Persona]
    threshold: float = 0.55


class EnumRequest(BaseModel):
    handle: str


class LookupRequest(BaseModel):
    value: str


@app.post("/lookup")
def lookup(req: LookupRequest):
    """Identity lookup: email -> Gravatar profile, phone -> carrier/region."""
    return identity_lookup(req.value)


@app.post("/enumerate")
def enumerate_handle(req: EnumRequest):
    """Check a username across public platforms (passive OSINT)."""
    return enumerate_username(req.handle)


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # need at least 2 personas to find a link
    personas = [p.model_dump() for p in req.personas if p.text.strip()]
    if len(personas) < 2:
        return {"nodes": [], "edges": [], "attributions": [],
                "error": "Add at least two personas with text."}
    result = build_graph(personas, threshold=req.threshold)
    audit_log.record("analyze",
        f"{len(personas)} personas, threshold {req.threshold}, "
        f"{len(result.get('attributions', []))} attribution(s) found")
    return result


@app.get("/sample")
def sample():
    """Hand the built-in demo personas to the frontend."""
    return {"personas": PERSONAS}


@app.post("/report/pdf")
def report_pdf(req: AnalyzeRequest):
    """Build the graph and return a downloadable case-file PDF."""
    personas = [p.model_dump() for p in req.personas if p.text.strip()]
    if len(personas) < 2:
        return Response(content=b"Add at least two personas.", status_code=400)
    g = build_graph(personas, threshold=req.threshold)
    pdf = build_report_pdf(g, personas, req.threshold)
    audit_log.record("export_pdf",
        f"case file for {len(g.get('attributions', []))} attribution(s), "
        f"{len(personas)} personas")
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sutradhar_case_file.pdf"},
    )


@app.get("/audit")
def audit():
    """Tamper-evident chain-of-custody log for every analysis/export action."""
    ok, broke_at = audit_log.verify_chain()
    return {"entries": audit_log.get_log(), "chain_valid": ok, "broke_at_seq": broke_at}


@app.post("/export/json")
def export_json(req: AnalyzeRequest):
    personas = [p.model_dump() for p in req.personas if p.text.strip()]
    if len(personas) < 2:
        return Response(content=b"Add at least two personas.", status_code=400)
    g = build_graph(personas, threshold=req.threshold)
    data = build_json_export(g, req.threshold)
    audit_log.record("export_json", f"{len(g.get('attributions', []))} attribution(s)")
    return Response(content=data, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=sutradhar_export.json"})


@app.post("/export/csv")
def export_csv(req: AnalyzeRequest):
    personas = [p.model_dump() for p in req.personas if p.text.strip()]
    if len(personas) < 2:
        return Response(content=b"Add at least two personas.", status_code=400)
    g = build_graph(personas, threshold=req.threshold)
    data = build_csv_export(g)
    audit_log.record("export_csv", f"{len(g.get('edges', []))} row(s)")
    return Response(content=data, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=sutradhar_export.csv"})


@app.post("/monitor/start")
def monitor_start():
    """Begin autonomous polling of configured sources (demo feed)."""
    return monitor.start(interval_sec=6)


@app.post("/monitor/stop")
def monitor_stop():
    return monitor.stop()


@app.get("/monitor/status")
def monitor_status():
    return monitor.status()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


# serve /static/* (css, js if we split later)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
