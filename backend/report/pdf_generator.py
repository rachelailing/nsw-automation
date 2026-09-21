"""Generate a technician-facing PDF from persisted diagnostic session state."""

from datetime import datetime, timezone
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#18211D")
MUTED = colors.HexColor("#5F6E66")
ACCENT = colors.HexColor("#168467")
LINE = colors.HexColor("#D8E0DB")
PALE = colors.HexColor("#F3F7F5")
WARNING = colors.HexColor("#956516")


def _text(value) -> str:
    """Escape dynamic text and keep it compatible with built-in PDF fonts."""
    cleaned = str(value if value is not None else "Not provided")
    cleaned = cleaned.encode("latin-1", "replace").decode("latin-1")
    return escape(cleaned).replace("\n", "<br/>")


def _confidence(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not provided"
    if number <= 1:
        number *= 100
    return f"{round(number)}%"


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=INK,
            spaceAfter=5 * mm,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["BodyText"],
            fontSize=9,
            leading=13,
            textColor=MUTED,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=INK,
            spaceBefore=6 * mm,
            spaceAfter=2.5 * mm,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontSize=9,
            leading=13,
            textColor=INK,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "label": ParagraphStyle(
            "ReportLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=MUTED,
        ),
        "right": ParagraphStyle(
            "ReportRight",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_RIGHT,
        ),
    }


def _draw_page(canvas, document) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(18 * mm, 10 * mm, "Defect Detective - Troubleshooting Report")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _metadata_table(session_data: dict, styles: dict) -> Table:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = [
        [Paragraph("Session", styles["label"]), Paragraph(_text(session_data.get("session_id")), styles["small"])],
        [Paragraph("Generated", styles["label"]), Paragraph(generated, styles["small"])],
        [Paragraph("Project", styles["label"]), Paragraph(_text(session_data.get("project_id")), styles["small"])],
        [Paragraph("Knowledge Pack", styles["label"]), Paragraph(_text(session_data.get("knowledge_pack_id")), styles["small"])],
    ]
    table = Table(rows, colWidths=[34 * mm, 128 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


async def generate_pdf(session_data: dict) -> bytes:
    """Generate a complete troubleshooting report as PDF bytes."""
    state = session_data.get("state") or session_data
    report = state.get("report") or {}
    defect = state.get("defect_result") or {}
    causes = state.get("causes") or []
    qa_pairs = state.get("qa_pairs") or []
    threshold_checks = (state.get("reference_threshold_evaluation") or {}).get("checks") or []
    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=22 * mm,
        title="Troubleshooting Report",
        author="AI Dispensing Defect Detective",
    )

    story = [
        Paragraph("Troubleshooting Report", styles["title"]),
        Paragraph(
            f"Dispensing defect analysis for <b>{_text(state.get('defect_type') or defect.get('defect_type'))}</b>",
            styles["subtitle"],
        ),
        Spacer(1, 5 * mm),
        _metadata_table({**session_data, **state}, styles),
        Paragraph("Diagnosis Summary", styles["section"]),
        Paragraph(_text(report.get("summary") or defect.get("reasoning")), styles["body"]),
    ]

    if defect:
        story.append(
            Paragraph(
                f"<b>Classification confidence:</b> {_confidence(defect.get('confidence'))} &nbsp;&nbsp; "
                f"<b>Evidence source:</b> {_text(defect.get('source'))}",
                styles["body"],
            )
        )

    if threshold_checks:
        story.append(Paragraph("Reference Checks", styles["section"]))
        rows = [["Parameter", "Measured", "Approved range", "Result"]]
        for check in threshold_checks:
            unit = check.get("unit") or ""
            minimum = check.get("min")
            maximum = check.get("max")
            rows.append(
                [
                    _text(check.get("parameter")),
                    f"{_text(check.get('measured'))} {_text(unit)}",
                    f"{_text(minimum)} to {_text(maximum)} {_text(unit)}",
                    _text(check.get("status")),
                ]
            )
        table = Table(rows, colWidths=[38 * mm, 36 * mm, 55 * mm, 33 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    story.append(Paragraph("Probable Root Causes", styles["section"]))
    if causes:
        for cause in causes:
            block = [
                Paragraph(
                    f"<b>{_text(cause.get('rank'))}. {_text(cause.get('cause'))}</b>",
                    styles["body"],
                ),
                Paragraph(
                    f"{_text(cause.get('category'))} | Confidence {_confidence(cause.get('confidence'))}",
                    styles["small"],
                ),
                Paragraph(_text(cause.get("reasoning")), styles["body"]),
                Spacer(1, 1.5 * mm),
            ]
            story.append(KeepTogether(block))
    else:
        story.append(Paragraph("No ranked causes were recorded.", styles["body"]))

    story.append(Paragraph("Recommended Action Plan", styles["section"]))
    actions = report.get("action_plan") or []
    if actions:
        for index, action in enumerate(actions, 1):
            story.append(
                KeepTogether(
                    [
                        Paragraph(
                            f"<b>{index}. {_text(action.get('action'))}</b> "
                            f"[{_text(action.get('priority')).upper()}]",
                            styles["body"],
                        ),
                        Paragraph(f"Why: {_text(action.get('rationale'))}", styles["small"]),
                        Spacer(1, 1.5 * mm),
                    ]
                )
            )
    else:
        story.append(Paragraph("No action plan was recorded.", styles["body"]))

    recommendations = report.get("recommendations") or []
    if recommendations:
        story.append(Paragraph("Preventive Recommendations", styles["section"]))
        for recommendation in recommendations:
            story.append(Paragraph(f"- {_text(recommendation)}", styles["body"]))

    if qa_pairs:
        story.append(Paragraph("Diagnostic Evidence", styles["section"]))
        for qa in qa_pairs:
            story.append(
                KeepTogether(
                    [
                        Paragraph(f"<b>Q:</b> {_text(qa.get('question'))}", styles["body"]),
                        Paragraph(f"<b>A:</b> {_text(qa.get('answer'))}", styles["body"]),
                        Spacer(1, 1 * mm),
                    ]
                )
            )

    if state.get("feedback_action"):
        story.append(Paragraph("Confirmed Outcome", styles["section"]))
        outcome = "Resolved" if state.get("feedback_fixed") else "Not resolved"
        story.extend(
            [
                Paragraph(f"<b>Outcome:</b> {_text(outcome)}", styles["body"]),
                Paragraph(f"<b>Action attempted:</b> {_text(state.get('feedback_action'))}", styles["body"]),
                Paragraph(f"<b>Confirmed cause:</b> {_text(state.get('feedback_cause'))}", styles["body"]),
            ]
        )

    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph(
                "This report supports technician review. Apply process changes only within approved operating and safety limits.",
                ParagraphStyle(
                    "ReportDisclaimer",
                    parent=styles["small"],
                    textColor=WARNING,
                ),
            ),
        ]
    )

    document.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return buffer.getvalue()
