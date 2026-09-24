"""
SUTRADHAR - Attribution case-file PDF (forensic report format)
-----------------------------------------------------------------
Produces a formal, multi-section forensic-style report: cover page,
executive summary, legal basis, methodology (with theory for each signal),
case overview, attribution findings, detailed evidence analysis, audit
trail (chain-of-custody), limitations and a certification block.

Returns raw PDF bytes so the web endpoint can stream it as a download.
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    PageBreak, ListFlowable, ListItem, KeepTogether
)
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

import audit_log

# ---- palette ----
NAVY  = colors.HexColor("#0F2544")
TEAL  = colors.HexColor("#0E7490")
AMBER = colors.HexColor("#B45309")
SLATE = colors.HexColor("#334155")
MUTE  = colors.HexColor("#64748B")
LINE  = colors.HexColor("#CBD5E1")
CARD  = colors.HexColor("#F1F5F9")
GREEN = colors.HexColor("#15803D")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("CoverTitle", fontSize=30, textColor=NAVY, fontName="Helvetica-Bold",
                         alignment=TA_CENTER, spaceAfter=6, leading=34))
    s.add(ParagraphStyle("CoverSub", fontSize=13, textColor=TEAL, fontName="Helvetica-Bold",
                         alignment=TA_CENTER, spaceAfter=4))
    s.add(ParagraphStyle("CoverMeta", fontSize=10, textColor=SLATE, alignment=TA_CENTER, leading=15))
    s.add(ParagraphStyle("Classify", fontSize=9, textColor=colors.white, alignment=TA_CENTER,
                         fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("H", fontSize=17, textColor=NAVY, fontName="Helvetica-Bold",
                         spaceBefore=0, spaceAfter=2))
    s.add(ParagraphStyle("Sub", fontSize=9, textColor=MUTE, spaceAfter=2))
    s.add(ParagraphStyle("Sec", fontSize=13, textColor=TEAL, spaceBefore=16,
                         spaceAfter=6, leading=16, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("SubSec", fontSize=10.5, textColor=NAVY, spaceBefore=9,
                         spaceAfter=3, leading=13, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Body", fontSize=9.7, textColor=SLATE, leading=14.5,
                         spaceAfter=6, alignment=TA_JUSTIFY))
    s.add(ParagraphStyle("BodyB", parent=s["Body"], leftIndent=12))
    s.add(ParagraphStyle("Small", fontSize=8.3, textColor=MUTE, leading=11.5))
    s.add(ParagraphStyle("Find", fontSize=10.5, textColor=NAVY, leading=14,
                         fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Foot", fontSize=7.5, textColor=MUTE))
    return s


def _pct(x):
    return f"{round(float(x) * 100)}%"


def _bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=14, value="•") for t in items],
        bulletType="bullet", leftIndent=6, spaceAfter=6)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, doc.pagesize[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTE)
    canvas.drawString(18 * mm, 10 * mm, "SUTRADHAR Forensic Attribution Report - Authorized Investigative Use Only")
    canvas.drawRightString(doc.pagesize[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


SIGNAL_THEORY = [
    ("1. Stylometric Analysis (Writing Style)",
     "Every author possesses an idiolect - an unconscious, largely stable set of linguistic habits "
     "(punctuation frequency, function-word usage, sentence rhythm, orthographic quirks) that persists "
     "across pseudonyms. The system decomposes each document into three independent feature families - "
     "character n-gram distributions, function-word frequency vectors, and structural style ratios - and "
     "computes pairwise cosine similarity across each family using a TF-IDF weighted vector space model. "
     "This approach is consistent with established forensic-linguistics methodology used in authorship "
     "verification research (cf. PAN-CLEF benchmark tasks)."),
    ("2. Cognitive Fingerprint (Behavioural Reasoning Signature)",
     "Surface stylometry can be defeated by an operator routing text through an AI rewriter, which alters "
     "word choice while preserving the author's underlying reasoning. This signal therefore fingerprints "
     "how a subject reasons rather than which words they select - a property substantially more robust to "
     "paraphrase. Seven behavioural dimensions are measured as length-normalized rates: hedging versus "
     "certainty language, causal-reasoning density, argumentative contrast, risk versus opportunity framing, "
     "and deductive (conclusion-first) versus inductive (evidence-first) argument order. These form a "
     "seven-dimensional behavioural vector compared by cosine similarity. This directly implements the "
     "problem statement's requirement for behavioural profiling of rebranded or migrated personas, and is "
     "offered as corroborating evidence explicitly more paraphrase-resistant than surface style, not as an "
     "infallible indicator."),
    ("2. Temporal Behavioural Analysis",
     "Human activity follows circadian patterns that are difficult to consciously suppress. The system "
     "constructs a 24-hour posting-frequency histogram per persona and measures distributional overlap "
     "via cosine similarity. Concordant active-hour windows across ostensibly distinct personas constitute "
     "corroborating evidence of common operator identity, and the peak window additionally provides a "
     "probabilistic timezone indicator."),
    ("3. Persona-Reuse Detection (Hard Identifiers)",
     "Operational identifiers - PGP key fingerprints, e-mail addresses, cryptocurrency wallet strings, and "
     "platform handles - are extracted via pattern recognition and cross-referenced across personas. Unlike "
     "the probabilistic signals above, a shared hard identifier constitutes direct, non-circumstantial "
     "evidence of common ownership and is accordingly weighted with a high confidence floor."),
    ("4. OPSEC Exposure Assessment",
     "The system audits each persona's own text for inadvertent operational-security failures - leaked "
     "e-mail addresses, telephone numbers, or wallet strings - and derives a composite exposure-risk rating "
     "(Low / Medium / High / Critical). This does not contribute to inter-persona linkage but independently "
     "flags high-value investigative targets."),
    ("5. Cryptocurrency Flow Analysis",
     "Wallet addresses referenced in persona text are checked against a chain-analysis reference ledger for "
     "(a) common-entity clustering - distinct addresses attributable to a single controlling party through "
     "co-spend heuristics - and (b) terminal cash-out attribution, distinguishing KYC-regulated exchange "
     "off-ramps (subpoena-traceable) from mixing services (an independent risk indicator). In the present "
     "prototype this operates against a representative reference dataset; production deployment would "
     "integrate a licensed chain-analysis API (e.g., Chainalysis, GraphSense)."),
    ("6. Infrastructure Fingerprint Correlation",
     "Hidden services, notwithstanding Tor's network-layer anonymity, are frequently exposed by operator "
     "misconfiguration of the underlying server. The system models four such misconfiguration classes: "
     "(a) exposed server-status or debug endpoints revealing internal network details; (b) TLS certificates "
     "shared between the hidden service and an indexed clearnet domain; (c) default, unmodified service "
     "banners that are fingerprintable and often indicative of shared hosting; and (d) hidden-service "
     "descriptor inconsistencies, such as shared introduction-point sets, indicating common infrastructure. "
     "Where two onion services exhibit a shared misconfiguration signature, common server infrastructure - "
     "and by extension common operatorship - is inferred. This technique mirrors documented law-enforcement "
     "methodology (e.g., the 2013 Silk Road server identification). The present prototype operates against "
     "a representative reference ledger; production deployment would integrate live Shodan/Censys/OnionScan "
     "telemetry."),
    ("7. Evasion Confidence Assessment (Meta-Signal)",
     "Where the preceding six signals evaluate what a persona has left behind, this meta-signal evaluates "
     "the inverse: the degree to which a persona exhibits deliberate anti-forensic discipline. Three "
     "indicators are assessed - the absence of any leaked identifier despite substantial text volume; "
     "abnormally low variance in sentence length, consistent with deliberate stylistic neutralization or "
     "AI-assisted rewriting; and near-zero variance in posting-hour distribution, consistent with scheduled "
     "or automated posting rather than organic human activity. The system treats elevated discipline itself "
     "as an investigative signal: a persona scored 'Professional' on this metric warrants prioritized "
     "attention as a likely trained operator, independent of whether it links to any other persona."),
]


def build_report_pdf(graph, personas, threshold, case_id=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=20 * mm,
                            title="SUTRADHAR Forensic Attribution Report")
    st = _styles()
    story = []
    case_id = case_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    now_full = datetime.now().strftime("%d %B %Y, %H:%M:%S")

    nodes = graph["nodes"]
    edges = graph["edges"]
    attrs = graph["attributions"]

    # ================= COVER PAGE =================
    story.append(Spacer(1, 8))
    story.append(Table([[Paragraph("AUTHORIZED INVESTIGATIVE USE ONLY", st["Classify"])]],
                       colWidths=[174 * mm],
                       style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])))
    story.append(Spacer(1, 60))
    story.append(Paragraph("SUTRADHAR", st["CoverTitle"]))
    story.append(Paragraph("MULTI-SIGNAL DARK WEB THREAT-ACTOR", st["CoverSub"]))
    story.append(Paragraph("ATTRIBUTION REPORT", st["CoverSub"]))
    story.append(Spacer(1, 40))
    story.append(HRFlowable(width="60%", thickness=1, color=LINE, hAlign="CENTER"))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"Case Reference&nbsp;&nbsp;<b>{case_id}</b><br/>"
        f"Report Generated&nbsp;&nbsp;<b>{now_full}</b><br/>"
        f"Problem Statement&nbsp;&nbsp;<b>SIH26151 - Dark Web Threat Actor De-anonymization</b><br/>"
        f"Prepared For&nbsp;&nbsp;<b>National Technical Research Organisation (NTRO)</b>",
        st["CoverMeta"]))
    story.append(Spacer(1, 60))
    story.append(Paragraph(
        "This document is generated by an automated multi-signal correlation system for the exclusive "
        "use of authorized law-enforcement and intelligence personnel. It constitutes an investigative "
        "lead, not conclusive proof of identity, and must be corroborated by a qualified human analyst "
        "prior to any operational or judicial action.",
        st["CoverMeta"]))
    story.append(PageBreak())

    # ================= 1. EXECUTIVE SUMMARY =================
    story.append(Paragraph("1. Executive Summary", st["Sec"]))
    story.append(Paragraph(
        f"This report documents an automated attribution analysis conducted by the SUTRADHAR platform on "
        f"{len(nodes)} distinct dark-web personas. The system applies six independent, methodologically "
        f"distinct signal-extraction processes - stylometric, temporal, identifier-based, exposure-based, "
        f"financial, and infrastructural - and fuses the resulting evidence into a single, weighted "
        f"attribution confidence score for each candidate pair of personas, subject to a minimum linkage "
        f"threshold of {threshold:.2f} ({_pct(threshold)}).", st["Body"]))
    story.append(Paragraph(
        f"The analysis identified <b>{len(edges)}</b> candidate link(s) meeting the threshold criterion, "
        f"which resolve into <b>{len(attrs)}</b> distinct suspected-identity cluster(s). Each finding is "
        f"supported by an itemized evidentiary breakdown (Section 6) and is logged in a cryptographically "
        f"chained audit trail (Section 7) to preserve chain-of-custody integrity in accordance with "
        f"Section 65B of the Information Technology Act, 2000.", st["Body"]))

    # ================= 2. LEGAL & REGULATORY BASIS =================
    story.append(Paragraph("2. Legal and Regulatory Basis", st["Sec"]))
    story.append(Paragraph(
        "This report and the underlying methodology are designed with reference to the following "
        "Indian statutory provisions governing the admissibility of electronic evidence:", st["Body"]))
    story.append(_bullets([
        "<b>Bharatiya Sakshya Adhiniyam, 2023, Section 63</b> - governs the admissibility of electronic "
        "records as evidence, subject to a certificate identifying the manner of production and the "
        "device involved.",
        "<b>Information Technology Act, 2000, Section 65B</b> - the predecessor provision on electronic "
        "evidence, requiring demonstration that the record was produced by a system operating properly "
        "and without unauthorized alteration.",
        "<b>ISO/IEC 27037:2012</b> - international guidelines for the identification, collection, "
        "acquisition, and preservation of digital evidence, informing the chain-of-custody design in "
        "Section 7 of this report.",
    ], st["BodyB"]))
    story.append(Paragraph(
        "Accordingly, every analytical action taken by the system - each correlation run and every "
        "export of this report - is recorded in an append-only, hash-chained audit log (Section 7), "
        "such that any retrospective alteration of a prior entry is cryptographically detectable.",
        st["Body"]))

    # ================= 3. METHODOLOGY =================
    story.append(Paragraph("3. Methodology", st["Sec"]))
    story.append(Paragraph(
        "SUTRADHAR operates on the forensic principle that sustained operational anonymity requires "
        "consistent suppression of every behavioural, linguistic, financial, and infrastructural trace an "
        "individual leaves behind - a standard that is difficult to meet in practice. The system therefore "
        "evaluates six independent signal categories per persona pair. Where multiple independent signals "
        "concur, the aggregate evidentiary weight substantially exceeds that of any single signal in "
        "isolation, consistent with the Bayesian principle of independent corroboration.", st["Body"]))
    for title, body in SIGNAL_THEORY:
        story.append(Paragraph(title, st["SubSec"]))
        story.append(Paragraph(body, st["Body"]))
    story.append(Paragraph("3.7 Score Fusion", st["SubSec"]))
    story.append(Paragraph(
        "Applicable signal scores are combined via a weighted linear blend. Signals constituting direct "
        "evidence (persona reuse, wallet clustering, infrastructure match) additionally impose a minimum "
        "confidence floor, reflecting their comparatively higher evidentiary weight relative to the "
        "probabilistic stylometric and temporal signals. The resulting composite score, together with its "
        "full per-signal decomposition, is reported for every identified link (Section 6) - the system "
        "does not produce an unexplained or non-auditable output at any stage.", st["Body"]))

    # ================= 4. CASE OVERVIEW =================
    story.append(PageBreak())
    story.append(Paragraph("4. Case Overview", st["Sec"]))
    story.append(Paragraph(
        f"The following {len(nodes)} persona(s) were submitted for analysis. Word count reflects the "
        f"volume of text available per persona; the OPSEC risk rating reflects the outcome of the "
        f"exposure-assessment process described in Section 3.4.", st["Body"]))
    prows = [["#", "Alias", "Site / Source", "Words", "OPSEC Risk", "Evasion"]]
    for i, n in enumerate(nodes):
        words = len((personas[i].get("text", "").split()))
        risk = n.get("exposure", {}).get("level", "-")
        evasion = n.get("evasion", {}).get("level", "-")
        prows.append([str(i + 1), n["alias"], n.get("site", "") or "-", str(words), risk, evasion])
    pt = Table(prows, colWidths=[8 * mm, 32 * mm, 38 * mm, 16 * mm, 24 * mm, 22 * mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), SLATE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ]))
    story.append(pt)

    # ================= 5. ATTRIBUTION FINDINGS =================
    story.append(Paragraph("5. Attribution Findings", st["Sec"]))
    if not attrs:
        story.append(Paragraph(
            "No persona pairs met the configured linkage threshold in this analysis run. This does not "
            "preclude common ownership; it indicates that available signal evidence was insufficient at "
            "the current threshold setting. Analysts may consider lowering the threshold or supplying "
            "additional persona text to improve signal resolution.", st["Body"]))
    else:
        story.append(Paragraph(
            f"The analysis resolved the submitted personas into {len(attrs)} suspected-identity cluster(s), "
            f"summarized below. Full evidentiary support for each underlying link is presented in Section 6.",
            st["Body"]))
        for idx, a in enumerate(attrs, 1):
            story.append(Paragraph(
                f"Finding {idx}: " + " = ".join(a["aliases"]) +
                f' &nbsp; <font color="#B45309">[{_pct(a["confidence"])} confidence]</font>', st["Find"]))
            story.append(Paragraph(
                f"The system assesses, with {_pct(a['confidence'])} confidence, that the {len(a['aliases'])} "
                f"aliases listed above are operated by a single individual or entity, on the basis of the "
                f"corroborating signals detailed in Section 6.", st["Small"]))
            story.append(Spacer(1, 5))

    # ================= 6. DETAILED EVIDENCE ANALYSIS =================
    story.append(PageBreak())
    story.append(Paragraph("6. Detailed Evidence Analysis", st["Sec"]))
    story.append(Paragraph(
        "This section presents the complete, itemized evidentiary basis for every link identified in "
        "Section 5, disaggregated by signal category as defined in Section 3. All figures represent "
        "similarity or match scores in the [0,1] range, expressed here as percentages.", st["Body"]))
    if not edges:
        story.append(Paragraph("No qualifying links were identified in this analysis run.", st["Body"]))
    for e in edges:
        sa = nodes[e["source"]]["alias"]
        ta = nodes[e["target"]]["alias"]
        block = [Paragraph(
            f'{sa} &harr; {ta} &nbsp; <font color="#0E7490">Composite score: {_pct(e["score"])}</font>',
            st["Find"])]
        ev = e["evidence"]
        rows = [["Signal Category", "Score / Detail"]]
        rows.append(["Character n-gram similarity", _pct(ev.get("char_ngrams", 0))])
        rows.append(["Function-word similarity", _pct(ev.get("function_words", 0))])
        rows.append(["Style-ratio similarity", _pct(ev.get("style_ratios", 0))])
        if "cognitive" in ev:
            rows.append(["Cognitive-fingerprint similarity", _pct(ev["cognitive"])])
        if "activity_pattern" in ev:
            rows.append(["Temporal activity overlap", _pct(ev["activity_pattern"])])
            pw = ev.get("peak_windows")
            if pw:
                rows.append(["Concordant active window", f"{pw[0]}  /  {pw[1]}"])
        if "persona_reuse" in ev:
            rows.append(["Persona-reuse match", _pct(ev["persona_reuse"])])
            si = ev.get("shared_identifiers")
            if si:
                rows.append(["Shared identifier(s)", ", ".join(si)])
        if "crypto_flow" in ev:
            rows.append(["Cryptocurrency wallet linkage", _pct(ev["crypto_flow"])])
            cd = ev.get("crypto_detail") or {}
            if cd:
                line = f"{cd.get('kind','')} {cd.get('detail','')}"
                if cd.get("cashout"):
                    line += f"  (cash-out: {cd['cashout']['vasp']})"
                rows.append(["Wallet trail", line])
        if "infra" in ev:
            rows.append(["Infrastructure fingerprint match", _pct(ev["infra"])])
            idt = ev.get("infra_detail") or {}
            if idt:
                line = f"{idt.get('kind','')} {idt.get('detail','')}"
                if idt.get("clearnet_ip"):
                    line += f"  (clearnet host: {idt['clearnet_ip']})"
                rows.append(["Server trail", line])
        t = Table(rows, colWidths=[80 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (0, -1), SLATE), ("TEXTCOLOR", (1, 1), (1, -1), TEAL),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        block.append(t)
        block.append(Spacer(1, 10))
        story.append(KeepTogether(block))

    # ================= 7. AUDIT TRAIL =================
    story.append(PageBreak())
    story.append(Paragraph("7. Audit Trail (Chain of Custody)", st["Sec"]))
    story.append(Paragraph(
        "In accordance with the chain-of-custody requirements referenced in Section 2, every analytical "
        "and reporting action performed by this system is recorded as an append-only log entry. Each "
        "entry is bound to its predecessor via a SHA-256 hash chain: the hash of every entry incorporates "
        "the hash of the entry immediately preceding it, such that retrospective modification of any "
        "single entry invalidates every subsequent hash and is therefore cryptographically detectable.",
        st["Body"]))
    ok, broke_at = audit_log.verify_chain()
    status_color = GREEN if ok else colors.HexColor("#DC2626")
    status_text = "CHAIN INTEGRITY VERIFIED" if ok else f"CHAIN INTEGRITY FAILURE AT ENTRY #{broke_at}"
    story.append(Table([[Paragraph(status_text, ParagraphStyle(
        "st", fontSize=9.5, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER))]],
        colWidths=[174 * mm],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), status_color),
                          ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])))
    story.append(Spacer(1, 6))
    log_entries = audit_log.get_log()
    if log_entries:
        arows = [["#", "Timestamp (UTC)", "Action", "Summary", "Hash (truncated)"]]
        for entry in log_entries:
            arows.append([str(entry["seq"]), entry["timestamp"].replace("T", " "),
                         entry["action"], entry["summary"][:38], entry["hash"][:16] + "..."])
        at = Table(arows, colWidths=[8 * mm, 34 * mm, 22 * mm, 68 * mm, 38 * mm])
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), SLATE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("FONTNAME", (4, 1), (4, -1), "Courier"),
        ]))
        story.append(at)
    else:
        story.append(Paragraph("No prior actions recorded in this session.", st["Body"]))

    # ================= 8. LIMITATIONS =================
    story.append(Paragraph("8. Limitations and Scope", st["Sec"]))
    story.append(_bullets([
        "This report constitutes an <b>investigative lead</b>, not conclusive proof of identity. All "
        "findings require corroboration by a qualified human analyst prior to operational action.",
        "Confidence scores are probabilistic outputs of statistical and pattern-matching processes and "
        "are subject to false-positive and false-negative error rates inherent to any such system.",
        "The cryptocurrency-flow and infrastructure-correlation modules operate, in the present "
        "prototype configuration, against representative reference datasets; production deployment is "
        "designed to integrate live chain-analysis and network-telemetry data sources.",
        "This system does not perform, and this report does not constitute authorization for, any "
        "active intrusion, interception, or unauthorized access to computer systems.",
    ], st["BodyB"]))

    # ================= 9. CERTIFICATION =================
    story.append(Paragraph("9. Certification", st["Sec"]))
    story.append(Paragraph(
        "This report was generated automatically by the SUTRADHAR attribution platform on the date and "
        "time indicated on the cover page, from the persona data and configuration parameters submitted "
        "by the operating analyst, and is reproduced here without manual alteration to its analytical "
        "content. The audit trail in Section 7 evidences the integrity of the generating process.",
        st["Body"]))
    story.append(Spacer(1, 24))
    story.append(Table([
        ["Prepared by (System)", "SUTRADHAR v1.0"],
        ["Reviewing Analyst", "_____________________________"],
        ["Badge / Employee ID", "_____________________________"],
        ["Signature", "_____________________________"],
        ["Date", "_____________________________"],
    ], colWidths=[55 * mm, 90 * mm], style=TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("TEXTCOLOR", (0, 0), (0, -1), SLATE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("TEXTCOLOR", (1, 0), (1, -1), MUTE),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ])))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Generated by SUTRADHAR - an authorized-investigator attribution platform - from stylometric, "
        "temporal, identifier, exposure, financial, and infrastructural signals, on consented or "
        "published research data. Distribution restricted to authorized investigative personnel.",
        st["Foot"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()


if __name__ == "__main__":
    from correlation import build_graph
    from sample_personas import PERSONAS
    audit_log.record("analyze", f"{len(PERSONAS)} personas, threshold 0.55")
    g = build_graph(PERSONAS)
    audit_log.record("export_pdf", f"case file for {len(g['attributions'])} attribution(s)")
    pdf = build_report_pdf(g, PERSONAS, 0.55)
    open("case_file_sample.pdf", "wb").write(pdf)
    print("wrote case_file_sample.pdf", len(pdf), "bytes")
