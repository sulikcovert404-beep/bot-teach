from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from app.services.worksheet import WorksheetQuestion, render_worksheet


def render_worksheet_pdf(
    title: str, instructions: str, questions: list[WorksheetQuestion]
) -> bytes:
    markdown = render_worksheet(title, instructions, questions)
    output = BytesIO()
    canvas = Canvas(output, pagesize=A4)
    _, height = A4
    canvas.setFont("Helvetica", 11)
    y = height - 48
    for line in markdown.splitlines():
        if y < 48:
            canvas.showPage()
            canvas.setFont("Helvetica", 11)
            y = height - 48
        canvas.drawString(42, y, line.encode("ascii", "replace").decode("ascii"))
        y -= 16
    canvas.save()
    return output.getvalue()
