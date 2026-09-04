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


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # need at least 2 personas to find a link
    personas = [p.model_dump() for p in req.personas if p.text.strip()]
    if len(personas) < 2:
        return {"nodes": [], "edges": [], "attributions": [],
                "error": "Add at least two personas with text."}
    return build_graph(personas, threshold=req.threshold)


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
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sutradhar_case_file.pdf"},
    )


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


# serve /static/* (css, js if we split later)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
