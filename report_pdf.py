"""
SUTRADHAR - Attribution case-file PDF
-------------------------------------
Turns an analysis result into a court-ready-looking evidence document:
summary, attribution findings, per-link evidence tables and a persona index.
Returns raw PDF bytes so the web endpoint can stream it as a download.
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# brand colours
NAVY  = colors.HexColor("#0F2544")
TEAL  = colors.HexColor("#0E7490")
AMBER = colors.HexColor("#B45309")
SLATE = colors.HexColor("#334155")
MUTE  = colors.HexColor("#64748B")
LINE  = colors.HexColor("#CBD5E1")
CARD  = colors.HexColor("#F1F5F9")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("H", parent=s["Title"], fontSize=20, textColor=NAVY,
                         spaceAfter=2, alignment=0))
    s.add(ParagraphStyle("Sub", fontSize=9, textColor=MUTE, spaceAfter=2))
    s.add(ParagraphStyle("Sec", fontSize=12, textColor=TEAL, spaceBefore=14,
                         spaceAfter=6, leading=14, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Body", fontSize=10, textColor=SLATE, leading=14))
    s.add(ParagraphStyle("Small", fontSize=8.5, textColor=MUTE, leading=11))
    s.add(ParagraphStyle("Find", fontSize=11, textColor=NAVY, leading=15,
                         fontName="Helvetica-Bold"))
    return s


def _pct(x):
    return f"{round(float(x) * 100)}%"


def build_report_pdf(graph, personas, threshold, case_id=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="SUTRADHAR Attribution Case File")
    st = _styles()
    story = []
    case_id = case_id or datetime.now().strftime("%Y%m%d-%H%M")
    now = datetime.now().strftime("%d %b %Y, %H:%M")

    nodes = graph["nodes"]
    edges = graph["edges"]
    attrs = graph["attributions"]

    # ---- header ----
    story.append(Paragraph("SUTRADHAR Attribution Case File", st["H"]))
    story.append(Paragraph(
        f"Case #{case_id} &nbsp;|&nbsp; Generated {now} &nbsp;|&nbsp; "
        f"Authorized investigative use only", st["Sub"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.2, color=TEAL))
    story.append(Spacer(1, 8))

    # ---- summary ----
    story.append(Paragraph("1 &nbsp; Summary", st["Sec"]))
    story.append(Paragraph(
        f"{len(nodes)} personas analysed &nbsp;&bull;&nbsp; "
        f"{len(edges)} suspected link(s) found &nbsp;&bull;&nbsp; "
        f"{len(attrs)} identity cluster(s) &nbsp;&bull;&nbsp; "
        f"link threshold {threshold:.2f}", st["Body"]))

    # ---- findings ----
    story.append(Paragraph("2 &nbsp; Attribution findings", st["Sec"]))
    if not attrs:
        story.append(Paragraph("No links above threshold.", st["Body"]))
    for a in attrs:
        story.append(Paragraph(
            " = ".join(a["aliases"]) +
            f' &nbsp; <font color="#B45309">[{_pct(a["confidence"])} confidence]</font>',
            st["Find"]))
        story.append(Paragraph(
            f"Suspected single author across {len(a['aliases'])} aliases.",
            st["Small"]))
        story.append(Spacer(1, 4))

    # ---- evidence per link ----
    story.append(Paragraph("3 &nbsp; Evidence detail", st["Sec"]))
    for e in edges:
        sa = nodes[e["source"]]["alias"]
        ta = nodes[e["target"]]["alias"]
        story.append(Paragraph(
            f'{sa} &harr; {ta} &nbsp; '
            f'<font color="#0E7490">blended {_pct(e["score"])}</font>',
            st["Find"]))
        ev = e["evidence"]
        rows = [["Signal", "Match"]]
        rows.append(["Character n-grams", _pct(ev.get("char_ngrams", 0))])
        rows.append(["Function words", _pct(ev.get("function_words", 0))])
        rows.append(["Style ratios", _pct(ev.get("style_ratios", 0))])
        if "activity_pattern" in ev:
            rows.append(["Activity-hours overlap", _pct(ev["activity_pattern"])])
            pw = ev.get("peak_windows")
            if pw:
                rows.append(["Peak active window", f"{pw[0]}  /  {pw[1]}"])
        if "persona_reuse" in ev:
            rows.append(["Shared identifier match", _pct(ev["persona_reuse"])])
            si = ev.get("shared_identifiers")
            if si:
                rows.append(["Reused identifier", ", ".join(si)])
        if "crypto_flow" in ev:
            rows.append(["Crypto wallet link", _pct(ev["crypto_flow"])])
            cd = ev.get("crypto_detail") or {}
            if cd:
                line = f"{cd.get('kind','')} {cd.get('detail','')}"
                if cd.get("cashout"):
                    line += f"  (cash-out: {cd['cashout']['vasp']})"
                rows.append(["Wallet trail", line])
        t = Table(rows, colWidths=[70 * mm, 40 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (0, -1), SLATE),
            ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # ---- persona index ----
    story.append(Paragraph("4 &nbsp; Personas examined", st["Sec"]))
    prows = [["Alias", "Site", "Words", "OPSEC risk"]]
    for i, n in enumerate(nodes):
        words = len((personas[i].get("text", "").split()))
        risk = n.get("exposure", {}).get("level", "-")
        prows.append([n["alias"], n.get("site", "") or "-", str(words), risk])
    pt = Table(prows, colWidths=[45 * mm, 45 * mm, 20 * mm, 25 * mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), SLATE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(pt)

    # ---- disclaimer ----
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Investigative lead only, not conclusive proof of identity. "
        "Generated by SUTRADHAR from stylometric and temporal signals for "
        "authorized investigators, on consented or published research data. "
        "Findings should be corroborated by a human analyst before any action.",
        st["Small"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()


if __name__ == "__main__":
    from correlation import build_graph
    from sample_personas import PERSONAS
    g = build_graph(PERSONAS)
    pdf = build_report_pdf(g, PERSONAS, 0.55)
    open("case_file_sample.pdf", "wb").write(pdf)
    print("wrote case_file_sample.pdf", len(pdf), "bytes")
