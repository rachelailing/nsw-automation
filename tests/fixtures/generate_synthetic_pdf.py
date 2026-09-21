from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT = Path(__file__).with_name("synthetic_knowledge_pack.pdf")


def build_pdf() -> None:
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="Synthetic Dispensing Guide",
        author="Defect Detective Test Suite",
    )
    story = [
        Paragraph("Synthetic Dispensing Guide", styles["Title"]),
        Spacer(1, 7 * mm),
        Paragraph("Material", styles["Heading2"]),
        Paragraph(
            "Synthetic Silver Epoxy is a conductive epoxy with a test viscosity "
            "range of 18,000 to 24,000 mPa.s. Mix for two minutes before use.",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Undersized Dot", styles["Heading2"]),
        Paragraph(
            "For a continuous undersized dot, compare pressure with the synthetic "
            "qualified recipe. Engineer approval is required before changing the "
            "setting. Do not exceed the synthetic process window.",
            styles["BodyText"],
        ),
    ]
    document.build(story)


if __name__ == "__main__":
    build_pdf()
