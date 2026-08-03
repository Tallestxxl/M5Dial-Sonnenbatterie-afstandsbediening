from __future__ import annotations

import math
import filecmp
import os
from pathlib import Path
import tempfile

import reportlab
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
USER_OUT = ROOT / "docs/gebruikershandleiding/M5Dial-Sonnenbatterie-gebruikershandleiding-versie-1.2.pdf"
INSTALLER_OUT = ROOT / "docs/gebruikershandleiding/M5Dial-Sonnenbatterie-installateurshandleiding-versie-1.1.pdf"
FRONT_PHOTO = ROOT / "docs/images/m5dial-remote-status-photo.jpg"
CASE_PHOTO = ROOT / "hardware/case/m5stack-dial-case-preview.webp"
FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"

W, H = A4
M = 44

DARK = HexColor("#0B1216")
INK = HexColor("#17262E")
MUTED = HexColor("#607078")
LINE = HexColor("#D7E0DE")
LIGHT = HexColor("#F4F7F6")
ORANGE = HexColor("#F47B20")
GREEN = HexColor("#4BCF8B")
BLUE = HexColor("#53A9E8")
AMBER = HexColor("#F0AB43")
RED = HexColor("#D9544D")
PANEL = HexColor("#28343A")
PALE_GREEN = HexColor("#EAF8F1")
PALE_BLUE = HexColor("#ECF6FC")
PALE_ORANGE = HexColor("#FFF1E6")
PALE_RED = HexColor("#FDEDEC")


def register_fonts() -> None:
    # ReportLab ships these fonts, so local and CI builds use identical files.
    pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("DV-Bold", str(FONT_DIR / "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("DV-Italic", str(FONT_DIR / "VeraIt.ttf")))
    pdfmetrics.registerFont(pdfmetrics.Font("DV-Mono", "Courier", "WinAnsiEncoding"))
    pdfmetrics.registerFont(pdfmetrics.Font("DV-Mono-Bold", "Courier-Bold", "WinAnsiEncoding"))


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for raw in text.split("\n"):
        words = raw.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            test = current + " " + word
            if pdfmetrics.stringWidth(test, font, size) <= width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    size: float = 9.4,
    leading: float = 13.2,
    font: str = "DV",
    color=INK,
) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    for line in wrap(text, font, size, width):
        c.drawString(x, y, line)
        y -= leading
    return y


def label(c: canvas.Canvas, text: str, x: float, y: float, *, color=ORANGE) -> None:
    c.setFont("DV-Bold", 7.3)
    c.setFillColor(color)
    c.drawString(x, y, text.upper())


def section_title(
    c: canvas.Canvas,
    section: str,
    title: str,
    page: int,
    *,
    document_name: str = "Gebruikershandleiding",
) -> float:
    c.setFillColor(LIGHT)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(DARK)
    c.rect(0, H - 88, W, 88, fill=1, stroke=0)
    c.setFillColor(ORANGE)
    c.rect(0, H - 88, 9, 88, fill=1, stroke=0)
    c.setFont("DV-Bold", 7.5)
    c.setFillColor(GREEN)
    c.drawString(M, H - 30, section.upper())
    c.setFont("DV-Bold", 22)
    c.setFillColor(white)
    c.drawString(M, H - 60, title)
    footer(c, page, document_name)
    return H - 116


def footer(c: canvas.Canvas, page: int, document_name: str = "Gebruikershandleiding") -> None:
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(M, 31, W - M, 31)
    c.setFillColor(MUTED)
    c.setFont("DV", 6.7)
    c.drawString(M, 18, f"M5Dial Sonnenbatterie-afstandsbediening | {document_name}")
    c.drawRightString(W - M, 18, f"{page}")


def callout(
    c: canvas.Canvas,
    title: str,
    body: str,
    x: float,
    y: float,
    width: float,
    *,
    fill=PALE_ORANGE,
    accent=ORANGE,
    body_size: float = 8.9,
) -> float:
    title_lines = wrap(title, "DV-Bold", 9.2, width - 32)
    body_lines = wrap(body, "DV", body_size, width - 32)
    height = 23 + len(title_lines) * 12 + len(body_lines) * 12.2 + 10
    c.setFillColor(fill)
    c.setStrokeColor(accent)
    c.setLineWidth(0.8)
    c.roundRect(x, y - height, width, height, 6, fill=1, stroke=1)
    c.setFillColor(accent)
    c.rect(x, y - height, 6, height, fill=1, stroke=0)
    ty = y - 19
    c.setFont("DV-Bold", 9.2)
    c.setFillColor(INK)
    for line in title_lines:
        c.drawString(x + 18, ty, line)
        ty -= 12
    ty -= 2
    c.setFont("DV", body_size)
    c.setFillColor(INK)
    for line in body_lines:
        c.drawString(x + 18, ty, line)
        ty -= 12.2
    return y - height - 10


def bullets(
    c: canvas.Canvas,
    items: list[str],
    x: float,
    y: float,
    width: float,
    *,
    size: float = 9.1,
    leading: float = 12.4,
    color=INK,
    dot=GREEN,
    gap: float = 5,
) -> float:
    for item in items:
        lines = wrap(item, "DV", size, width - 18)
        c.setFillColor(dot)
        c.circle(x + 3, y + 2.8, 2.4, fill=1, stroke=0)
        c.setFont("DV", size)
        c.setFillColor(color)
        for line in lines:
            c.drawString(x + 14, y, line)
            y -= leading
        y -= gap
    return y


def numbered_steps(
    c: canvas.Canvas,
    items: list[tuple[str, str]],
    x: float,
    y: float,
    width: float,
    *,
    accent=ORANGE,
    size: float = 8.9,
    gap: float = 8,
) -> float:
    for index, (title, body) in enumerate(items, 1):
        title_lines = wrap(title, "DV-Bold", size, width - 40)
        body_lines = wrap(body, "DV", size, width - 40)
        c.setFillColor(accent)
        c.circle(x + 13, y - 4, 11, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("DV-Bold", 8.2)
        c.drawCentredString(x + 13, y - 7, str(index))
        ty = y
        c.setFillColor(INK)
        c.setFont("DV-Bold", size)
        for line in title_lines:
            c.drawString(x + 34, ty, line)
            ty -= 11.8
        c.setFont("DV", size)
        for line in body_lines:
            c.drawString(x + 34, ty, line)
            ty -= 11.8
        y = ty - gap
    return y


def draw_table(
    c: canvas.Canvas,
    headers: list[str],
    rows: list[list[str]],
    x: float,
    y: float,
    widths: list[float],
    *,
    font_size: float = 7.8,
    row_pad: float = 6,
    header_fill=DARK,
) -> float:
    assert len(headers) == len(widths)
    total_w = sum(widths)
    header_h = 24
    c.setFillColor(header_fill)
    c.roundRect(x, y - header_h, total_w, header_h, 4, fill=1, stroke=0)
    cx = x
    c.setFont("DV-Bold", 7.4)
    c.setFillColor(white)
    for head, width in zip(headers, widths):
        c.drawString(cx + 6, y - 16, head)
        cx += width
    y -= header_h
    for row_index, row in enumerate(rows):
        wrapped = [wrap(cell, "DV", font_size, width - 12) for cell, width in zip(row, widths)]
        lines = max(len(cell_lines) for cell_lines in wrapped)
        row_h = max(25, lines * (font_size + 3.2) + row_pad * 2)
        c.setFillColor(white if row_index % 2 == 0 else HexColor("#EEF3F2"))
        c.setStrokeColor(LINE)
        c.rect(x, y - row_h, total_w, row_h, fill=1, stroke=1)
        cx = x
        for cell_lines, width in zip(wrapped, widths):
            c.setFillColor(INK)
            c.setFont("DV", font_size)
            ty = y - row_pad - font_size
            for line in cell_lines:
                c.drawString(cx + 6, ty, line)
                ty -= font_size + 3.2
            cx += width
            c.setStrokeColor(LINE)
            c.line(cx, y, cx, y - row_h)
        y -= row_h
    return y - 8


def draw_code(c: canvas.Canvas, lines: list[str], x: float, y: float, width: float, *, size=7.2) -> float:
    leading = size + 4
    height = len(lines) * leading + 18
    c.setFillColor(DARK)
    c.roundRect(x, y - height, width, height, 6, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont("DV-Mono", size)
    ty = y - 15
    for line in lines:
        c.drawString(x + 12, ty, line)
        ty -= leading
    return y - height - 8


def cover_image(c: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float) -> None:
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    scale = max(width / iw, height / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (width - dw) / 2, y + (height - dh) / 2
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, width, height)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(image, dx, dy, dw, dh, mask="auto")
    c.restoreState()


def contain_image(c: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float) -> None:
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    scale = min(width / iw, height / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (width - dw) / 2, y + (height - dh) / 2
    c.setFillColor(white)
    c.setStrokeColor(LINE)
    c.roundRect(x, y, width, height, 6, fill=1, stroke=1)
    c.drawImage(image, dx, dy, dw, dh, mask="auto")


def arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, color=GREEN, width=2) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 6
    for offset in (2.55, -2.55):
        c.line(x2, y2, x2 + size * math.cos(angle + offset), y2 + size * math.sin(angle + offset))


def marker(c: canvas.Canvas, number: int, x: float, y: float, color=ORANGE) -> None:
    c.setFillColor(color)
    c.setStrokeColor(white)
    c.setLineWidth(1.4)
    c.circle(x, y, 10, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("DV-Bold", 7.8)
    c.drawCentredString(x, y - 2.8, str(number))


def draw_screen(c: canvas.Canvas, x: float, y: float, diameter: float) -> None:
    r = diameter / 2
    cx, cy = x + r, y + r
    c.setFillColor(ORANGE)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(HexColor("#11161B"))
    c.circle(cx, cy, r - 12, fill=1, stroke=0)
    # The firmware positions the SOC arc above the physical screen center and
    # leaves the lower part free for the four power values and action bar.
    tick_cy = cy + r * 0.22
    tick_r = r * 0.62
    for i in range(60):
        angle = math.radians(-220 + 260 * i / 59)
        inner = tick_r - (9 if i % 5 == 0 else 5)
        active = i < 31
        c.setStrokeColor(GREEN if active else PANEL)
        c.setLineWidth(1.2 if i % 5 == 0 else 0.7)
        c.line(
            cx + math.cos(angle) * inner,
            tick_cy - math.sin(angle) * inner,
            cx + math.cos(angle) * tick_r,
            tick_cy - math.sin(angle) * tick_r,
        )
    c.setFillColor(GREEN)
    c.setFont("DV-Bold", 6.5)
    c.drawCentredString(cx, cy + 72, "Mode 2")
    c.setFillColor(white)
    c.setFont("DV-Mono-Bold", 25)
    c.drawCentredString(cx - 5, cy + 27, "51")
    c.setFont("DV-Bold", 10)
    c.drawString(cx + 24, cy + 30, "%")
    c.setFont("DV", 6)
    c.setFillColor(HexColor("#A8B4B4"))
    c.drawCentredString(cx, cy + 5, "SOC")
    positions = [
        (cx - 38, cy - 34, "PV", "+2350W", GREEN),
        (cx + 38, cy - 34, "USE", "+620W", white),
        (cx - 38, cy - 68, "GRID", "+730W", AMBER),
        (cx + 38, cy - 68, "BAT", "+1000W", BLUE),
    ]
    for px, py, name, value, color in positions:
        c.setFont("DV", 5.8)
        c.setFillColor(HexColor("#A8B4B4"))
        c.drawCentredString(px, py + 8, name)
        c.setFont("DV-Mono-Bold", 7.2)
        c.setFillColor(color)
        c.drawCentredString(px, py - 1, value)
    c.setFillColor(GREEN)
    c.roundRect(cx - 58, cy - 107, 116, 15, 5, fill=1, stroke=0)
    c.setFillColor(DARK)
    c.setFont("DV-Mono-Bold", 7.6)
    c.drawCentredString(cx, cy - 103, "< STATUS >")


def draw_menu_carousel(c: canvas.Canvas, x: float, y: float, width: float) -> None:
    items = ["STATUS", "AUTO", "CHARGE", "DISCH", "DIM"]
    box_w = (width - 4 * 9) / 5
    for i, item in enumerate(items):
        bx = x + i * (box_w + 9)
        fill = GREEN if item == "STATUS" else white
        c.setFillColor(fill)
        c.setStrokeColor(GREEN)
        c.roundRect(bx, y, box_w, 32, 5, fill=1, stroke=1)
        c.setFillColor(DARK)
        c.setFont("DV-Bold", 7.2 if item != "CHARGE" else 6.7)
        c.drawCentredString(bx + box_w / 2, y + 12, item)
        if i < len(items) - 1:
            arrow(c, bx + box_w + 2, y + 16, bx + box_w + 7, y + 16, MUTED, 1)
    c.setFont("DV", 7)
    c.setFillColor(MUTED)
    c.drawCentredString(x + width / 2, y - 14, "De lijst loopt rond: na DIM volgt weer STATUS.")


def draw_flow(c: canvas.Canvas, steps: list[str], x: float, y: float, width: float, *, accent=GREEN) -> float:
    gap = 13
    box_w = (width - gap * (len(steps) - 1)) / len(steps)
    h = 48
    for i, step in enumerate(steps):
        bx = x + i * (box_w + gap)
        c.setFillColor(white)
        c.setStrokeColor(accent)
        c.setLineWidth(1)
        c.roundRect(bx, y - h, box_w, h, 6, fill=1, stroke=1)
        c.setFillColor(accent)
        c.circle(bx + 13, y - 13, 8, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("DV-Bold", 6.6)
        c.drawCentredString(bx + 13, y - 15.5, str(i + 1))
        lines = wrap(step, "DV-Bold", 7.1, box_w - 14)
        ty = y - 28
        c.setFillColor(INK)
        c.setFont("DV-Bold", 7.1)
        for line in lines[:2]:
            c.drawCentredString(bx + box_w / 2, ty, line)
            ty -= 9
        if i < len(steps) - 1:
            arrow(c, bx + box_w + 2, y - h / 2, bx + box_w + gap - 2, y - h / 2, accent, 1.4)
    return y - h - 12


def draw_power_diagram(c: canvas.Canvas, x: float, y: float, width: float) -> float:
    cols = [
        ("USB-C", "5 V DC", "Aan zijkant", BLUE),
        ("Witte accuplug", "1S / 3,7 V", "1,25 mm - 2 polig", GREEN),
        ("Groene klem", "6-36 V DC", "+ en - volgen", ORANGE),
    ]
    gap = 14
    col_w = (width - gap * 2) / 3
    for i, (name, voltage, note, color) in enumerate(cols):
        bx = x + i * (col_w + gap)
        c.setFillColor(white)
        c.setStrokeColor(color)
        c.setLineWidth(1.2)
        c.roundRect(bx, y - 122, col_w, 122, 8, fill=1, stroke=1)
        c.setFillColor(color)
        if i == 0:
            c.roundRect(bx + col_w / 2 - 20, y - 37, 40, 16, 5, fill=0, stroke=1)
            c.line(bx + col_w / 2 - 11, y - 29, bx + col_w / 2 + 11, y - 29)
        elif i == 1:
            c.roundRect(bx + col_w / 2 - 22, y - 44, 44, 25, 4, fill=0, stroke=1)
            c.line(bx + col_w / 2, y - 44, bx + col_w / 2, y - 19)
            c.circle(bx + col_w / 2 - 11, y - 31, 2, fill=1, stroke=0)
            c.circle(bx + col_w / 2 + 11, y - 31, 2, fill=1, stroke=0)
        else:
            c.roundRect(bx + col_w / 2 - 28, y - 47, 56, 30, 3, fill=0, stroke=1)
            c.setFont("DV-Bold", 10)
            c.drawCentredString(bx + col_w / 2 - 14, y - 38, "+")
            c.drawCentredString(bx + col_w / 2 + 14, y - 38, "-")
        c.setFillColor(INK)
        c.setFont("DV-Bold", 9.2)
        c.drawCentredString(bx + col_w / 2, y - 65, name)
        c.setFillColor(color)
        c.setFont("DV-Bold", 10.5)
        c.drawCentredString(bx + col_w / 2, y - 83, voltage)
        c.setFillColor(MUTED)
        c.setFont("DV", 7.2)
        c.drawCentredString(bx + col_w / 2, y - 102, note)
    return y - 136


def draw_network(c: canvas.Canvas, x: float, y: float, width: float) -> float:
    items = [
        ("M5Dial", "2,4 GHz wifi", BLUE),
        ("Router", "hetzelfde LAN", GREEN),
        ("Sonnenbatterie", "lokale API", ORANGE),
    ]
    gap = 42
    box_w = (width - gap * 2) / 3
    for i, (title, sub, color) in enumerate(items):
        bx = x + i * (box_w + gap)
        c.setFillColor(white)
        c.setStrokeColor(color)
        c.setLineWidth(1.5)
        c.roundRect(bx, y - 70, box_w, 70, 8, fill=1, stroke=1)
        c.setFillColor(color)
        c.circle(bx + box_w / 2, y - 21, 7, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DV-Bold", 9)
        c.drawCentredString(bx + box_w / 2, y - 43, title)
        c.setFillColor(MUTED)
        c.setFont("DV", 7)
        c.drawCentredString(bx + box_w / 2, y - 57, sub)
        if i < len(items) - 1:
            arrow(c, bx + box_w + 6, y - 35, bx + box_w + gap - 6, y - 35, GREEN, 2)
    c.setFillColor(PALE_RED)
    c.setStrokeColor(RED)
    c.roundRect(x + width * 0.28, y - 128, width * 0.44, 35, 6, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DV-Bold", 8)
    c.drawCentredString(x + width / 2, y - 108, "Geen willekeurig wifi / geen Tailscale-client")
    return y - 142


def draw_qr(c: canvas.Canvas, url: str, x: float, y: float, size: float) -> None:
    qr = QrCodeWidget(url)
    bounds = qr.getBounds()
    bw = bounds[2] - bounds[0]
    bh = bounds[3] - bounds[1]
    drawing = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0])
    drawing.add(qr)
    renderPDF.draw(drawing, c, x, y)


def cover(c: canvas.Canvas) -> None:
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    cover_image(c, FRONT_PHOTO, 0, 300, W, H - 300)
    c.saveState()
    c.setFillAlpha(0.72)
    c.setFillColor(DARK)
    c.rect(0, 300, W, 86, fill=1, stroke=0)
    c.restoreState()
    c.setFillColor(ORANGE)
    c.rect(0, 0, 10, 300, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont("DV-Bold", 8)
    c.drawString(48, 267, "GEBRUIKERSHANDLEIDING")
    c.setFillColor(white)
    c.setFont("DV-Bold", 26)
    c.drawString(48, 225, "M5Dial Sonnenbatterie-")
    c.drawString(48, 190, "afstandsbediening")
    c.setFont("DV", 11)
    c.setFillColor(HexColor("#C9D3D2"))
    c.drawString(48, 154, "Status bekijken, handmatig laden of ontladen en veilig terug naar AUTO")
    c.setFillColor(PANEL)
    c.roundRect(48, 96, 230, 34, 7, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("DV-Bold", 8.5)
    c.drawString(62, 109, "Versie 1.2  |  3 augustus 2026")
    c.setFillColor(HexColor("#8FA0A4"))
    c.setFont("DV", 7.2)
    c.drawString(48, 58, "Voor firmwarecommit 50f31c3 en de huidige apparaatconfiguratie")
    c.drawString(48, 43, "DIY-project - geen officieel product van sonnen of M5Stack")
    c.showPage()


def page_2(c: canvas.Canvas) -> None:
    y = section_title(c, "Start", "Over deze handleiding", 2)
    y = paragraph(
        c,
        "Deze handleiding beschrijft het dagelijkse gebruik van het apparaat zoals het nu is opgebouwd en "
        "geprogrammeerd. Dagelijks gebruik kan volledig zonder computer. Configuratie, firmware-updates, "
        "technisch onderhoud en herstel staan in de afzonderlijke installateurshandleiding.",
        M,
        y,
        W - 2 * M,
        size=10,
        leading=14.2,
    )
    y -= 10
    y = callout(
        c,
        "Belangrijkste regel",
        "Na handmatig laden of ontladen zet je de batterij weer op AUTO. AUTO herstelt de normale "
        "zelfverbruiksregeling van de Sonnenbatterie en zet haar terug in Mode 2. Boven in het scherm moet "
        "daarna 'Mode 2' zichtbaar zijn.",
        M,
        y,
        W - 2 * M,
        fill=PALE_GREEN,
        accent=GREEN,
        body_size=9.4,
    )
    label(c, "Inhoud", M, y - 5, color=BLUE)
    toc = [
        ("Lees dit eerst", "3"),
        ("Apparaat in één oogopslag", "4"),
        ("Voeding en aansluitingen", "5"),
        ("Eerste ingebruikname", "6"),
        ("Het statusscherm lezen", "7"),
        ("Bediening en menu", "8"),
        ("STATUS en AUTO", "9"),
        ("Handmatig laden", "10"),
        ("Handmatig ontladen", "11"),
        ("Wifi, bereik en automatisch verversen", "12"),
        ("Meldingen en foutcodes", "13"),
        ("Problemen oplossen", "14"),
        ("Voeding van de M5Dial", "15"),
        ("Snelle bedieningskaart en bronnen", "16"),
    ]
    ty = y - 28
    for i, (name, number) in enumerate(toc):
        col = 0 if i < 9 else 1
        row = i if i < 9 else i - 9
        x = M + col * 255
        yy = ty - row * 31
        c.setFillColor(white)
        c.setStrokeColor(LINE)
        c.roundRect(x, yy - 19, 238, 24, 4, fill=1, stroke=1)
        c.setFont("DV", 7.8)
        c.setFillColor(INK)
        c.drawString(x + 9, yy - 10, name)
        c.setFont("DV-Bold", 7.8)
        c.setFillColor(ORANGE)
        c.drawRightString(x + 228, yy - 10, number)
    c.showPage()


def page_3(c: canvas.Canvas) -> None:
    y = section_title(c, "Veiligheid", "Lees dit eerst", 3)
    y = callout(
        c,
        "Dit apparaat geeft echte opdrachten",
        "CHARGE, DISCH en AUTO sturen schrijfcommando's naar de Sonnenbatterie. Een geaccepteerd "
        "commando kan het energiegedrag direct veranderen. Controleer daarom altijd de gekozen actie en het wattage.",
        M,
        y,
        W - 2 * M,
        fill=PALE_RED,
        accent=RED,
        body_size=9.4,
    )
    label(c, "Veilig gebruiken", M, y - 2)
    y = bullets(
        c,
        [
            "Begin een nieuwe test met 100 W of 500 W. Verhoog pas wanneer de richting en reactie kloppen.",
            "Wacht na een commando enkele seconden. Stuur niet herhaaldelijk hetzelfde commando terwijl WORKING zichtbaar is.",
            "Zet de batterij na handmatig laden of ontladen terug op AUTO, tenzij je bewust in handmatige modus wilt blijven.",
            "Gebruik bij onverwacht gedrag ook het officiële Sonnen-dashboard of de installatiebediening. Deze afstandsbediening is geen noodstop.",
            "Open of wijzig nooit de Sonnenbatterie zelf. Werkzaamheden aan de batterij-installatie horen bij een erkende installateur.",
            "Gebruik alleen passende laagspanningsvoeding. Sluit nooit 7,4 V aan op de witte 3,7 V accuconnector.",
        ],
        M,
        y - 22,
        W - 2 * M,
        size=9.1,
        leading=12.6,
    )
    y -= 3
    label(c, "Wat het apparaat wel en niet doet", M, y, color=BLUE)
    y -= 16
    left_x = M
    right_x = W / 2 + 8
    box_w = W / 2 - M - 18
    c.setFillColor(PALE_GREEN)
    c.setStrokeColor(GREEN)
    c.roundRect(left_x, y - 144, box_w, 144, 7, fill=1, stroke=1)
    c.setFillColor(PALE_RED)
    c.setStrokeColor(RED)
    c.roundRect(right_x, y - 144, box_w, 144, 7, fill=1, stroke=1)
    c.setFont("DV-Bold", 9.5)
    c.setFillColor(GREEN)
    c.drawString(left_x + 14, y - 21, "WEL")
    c.setFillColor(RED)
    c.drawString(right_x + 14, y - 21, "NIET")
    bullets(c, ["Actuele waarden tonen", "AUTO activeren", "Laden en ontladen tot 3,6 kW", "Automatisch status verversen"], left_x + 12, y - 42, box_w - 24, size=8.1, leading=10.5, gap=3)
    bullets(c, ["Een noodstop vervangen", "Garanderen dat 3,6 kW haalbaar is", "Buiten het lokale wifi werken", "Sonnen-beveiligingen omzeilen"], right_x + 12, y - 42, box_w - 24, size=8.1, leading=10.5, gap=3, dot=RED)
    c.showPage()


def page_4(c: canvas.Canvas) -> None:
    y = section_title(c, "Hardware", "Apparaat in één oogopslag", 4)
    img_x, img_y, img_w, img_h = M, 165, 300, 530
    contain_image(c, FRONT_PHOTO, img_x, img_y, img_w, img_h)
    # Markers are positioned on the visible device in the portrait project photo.
    marker(c, 1, img_x + 224, img_y + 292)
    marker(c, 2, img_x + 167, img_y + 285, BLUE)
    marker(c, 3, img_x + 52, img_y + 310, GREEN)
    marker(c, 4, img_x + 223, img_y + 365, AMBER)
    x = 370
    label(c, "Onderdelen", x, y, color=BLUE)
    items = [
        ("1", "Draairing", "Draai links of rechts om door het menu te lopen of een wattage te kiezen.", ORANGE),
        ("2", "Drukknop onder scherm", "Druk het ronde scherm fysiek in. Aanraken of vegen wordt door deze firmware niet gebruikt.", BLUE),
        ("3", "USB-C", "Voeding, programmeren en seriële verbinding. Gebruik bij uploaden een datakabel.", GREEN),
        ("4", "3D-geprinte behuizing", "Beschermt de Dial en biedt ruimte voor voeding of een accu. De uitvoering kan afwijken.", AMBER),
    ]
    ty = y - 25
    for number, title, body, color in items:
        c.setFillColor(color)
        c.circle(x + 10, ty - 3, 9, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("DV-Bold", 7.5)
        c.drawCentredString(x + 10, ty - 5.5, number)
        c.setFillColor(INK)
        c.setFont("DV-Bold", 9.2)
        c.drawString(x + 27, ty, title)
        ty = paragraph(c, body, x + 27, ty - 15, 174, size=8.1, leading=11.3, color=MUTED)
        ty -= 15
    callout(
        c,
        "Let op bij wakker maken",
        "Het scherm dimt na twee minuten. Draai één klik om wakker te maken en controleer daarna de menuoptie. "
        "Een druk kan namelijk ook de geselecteerde actie uitvoeren.",
        x,
        ty + 2,
        181,
        fill=PALE_ORANGE,
        accent=ORANGE,
        body_size=8.0,
    )
    c.setFillColor(MUTED)
    c.setFont("DV-Italic", 6.8)
    c.drawString(M, 148, "Eigen projectfoto. De getoonde schermwaarden zijn een momentopname.")
    c.showPage()


def page_5(c: canvas.Canvas) -> None:
    y = section_title(c, "Hardware", "Voeding en aansluitingen", 5)
    y = paragraph(c, "De M5Dial kan op drie manieren worden gevoed. Kies voor de eerste ingebruikname USB-C; dat is het eenvoudigst en geeft tegelijk toegang tot firmware-updates.", M, y, W - 2 * M, size=9.6, leading=13.5)
    y -= 12
    y = draw_power_diagram(c, M, y, W - 2 * M)
    rows = [
        ["USB-C", "5 V DC", "Aanbevolen voor vaste voeding en uploaden. Gebruik een degelijke 5 V adapter en kabel."],
        ["Witte accuplug", "1S lithium, 3,7 V / 500 mAh", "De ingebouwde M5Dial-accu. Alleen 1,25 mm 2-polig met juiste polariteit."],
        ["Groene klem", "6-36 V DC", "Volg + en - exact. Een 2S/7,4 V pakket met BMS kan hier voeden, maar wordt hier niet als 2S-pakket geladen."],
    ]
    y = draw_table(c, ["Aansluiting", "Spanning", "Gebruik"], rows, M, y, [100, 125, W - 2 * M - 225], font_size=7.5)
    y -= 4
    photo_w, photo_h = 152, 203
    contain_image(c, CASE_PHOTO, M, y - photo_h, photo_w, photo_h)
    c.setFillColor(MUTED)
    c.setFont("DV-Italic", 6.4)
    c.drawString(M, y - photo_h - 12, "Open voorbeeldbehuizing met extra bedrading.")
    c.drawString(M, y - photo_h - 22, "Gebruik deze foto niet als elektrisch schema.")
    bx = M + photo_w + 18
    callout(
        c,
        "Nooit verwisselen",
        "Een 7,4 V 2S-accu hoort uitsluitend op de groene 6-36 V ingang. Op de witte accuconnector hoort alleen "
        "een 3,7 V 1S-accu. Een fout voltage of omgekeerde polariteit kan de M5Dial, accu of bedrading beschadigen.",
        bx,
        y,
        W - M - bx,
        fill=PALE_RED,
        accent=RED,
        body_size=8.3,
    )
    callout(
        c,
        "Praktisch advies",
        "Gebruik als beginner één voedingsbron tegelijk. Schakel de bron uit voordat je aan de groene klem werkt. "
        "Gebruik bij een losse lithiumaccu een BMS, passende zekering, trekontlasting en de juiste lader.",
        bx,
        y - 116,
        W - M - bx,
        fill=PALE_GREEN,
        accent=GREEN,
        body_size=8.2,
    )
    c.showPage()


def page_6(c: canvas.Canvas) -> None:
    y = section_title(c, "Start", "Eerste ingebruikname", 6)
    y = numbered_steps(
        c,
        [
            ("Controleer het netwerk", "De M5Dial en Sonnenbatterie moeten bereikbaar zijn via hetzelfde vertrouwde lokale netwerk. Gebruik geen gastnetwerk met apparaat-isolatie."),
            ("Sluit USB-C aan", "Gebruik een 5 V voeding. Voor programmeren is een USB-C datakabel nodig; voor dagelijks voeden volstaat een betrouwbare voedingskabel."),
            ("Wacht op de eerste uitlezing", "Je ziet achtereenvolgens Starting, Reading en mogelijk Wi-Fi. Een eerste verbinding kan ongeveer 10 tot 15 seconden duren."),
            ("Controleer SOC", "Vergelijk het grote percentage met de Sonnen-app of het lokale dashboard. De firmware gebruikt bij voorkeur USOC, de gebruikersweergave van de batterij."),
            ("Controleer de modus", "Mode 2 betekent normaal AUTO/zelfverbruik. Mode 1 betekent handmatige regeling. Andere waarden kunnen modelspecifiek zijn."),
            ("Voer een veilige bedieningstest uit", "Selecteer STATUS en druk kort. Test daarna alleen indien gewenst met 100 W, en zet de batterij meteen terug op AUTO."),
        ],
        M,
        y,
        W - 2 * M,
        size=8.9,
        gap=10,
    )
    y = callout(
        c,
        "Geen instellingen op het scherm",
        "Wifi-naam, wifi-wachtwoord, batterijadres en API-token worden vóór het uploaden in een privéconfiguratie gezet. "
        "Je voert ze niet op de M5Dial zelf in. Dit staat stap voor stap in de afzonderlijke installateurshandleiding.",
        M,
        y,
        W - 2 * M,
        fill=PALE_BLUE,
        accent=BLUE,
        body_size=8.8,
    )
    label(c, "Geslaagde start", M, y - 3, color=GREEN)
    y = bullets(c, ["Er staat een echt SOC-percentage.", "PV, USE, GRID en BAT tonen waarden in watt.", "Bovenaan staat Mode 2 of een andere geldige modus.", "De onderste balk toont < STATUS >."], M, y - 20, W - 2 * M, size=8.7, leading=11.4, gap=3)
    c.showPage()


def page_7(c: canvas.Canvas) -> None:
    y = section_title(c, "Scherm", "Het statusscherm lezen", 7)
    draw_screen(c, M + 8, 470, 250)
    x = 332
    label(c, "Wat je ziet", x, y, color=BLUE)
    ty = y - 22
    explain = [
        ("Statusregel", "Mode 2, Reading, Wi-Fi, Charge W of een foutmelding."),
        ("Schaal + SOC", "De streepjes en het grote percentage tonen de vulling van de batterij."),
        ("Vier vermogens", "Actuele energiestromen in watt. Kleine verschillen en afronding zijn normaal."),
        ("Onderste balk", "De geselecteerde actie. Draai om een andere actie te kiezen."),
    ]
    for title, body in explain:
        c.setFont("DV-Bold", 8.9)
        c.setFillColor(INK)
        c.drawString(x, ty, title)
        ty = paragraph(c, body, x, ty - 14, W - M - x, size=7.9, leading=10.8, color=MUTED)
        ty -= 10
    rows = [
        ["SOC", "51%", "Bruikbare laadstatus van de batterij."],
        ["PV", "+2350W", "Zonneproductie. Normaal positief."],
        ["USE", "+620W", "Actueel verbruik van woning/installatie."],
        ["GRID", "+730W", "Positief = teruglevering. Negatief = afname van het net."],
        ["BAT", "+1000W", "Positief = batterij laadt."],
        ["BAT", "-1000W", "Negatief = batterij ontlaadt."],
    ]
    draw_table(c, ["Veld", "Voorbeeld", "Betekenis"], rows, M, 445, [65, 90, W - 2 * M - 155], font_size=7.8)
    callout(
        c,
        "Waarom het BAT-teken afwijkt van de ruwe API",
        "De Sonnen API rapporteert Pac_total_W positief bij ontladen en negatief bij laden. De afstandsbediening draait "
        "dit bewust om: voor de gebruiker betekent BAT + laden en BAT - ontladen.",
        M,
        166,
        W - 2 * M,
        fill=PALE_BLUE,
        accent=BLUE,
        body_size=8.3,
    )
    c.showPage()


def page_8(c: canvas.Canvas) -> None:
    y = section_title(c, "Bediening", "Draaien, drukken en het menu", 8)
    y = paragraph(c, "De firmware gebruikt twee handelingen: draaien aan de ring en het ronde scherm fysiek indrukken. De touchsensor wordt niet gebruikt; vegen of licht aantikken heeft daarom geen functie.", M, y, W - 2 * M, size=9.6, leading=13.4)
    y -= 12
    cards = [
        ("DRAAIEN", "Menu kiezen of wattage wijzigen", GREEN),
        ("KORT DRUKKEN", "Selecteren, starten of bevestigen", BLUE),
        ("LANG DRUKKEN", "Minimaal 1,2 s: annuleren of dimmen", ORANGE),
    ]
    gap = 15
    cw = (W - 2 * M - 2 * gap) / 3
    for i, (title, body, color) in enumerate(cards):
        x = M + i * (cw + gap)
        c.setFillColor(white)
        c.setStrokeColor(color)
        c.roundRect(x, y - 112, cw, 112, 8, fill=1, stroke=1)
        c.setFillColor(color)
        c.circle(x + cw / 2, y - 29, 15, fill=0, stroke=1)
        if i == 0:
            arrow(c, x + cw / 2 - 7, y - 29, x + cw / 2 + 7, y - 29, color, 1.6)
        elif i == 1:
            c.circle(x + cw / 2, y - 29, 5, fill=1, stroke=0)
        else:
            c.setFont("DV-Bold", 7)
            c.drawCentredString(x + cw / 2, y - 31, "1,2s")
        c.setFillColor(INK)
        c.setFont("DV-Bold", 8.1)
        c.drawCentredString(x + cw / 2, y - 58, title)
        paragraph(c, body, x + 12, y - 76, cw - 24, size=7.5, leading=10.2, color=MUTED)
    y -= 139
    label(c, "Menuvolgorde", M, y, color=ORANGE)
    draw_menu_carousel(c, M, y - 52, W - 2 * M)
    y -= 104
    rows = [
        ["STATUS", "Leest de actuele waarden opnieuw uit. Wijzigt de batterij niet."],
        ["AUTO", "Zet de Sonnenbatterie direct terug naar automatische zelfverbruiksregeling."],
        ["CHARGE", "Opent eerst de wattagekeuze. Een tweede korte druk verzendt laden."],
        ["DISCH", "Opent eerst de wattagekeuze. Een tweede korte druk verzendt ontladen."],
        ["DIM", "Dimt het scherm. De huidige firmware schakelt niet volledig uit."],
    ]
    y = draw_table(c, ["Optie", "Functie"], rows, M, y, [85, W - 2 * M - 85], font_size=7.9)
    callout(c, "Wakker maken zonder verrassing", "Draai één klik om een gedimd scherm wakker te maken. De selectie verschuift daarbij ook één positie; controleer dus de onderste balk voordat je drukt.", M, y, W - 2 * M, fill=PALE_ORANGE, accent=ORANGE, body_size=8.4)
    c.showPage()


def page_9(c: canvas.Canvas) -> None:
    y = section_title(c, "Bediening", "STATUS en AUTO", 9)
    label(c, "STATUS - alleen uitlezen", M, y, color=GREEN)
    y -= 18
    y = draw_flow(c, ["Draai naar STATUS", "Druk kort", "Reading / WORKING", "Nieuwe waarden"], M, y, W - 2 * M, accent=GREEN)
    y = paragraph(c, "STATUS maakt wifi actief, leest /api/v2/status, werkt het scherm bij en schakelt wifi daarna weer uit. Deze actie wijzigt geen instelling in de Sonnenbatterie.", M, y, W - 2 * M, size=9.2, leading=13)
    y -= 15
    label(c, "AUTO - normale regeling herstellen", M, y, color=BLUE)
    y -= 18
    y = draw_flow(c, ["Draai naar AUTO", "Druk één keer", "AUTO controleren", "Mode 2 bevestigd"], M, y, W - 2 * M, accent=BLUE)
    y = paragraph(c, "AUTO stuurt onmiddellijk een schrijfcommando. Daarna leest de M5Dial de batterij na 2 seconden en vervolgens elke 2 seconden opnieuw uit, maximaal 12 seconden lang. De controle is geslaagd zodra OperatingMode 2 wordt gemeten: automatische zelfverbruiksregeling.", M, y, W - 2 * M, size=9.0, leading=12.7)
    y -= 12
    y = callout(c, "Wanneer AUTO gebruiken?", "Na iedere handmatige laad- of ontlaadactie, wanneer het ingestelde vermogen niet meer nodig is, en wanneer je onzeker bent welke handmatige modus actief is.", M, y, W - 2 * M, fill=PALE_GREEN, accent=GREEN, body_size=9)
    label(c, "Wat je na AUTO controleert", M, y - 2, color=ORANGE)
    bullets(c, ["Bovenaan verschijnt eerst AUTO controleren.", "Bij een geslaagde controle verschijnt Mode 2.", "BAT blijft altijd de werkelijk gemeten waarde; AUTO kan zelf laden of ontladen en hoeft BAT dus niet op 0 W te zetten.", "Verschijnt AUTO niet bevestigd, gebruik dan het officiële Sonnen-dashboard om AUTO te herstellen en controleer daarna STATUS."], M, y - 20, W - 2 * M, size=8.7, leading=11.8, gap=4)
    c.showPage()


def page_10(c: canvas.Canvas) -> None:
    y = section_title(c, "Bediening", "Handmatig laden", 10)
    y = callout(c, "Begin laag", "Gebruik voor een eerste praktijktest 100 W of 500 W. De huidige bovengrens is 3600 W, maar de Sonnenbatterie bepaalt zelf wat technisch en energetisch toegestaan is.", M, y, W - 2 * M, fill=PALE_ORANGE, accent=ORANGE, body_size=9)
    y = numbered_steps(
        c,
        [
            ("Kies CHARGE", "Draai totdat < CHARGE > onderin staat."),
            ("Open de wattagekeuze", "Druk kort. Er is nu nog geen laadopdracht verstuurd."),
            ("Stel het vermogen in", "Draai in stappen van 100 W. Het bereik loopt van 0 tot 3600 W; de startwaarde is doorgaans de laatst gekozen waarde."),
            ("Controleer nogmaals", "Lees het grote getal en controleer dat bovenaan Charge W staat."),
            ("Bevestig", "Druk kort. Nu schakelt de firmware naar handmatige modus en stuurt zij het laadsetpoint."),
            ("Laat de automatische controle lopen", "Bovenaan staat Doel +500W. De M5Dial leest na 2 seconden en daarna elke 2 seconden de echte status; BAT moet positief worden."),
            ("Sluit af met AUTO", "Wanneer handmatig laden niet meer nodig is: selecteer AUTO en druk één keer."),
        ],
        M,
        y,
        W - 2 * M,
        size=8.6,
        gap=7,
    )
    y = callout(c, "Annuleren vóór verzenden", "Houd de knop minimaal 1,2 seconde ingedrukt terwijl het wattage zichtbaar is. De tekst Cancelled verschijnt en er wordt geen setpoint verstuurd.", M, y, W - 2 * M, fill=PALE_BLUE, accent=BLUE, body_size=8.5)
    label(c, "Verwachte schermreactie", M, y - 2, color=GREEN)
    y -= 20
    y = draw_flow(c, ["CHARGE", "500 W", "Doel +500W", "echte BAT +...W", "AUTO"], M, y, W - 2 * M, accent=GREEN)
    paragraph(c, "De controle duurt maximaal 12 seconden. Doel niet bereikt betekent dat het gemeten vermogen buiten de controlemarge bleef. De werkelijke BAT-waarde kan afwijken door SOC, vermogenslimieten, temperatuur, reserve, PV en het energiemanagement van de batterij.", M, y, W - 2 * M, size=8.1, leading=11.1, color=MUTED)
    c.showPage()


def page_11(c: canvas.Canvas) -> None:
    y = section_title(c, "Bediening", "Handmatig ontladen", 11)
    y = callout(c, "Let op de laadstatus", "Ontlaad niet bewust voorbij een noodzakelijke reserve of noodstroombuffer. De batterij kan een opdracht begrenzen of weigeren; dat is beveiligingsgedrag, geen reden om de limieten te omzeilen.", M, y, W - 2 * M, fill=PALE_RED, accent=RED, body_size=9)
    y = numbered_steps(
        c,
        [
            ("Kies DISCH", "Draai totdat < DISCH > onderin staat."),
            ("Open de wattagekeuze", "Druk kort. Er is nog geen ontlaadopdracht verstuurd."),
            ("Stel het vermogen in", "Draai in stappen van 100 W, bij een eerste test bijvoorbeeld naar 100 W of 500 W."),
            ("Controleer nogmaals", "Lees het wattage en controleer dat bovenaan Disch W staat."),
            ("Bevestig", "Druk kort. De firmware zet de batterij in handmatige modus en stuurt het ontlaadsetpoint."),
            ("Laat de automatische controle lopen", "Bovenaan staat Doel -500W. De M5Dial leest na 2 seconden en daarna elke 2 seconden de echte status; BAT moet negatief worden."),
            ("Sluit af met AUTO", "Selecteer AUTO en druk één keer om de normale zelfverbruiksregeling te herstellen."),
        ],
        M,
        y,
        W - 2 * M,
        size=8.6,
        gap=7,
    )
    y = callout(c, "Annuleren vóór verzenden", "Houd de knop minimaal 1,2 seconde ingedrukt in de wattagekeuze. Bij Cancelled is geen ontlaadsetpoint verstuurd.", M, y, W - 2 * M, fill=PALE_BLUE, accent=BLUE, body_size=8.5)
    label(c, "Verwachte schermreactie", M, y - 2, color=BLUE)
    y -= 20
    y = draw_flow(c, ["DISCH", "500 W", "Doel -500W", "echte BAT -...W", "AUTO"], M, y, W - 2 * M, accent=BLUE)
    paragraph(c, "De controle duurt maximaal 12 seconden. Doel niet bereikt betekent dat het gemeten vermogen buiten de controlemarge bleef. Wanneer de woning minder vraagt dan de ingestelde ontlading, kan een deel naar het net gaan; controleer daarom ook GRID.", M, y, W - 2 * M, size=8.1, leading=11.1, color=MUTED)
    c.showPage()


def page_12(c: canvas.Canvas) -> None:
    y = section_title(c, "Netwerk", "Wifi, bereik en automatisch verversen", 12)
    y = draw_network(c, M, y, W - 2 * M)
    y = paragraph(c, "De huidige firmware praat rechtstreeks met het lokale IP-adres van de Sonnenbatterie. De M5Dial moet daarom op een wifi-netwerk zitten dat dit adres kan bereiken.", M, y, W - 2 * M, size=9.5, leading=13.5)
    y -= 10
    rows = [
        ["Na een opdracht", "Na 2 s, dan elke 2 s", "Maximaal 12 s; controleert echte BAT of Mode 2."],
        ["Korte nacontrole", "Elke 5 s, 30 s lang", "Volgt het verdere stabiliseren van de batterij."],
        ["Normaal actief", "Elke 10 s", "Als |BAT| ten minste 100 W is."],
        ["Normaal rustig", "Elke 60 s", "Als de batterij minder dan 100 W doet."],
        ["Na fout", "Elke 20 s", "Automatische nieuwe poging zonder draaien."],
    ]
    y = draw_table(c, ["Situatie", "Interval", "Uitleg"], rows, M, y, [142, 112, W - 2 * M - 254], font_size=7.25, row_pad=4.2)
    label(c, "Netwerkvoorwaarden", M, y - 2, color=GREEN)
    y = bullets(c, ["Alleen 2,4 GHz wifi; een gemengd 2,4/5 GHz netwerk werkt meestal zolang 2,4 GHz beschikbaar is.", "Wifi-naam en wachtwoord zijn in de firmware vastgelegd. Bij een nieuwe router is opnieuw configureren en uploaden nodig.", "Reserveer bij voorkeur een vast DHCP-adres voor de Sonnenbatterie, zodat het lokale IP niet verandert.", "Een gastnetwerk, client isolation of firewallregel kan lokaal verkeer blokkeren.", "Internet is niet nodig voor de lokale API-call, maar de Sonnenbatterie kan internet wel nodig hebben voor eigen diensten en support."], M, y - 20, W - 2 * M, size=8.5, leading=11.6, gap=3)
    callout(c, "Buiten het thuisnetwerk", "De M5Dial bevat geen Tailscale-client en gebruikt momenteel geen Home Assistant-proxy. Op een willekeurig wifi-netwerk kan hij de lokale Sonnenbatterie dus niet bereiken, tenzij dat netwerk zelf een veilige route naar het thuis-LAN aanbiedt.", M, 139, W - 2 * M, fill=PALE_RED, accent=RED, body_size=8.5)
    c.showPage()


def page_13(c: canvas.Canvas) -> None:
    y = section_title(c, "Hulp", "Meldingen en foutcodes", 13)
    y = paragraph(c, "De kleine tekst bovenaan en de onderste balk vertellen wat de firmware doet. Bij een fout wordt de accentkleur rood en staat onderin PRESS TO RETRY.", M, y, W - 2 * M, size=9.5, leading=13.5)
    y -= 10
    rows = [
        ["Starting", "Firmware start op.", "Wacht op de eerste statuscall."],
        ["Reading / WORKING", "Bezig met wifi of API.", "Niet opnieuw drukken; enkele seconden wachten."],
        ["Wi-Fi", "Bezig verbinding te maken.", "Normaal kort zichtbaar."],
        ["Mode 2", "AUTO/zelfverbruik actief.", "Normale toestand na AUTO."],
        ["Mode 1", "Handmatige regeling actief.", "Controleer of laden/ontladen bewust is gekozen."],
        ["Doel +...W / -...W", "De opdracht wordt gecontroleerd.", "Wacht; BAT toont ondertussen de echt gemeten waarde."],
        ["AUTO controleren", "Terugkeer naar AUTO wordt gecontroleerd.", "Wacht tot Mode 2 verschijnt."],
        ["Doel niet bereikt", "BAT bleef buiten de controlemarge.", "Controleer limieten en herstel zo nodig AUTO."],
        ["AUTO niet bevestigd", "Mode 2 kwam niet binnen 12 s terug.", "Herstel AUTO via het officiële dashboard."],
        ["Wi-Fi timeout", "Geen verbinding binnen 9 s.", "Controleer SSID, wachtwoord, bereik en 2,4 GHz."],
        ["HTTP -1 / begin failed", "Batterijadres niet bereikbaar.", "Controleer IP, poort, LAN en firewall."],
        ["HTTP 401 / 403", "Authenticatie geweigerd.", "Controleer API-token en rechten."],
        ["HTTP 404", "API-pad bestaat niet.", "Controleer batterijmodel, softwareversie en paden."],
        ["SOC missing", "Statusantwoord mist bekend SOC-veld.", "API-versie of antwoord wijkt af; laat configuratie controleren."],
        ["Writes locked", "Schrijfopdrachten uitgeschakeld.", "SONNEN_ALLOW_WRITES staat op 0; status blijft bruikbaar."],
        ["Demo only", "Demomodus actief.", "Upload echte configuratie; er gaat geen commando naar de batterij."],
        ["Cancelled", "Wattagekeuze of fout is geannuleerd.", "Geen setpoint verzonden als je nog in de keuze zat."],
        ["Dimmed", "Scherm is handmatig gedimd.", "Draai één klik om terug te keren."],
    ]
    draw_table(c, ["Melding", "Betekenis", "Actie"], rows, M, y, [116, 158, W - 2 * M - 274], font_size=6.2, row_pad=3.5)
    c.showPage()


def page_14(c: canvas.Canvas) -> None:
    y = section_title(c, "Hulp", "Problemen oplossen", 14)
    issues = [
        ("Scherm is zwart of erg donker", ["Draai één klik; de firmware dimt na 2 minuten.", "Controleer USB-C of de accuschakelaar.", "Trek USB los, wacht 5 seconden en sluit opnieuw aan.", "Probeer een andere 5 V kabel of adapter."]),
        ("Percentage loopt achter", ["Bij actief batterijvermogen komt normaal elke 10 seconden een update; in rust elke 60 seconden.", "Kies STATUS voor een directe uitlezing.", "Controleer wifi als Reading of een foutmelding blijft staan."]),
        ("Laad- of ontlaadopdracht lijkt niets te doen", ["Laat Doel +...W of Doel -...W maximaal 12 seconden controleren.", "BAT toont tijdens de controle uitsluitend de echt gemeten waarde.", "Doel niet bereikt kan komen door SOC, temperatuur, reserve of systeemlimieten.", "Zet bij twijfel AUTO en controleer via het Sonnen-dashboard."]),
        ("Steeds Wi-Fi timeout", ["Controleer of het ingestelde wifi nog bestaat en 2,4 GHz aanbiedt.", "Plaats de Dial dichter bij de router.", "Gebruik geen geïsoleerd gastnetwerk.", "Bij veranderd SSID of wachtwoord moet de firmware opnieuw worden geconfigureerd."]),
    ]
    x_positions = [M, W / 2 + 6]
    top = y
    card_w = W / 2 - M - 14
    for i, (title, points) in enumerate(issues):
        col = i % 2
        row = i // 2
        x = x_positions[col]
        yy = top - row * 252
        c.setFillColor(white)
        c.setStrokeColor(BLUE if col == 0 else ORANGE)
        c.roundRect(x, yy - 225, card_w, 225, 8, fill=1, stroke=1)
        title_lines = wrap(title, "DV-Bold", 9.5, card_w - 28)
        c.setFont("DV-Bold", 9.5)
        c.setFillColor(INK)
        title_y = yy - 24
        for line in title_lines:
            c.drawString(x + 14, title_y, line)
            title_y -= 12
        bullets(c, points, x + 12, yy - 49 - (len(title_lines) - 1) * 12, card_w - 24, size=8.0, leading=11.2, gap=4, dot=BLUE if col == 0 else ORANGE)
    y = top - 516
    y = callout(c, "Bij een rood foutscherm", "Een korte druk voert eerst een STATUS-poging uit, ongeacht welke menuoptie eerder was geselecteerd. Een lange druk annuleert de foutweergave. De firmware probeert daarnaast automatisch opnieuw na 20 seconden.", M, y, W - 2 * M, fill=PALE_RED, accent=RED, body_size=8.6)
    callout(c, "Niet eindeloos herhalen", "Blijft een opdracht mislukken, stuur dan geen reeks nieuwe setpoints. Herstel AUTO via het officiële dashboard en controleer netwerk, API-token en batterijstatus.", M, y, W - 2 * M, fill=PALE_ORANGE, accent=ORANGE, body_size=8.6)
    c.showPage()


def page_15(c: canvas.Canvas) -> None:
    y = section_title(c, "M5Dial", "Voeding van de M5Dial", 15)
    y = paragraph(c, "Dit hoofdstuk gaat uitsluitend over de voeding van de M5Dial-afstandsbediening, niet over de grote Sonnenbatterie. In dit apparaat is een 3,7 V / 500 mAh 1S-lithiumaccu ingebouwd. De firmware is ingesteld op goed leesbaar gebruik, niet op maximale accuduur: het scherm staat actief op helderheid 230, dimt na 2 minuten naar 55 en schakelt niet automatisch volledig uit. Wifi wordt na iedere API-call uitgezet.", M, y, W - 2 * M, size=9.0, leading=12.7)
    y -= 12
    # Battery capacity illustration.
    x = M
    bw, bh = 220, 92
    c.setStrokeColor(DARK)
    c.setLineWidth(2)
    c.roundRect(x, y - bh, bw, bh, 9, fill=0, stroke=1)
    c.rect(x + bw, y - bh / 2 - 12, 10, 24, fill=0, stroke=1)
    c.setFillColor(GREEN)
    c.roundRect(x + 7, y - bh + 7, bw * 0.72, bh - 14, 5, fill=1, stroke=0)
    c.setFillColor(DARK)
    c.setFont("DV-Bold", 15)
    c.drawCentredString(x + bw / 2, y - 42, "3,7 V x 500 mAh")
    c.setFont("DV-Bold", 10)
    c.drawCentredString(x + bw / 2, y - 61, "ongeveer 1,85 Wh")
    bx = 310
    callout(c, "Ordegrootte, geen garantie", "M5Stack noemt tijdens bedrijf ongeveer 0,84 tot 1,01 W, afhankelijk van de voedingswijze. 1,85 Wh gedeeld door 0,84 tot 1,01 W geeft theoretisch ongeveer 1,8 tot 2,2 uur vóór omzettingsverliezen. Reken praktisch op circa 1,5 tot 2 uur en meet het eigen apparaat; dimmen kan helpen, terwijl wifi, acculeeftijd en bedrading de duur beïnvloeden.", bx, y, W - M - bx, fill=PALE_BLUE, accent=BLUE, body_size=7.55)
    y -= 122
    rows = [
        ["Ingebouwd: 3,7 V / 500 mAh 1S", "ca. 1,85 Wh", "Witte accuconnector; praktisch circa 1,5 tot 2 uur."],
        ["USB-C 5 V", "Netvoeding", "Beste keuze voor permanent zichtbaar gebruik."],
        ["Groene ingang 6-36 V", "Externe bron", "Alleen door een deskundige aansluiten; zie installateurshandleiding."],
    ]
    y = draw_table(c, ["Voorbeeld", "Energie", "Praktische betekenis"], rows, M, y, [150, 90, W - 2 * M - 240], font_size=7.8)
    label(c, "Accuveiligheid", M, y - 2, color=RED)
    y = bullets(c, ["Gebruik geen bolle, beschadigde, warme of lekkende lithiumaccu.", "Controleer connectorformaat én polariteit met documentatie of multimeter; kleur alleen is geen garantie.", "Gebruik voor de witte aansluiting uitsluitend een passende 3,7 V 1S-accu; sluit hier nooit 7,4 V op aan.", "Zorg voor trekontlasting en bescherming tegen kortsluiting in de behuizing.", "Laad niet onbeheerd en volg de instructies van accufabrikant, lader en M5Stack.", "De officiële slaapstroom van 1,9 µA geldt alleen bij echte power-off/slaap. Die functie staat in deze firmware uit."], M, y - 20, W - 2 * M, size=8.3, leading=11.4, gap=3, dot=RED)
    c.showPage()


def installer_cover(c: canvas.Canvas) -> None:
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    cover_image(c, CASE_PHOTO, 0, 320, W, H - 320)
    c.saveState()
    c.setFillAlpha(0.76)
    c.setFillColor(DARK)
    c.rect(0, 320, W, 88, fill=1, stroke=0)
    c.restoreState()
    c.setFillColor(BLUE)
    c.rect(0, 0, 10, 320, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont("DV-Bold", 8)
    c.drawString(48, 283, "INSTALLATEURSHANDLEIDING")
    c.setFillColor(white)
    c.setFont("DV-Bold", 25)
    c.drawString(48, 239, "M5Dial Sonnenbatterie-")
    c.drawString(48, 204, "afstandsbediening")
    c.setFont("DV", 11)
    c.setFillColor(HexColor("#C9D3D2"))
    c.drawString(48, 164, "Installeren, configureren, testen, onderhouden en veilig opleveren")
    c.setFillColor(PANEL)
    c.roundRect(48, 103, 230, 34, 7, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("DV-Bold", 8.5)
    c.drawString(62, 116, "Versie 1.1  |  3 augustus 2026")
    c.setFillColor(HexColor("#8FA0A4"))
    c.setFont("DV", 7.2)
    c.drawString(48, 63, "Voor firmwarecommit 50f31c3 en de huidige apparaatconfiguratie")
    c.drawString(48, 48, "Bevat geen wifi-wachtwoord, API-token of ander geheim")
    c.showPage()


def installer_page_2(c: canvas.Canvas) -> None:
    y = section_title(c, "Start", "Doel en veiligheidsgrenzen", 2, document_name="Installateurshandleiding")
    y = paragraph(
        c,
        "Deze handleiding is bedoeld voor degene die de M5Dial-afstandsbediening assembleert, configureert, "
        "programmeert en overdraagt aan de gebruiker. Zij vult de gebruikershandleiding aan. Werk systematisch: "
        "eerst voeding en alleen-lezen, daarna pas een lage schrijftest.",
        M,
        y,
        W - 2 * M,
        size=9.6,
        leading=13.6,
    )
    y -= 10
    y = callout(
        c,
        "Werkgrens",
        "Deze handleiding gaat over de M5Dial en de lokale Sonnen API. Open of wijzig de Sonnenbatterie, "
        "netspanningsinstallatie of vaste batterijbekabeling niet. Laat dat uitsluitend uitvoeren door een "
        "daarvoor erkende installateur en volg altijd de actuele documentatie van de fabrikant.",
        M,
        y,
        W - 2 * M,
        fill=PALE_RED,
        accent=RED,
        body_size=8.8,
    )
    label(c, "Benodigd vóór de start", M, y - 3, color=GREEN)
    y = bullets(
        c,
        [
            "M5Stack Dial, USB-C-datakabel en betrouwbare 5 V voeding.",
            "Computer met deze repository en Arduino IDE 2 op de standaardlocatie.",
            "Een vertrouwd 2,4 GHz-netwerk waarop de M5Dial de Sonnenbatterie lokaal kan bereiken.",
            "Lokaal batterijadres en API-token, uitsluitend opgeslagen in sonnen_config.h.",
            "Toegang tot het officiële Sonnen-dashboard om AUTO zo nodig onafhankelijk te herstellen.",
        ],
        M,
        y - 20,
        W - 2 * M,
        size=8.5,
        leading=11.5,
        gap=3,
    )
    y -= 4
    label(c, "Inhoud", M, y, color=BLUE)
    contents = [
        ("Hardware en voeding", "3"),
        ("Wifi en Sonnen API instellen", "4"),
        ("Firmware installeren en uploaden", "5"),
        ("Inbedrijfstelling en functionele test", "6"),
        ("Onderhoud en technische gegevens", "7"),
        ("Oplevering, herstel en bronnen", "8"),
    ]
    ty = y - 23
    for i, (name, number) in enumerate(contents):
        col = i % 2
        row = i // 2
        x = M + col * 255
        yy = ty - row * 38
        c.setFillColor(white)
        c.setStrokeColor(LINE)
        c.roundRect(x, yy - 22, 238, 28, 4, fill=1, stroke=1)
        c.setFont("DV", 7.7)
        c.setFillColor(INK)
        c.drawString(x + 9, yy - 11, name)
        c.setFont("DV-Bold", 8)
        c.setFillColor(BLUE)
        c.drawRightString(x + 228, yy - 11, number)
    c.showPage()


def installer_page_3(c: canvas.Canvas) -> None:
    y = section_title(c, "Hardware", "Hardware en voeding", 3, document_name="Installateurshandleiding")
    y = paragraph(c, "De huidige afstandsbediening bevat een 3,7 V / 500 mAh 1S-lithiumaccu op de witte accuconnector. Gebruik USB-C voor de eerste ingebruikname en voor iedere firmware-upload. Controleer bij losse bedrading altijd spanning, polariteit, isolatie en trekontlasting voordat de voeding wordt ingeschakeld.", M, y, W - 2 * M, size=9.2, leading=13.1)
    y -= 10
    y = draw_power_diagram(c, M, y, W - 2 * M)
    rows = [
        ["USB-C", "5 V DC", "Eerste keuze voor uploaden, testen en permanent gebruik."],
        ["Witte accuplug", "3,7 V 1S / 500 mAh", "Ingebouwde M5Dial-accu; 1,25 mm 2-polig, polariteit controleren."],
        ["Groene klem", "6-36 V DC", "Externe voeding; + en - exact volgen. Geen laaduitgang voor een 2S-pakket."],
    ]
    y = draw_table(c, ["Aansluiting", "Spanning", "Installatie-eis"], rows, M, y, [100, 130, W - 2 * M - 230], font_size=7.35)
    y -= 4
    photo_w, photo_h = 142, 190
    contain_image(c, CASE_PHOTO, M, y - photo_h, photo_w, photo_h)
    c.setFillColor(MUTED)
    c.setFont("DV-Italic", 6.2)
    c.drawString(M, y - photo_h - 12, "Voorbeeldbehuizing.")
    c.drawString(M, y - photo_h - 22, "Geen elektrisch schema.")
    bx = M + photo_w + 18
    callout(c, "Witte aansluiting", "Sluit hier uitsluitend een 3,7 V 1S-accu met passende stekker en juiste polariteit aan. De ingebouwde capaciteit is 500 mAh, ongeveer 1,85 Wh. Sluit nooit een 7,4 V 2S-pakket op deze aansluiting aan.", bx, y, W - M - bx, fill=PALE_GREEN, accent=GREEN, body_size=8.0)
    callout(c, "Groene aansluiting", "Een 2S/7,4 V pakket mag alleen op de groene 6-36 V ingang en heeft een eigen 2S-BMS, zekering en geschikte 2S-lader nodig. De groene ingang voedt de M5Dial, maar laadt het 2S-pakket niet.", bx, y - 116, W - M - bx, fill=PALE_ORANGE, accent=ORANGE, body_size=8.0)
    callout(c, "Laatste controle", "Gebruik één voedingsbron tegelijk tijdens de eerste test. Controleer dat geen draad kan klemmen tegen de encoder, USB-C-poort of scherpe delen van de behuizing.", bx, y - 232, W - M - bx, fill=PALE_BLUE, accent=BLUE, body_size=8.0)
    c.showPage()


def installer_page_4(c: canvas.Canvas) -> None:
    y = section_title(c, "Configuratie", "Wifi en Sonnen API instellen", 4, document_name="Installateurshandleiding")
    y = paragraph(c, "Deze pagina is alleen nodig bij een nieuwe batterij, router, wifi-naam of API-token. De instellingen worden in sonnen_config.h gezet en daarna samen met de firmware geüpload.", M, y, W - 2 * M, size=9.4, leading=13.3)
    y -= 10
    y = callout(c, "API-token invoeren", "De token wordt op de computer ingevuld vóór het uploaden, niet op het ronde scherm. Bij veel systemen staat hij in het lokale Sonnen-dashboard onder Software-Integration. Ontbreekt die optie, vraag de installateur of Sonnen-support naar lokale API-toegang voor jouw model en softwareversie.", M, y, W - 2 * M, fill=PALE_BLUE, accent=BLUE, body_size=8.7)
    steps = [
        ("Vind het lokale batterijadres", "Bekijk de apparatenlijst in de router en reserveer het adres bij voorkeur via DHCP."),
        ("Test eerst alleen lezen", "Voer vanaf de computer een statuscall uit. Pas verder gaan wanneer SOC en vermogensvelden worden herkend."),
        ("Maak de privéconfiguratie", "Vul wifi, host en token in. Houd SONNEN_ALLOW_WRITES eerst op 0."),
        ("Upload en test STATUS", "Controleer echte waarden op de M5Dial zonder schrijfcommando's."),
        ("Schakel schrijven bewust in", "Zet writes pas op 1 na een geslaagde read-only test. Begin met een lage setpointlimiet."),
    ]
    y = numbered_steps(c, steps, M, y, W - 2 * M, size=8.2, gap=6)
    label(c, "Voorbeeldcommando's vanaf de repositorymap", M, y - 2, color=GREEN)
    y = draw_code(c, [
        "scripts/sonnen-probe status \\",
        "  --host 192.168.x.x --token 'JOUW_TOKEN'",
        "",
        "scripts/sonnen-probe make-config --force \\",
        "  --wifi-ssid 'JOUW_WIFI' --wifi-password 'WACHTWOORD' \\",
        "  --host 192.168.x.x --token 'JOUW_TOKEN' \\",
        "  --max-setpoint-w 500 --dim-after-ms 120000 \\",
        "  --sleep-after-ms 0 --active-brightness 230 \\",
        "  --dim-brightness 55",
    ], M, y - 18, W - 2 * M, size=6.65)
    callout(c, "Geheim houden", "sonnen_config.h kan je wifi-wachtwoord en API-token bevatten. Publiceer dit bestand nooit, stuur het niet mee in screenshots en controleer vóór iedere GitHub-commit dat het ontbreekt.", M, y, W - 2 * M, fill=PALE_RED, accent=RED, body_size=8.2)
    c.showPage()


def installer_page_5(c: canvas.Canvas) -> None:
    y = section_title(c, "Firmware", "Installeren en uploaden", 5, document_name="Installateurshandleiding")
    y = paragraph(c, "Voor de meegeleverde scripts is op macOS Arduino IDE 2 nodig op de standaardlocatie. Installeer daarnaast het ESP32-boardpakket van Espressif Systems en de M5Dial-library. Het bord heet M5Stack Dial; de technische bordcode is esp32:esp32:m5stack_dial.", M, y, W - 2 * M, size=9.1, leading=12.9)
    y -= 10
    label(c, "Bouwen en uploaden", M, y, color=GREEN)
    y = draw_code(c, [
        "cd /pad/naar/M5Dial-Sonnenbatterie-afstandsbediening",
        "scripts/sonnen-dial check",
        "scripts/sonnen-dial libs",
        "scripts/sonnen-dial compile",
        "scripts/sonnen-dial ports",
        "scripts/sonnen-dial upload /dev/cu.usbmodemXXXX",
    ], M, y - 18, W - 2 * M, size=7.2)
    y = numbered_steps(c, [
        ("Sluit de M5Dial met een datakabel aan", "Een laadkabel zonder datalijnen kan wel voeding geven maar verschijnt niet als seriële poort."),
        ("Compileer vóór uploaden", "Stop bij fouten; upload alleen een geslaagde build."),
        ("Kies de gevonden poort", "Op macOS lijkt die meestal op /dev/cu.usbmodemXXXX."),
        ("Wacht op de reset", "Na een geslaagde upload start de M5Dial opnieuw en leest hij de status."),
        ("Test STATUS, 100 W en AUTO", "Controleer eerst lezen, daarna de automatische doelcontrole en tenslotte de bevestigde terugkeer naar Mode 2."),
    ], M, y, W - 2 * M, size=8.2, gap=6)
    y = callout(c, "Zwart scherm na upload", "Trek USB-C los, wacht 5 seconden en sluit opnieuw aan. Verschijnt nog niets, probeer een andere kabel/poort en upload opnieuw. Een gedimd scherm wordt wakker door één klik te draaien.", M, y, W - 2 * M, fill=PALE_ORANGE, accent=ORANGE, body_size=8.5)
    label(c, "Fabrieksdemo terugzetten", M, y - 2, color=BLUE)
    y = bullets(c, ["Open de officiële M5Stack-pagina voor Dial.", "Gebruik de aangeboden Dial User Demo EasyLoader of M5Burner-route.", "Selecteer de juiste M5Dial en USB-poort en schrijf de demo opnieuw.", "De custom firmware en lokale configuratie worden overschreven; bewaar sonnen_config.h daarom privé als back-up.", "Je kunt deze afstandsbedieningsfirmware later altijd opnieuw uploaden."], M, y - 20, W - 2 * M, size=8.4, leading=11.5, gap=3, dot=BLUE)
    c.showPage()


def installer_page_6(c: canvas.Canvas) -> None:
    y = section_title(c, "Test", "Inbedrijfstelling en functionele test", 6, document_name="Installateurshandleiding")
    y = callout(
        c,
        "Begin zonder schrijftoegang",
        "Laat SONNEN_ALLOW_WRITES eerst op 0. Controleer via STATUS dat SOC, PV, USE, GRID, BAT en Mode "
        "plausibel zijn. Schakel schrijftoegang pas in nadat de alleen-lezen test volledig is geslaagd.",
        M,
        y,
        W - 2 * M,
        fill=PALE_BLUE,
        accent=BLUE,
        body_size=8.8,
    )
    steps = [
        ("Leg de uitgangssituatie vast", "Noteer SOC, Mode en BAT. Controleer dezelfde waarden in het officiële Sonnen-dashboard."),
        ("Test STATUS", "Kies STATUS en druk kort. De waarden moeten binnen ongeveer 5 tot 15 seconden actueel worden."),
        ("Test laden met 100 W", "Kies CHARGE, stel 100 W in en bevestig. Verwacht Doel +100W, Mode 1 en een positief gemeten BAT-vermogen."),
        ("Herstel AUTO", "Kies AUTO en bevestig. Verwacht AUTO controleren en daarna Mode 2."),
        ("Test ontladen met 100 W", "Kies DISCH, stel 100 W in en bevestig. Verwacht Doel -100W, Mode 1 en een negatief gemeten BAT-vermogen, voor zover toegestaan."),
        ("Eindig opnieuw met AUTO", "Bevestig AUTO, laat Mode 2 automatisch verifiëren en vergelijk het normale gedrag met het Sonnen-dashboard."),
    ]
    y = numbered_steps(c, steps, M, y, W - 2 * M, size=8.1, gap=6)
    label(c, "Acceptatiepunten", M, y - 1, color=GREEN)
    rows = [
        ["Status", "Echt SOC en actuele vermogenswaarden; geen blijvende foutmelding."],
        ["Laden", "Doel +100W; Mode 1; echt gemeten BAT positief."],
        ["AUTO na laden", "AUTO controleren eindigt met Mode 2."],
        ["Ontladen", "Doel -100W; Mode 1; echt gemeten BAT negatief."],
        ["Eindtoestand", "Mode 2; Sonnenbatterie gedraagt zich weer volgens zelfverbruik."],
    ]
    y = draw_table(c, ["Controle", "Geslaagd wanneer"], rows, M, y - 18, [120, W - 2 * M - 120], font_size=7.5, row_pad=4.6)
    callout(c, "Afwijking of twijfel", "Stop de test, stuur geen reeks nieuwe opdrachten en herstel AUTO via het officiële Sonnen-dashboard. Controleer daarna netwerk, API-token, batterijstatus, reserve, temperatuur en systeemlimieten.", M, y - 3, W - 2 * M, fill=PALE_RED, accent=RED, body_size=8.2)
    c.showPage()


def installer_page_7(c: canvas.Canvas) -> None:
    y = section_title(c, "Beheer", "Onderhoud en technische gegevens", 7, document_name="Installateurshandleiding")
    label(c, "Onderhoudscheck", M, y, color=GREEN)
    y = bullets(c, ["Na routerwissel: controleer SSID, wachtwoord en het vaste IP-adres van de Sonnenbatterie.", "Na een Sonnen-software-update: test STATUS en controleer Mode, SOC en tekens voordat je schrijft.", "Na firmware-update: voer een 100 W laad- en ontlaadtest uit en eindig met AUTO.", "Controleer accu, connectoren, schakelaar en behuizing regelmatig op warmte, slijtage en losse bedrading.", "Bewaar een versleutelde privéback-up van sonnen_config.h; de openbare GitHub-repository bevat dit bestand niet."], M, y - 20, W - 2 * M, size=8.6, leading=11.8, gap=3)
    y -= 4
    label(c, "Huidige apparaatinstellingen", M, y, color=ORANGE)
    rows = [
        ["Schrijfacties", "Ingeschakeld"],
        ["Wattage", "0-3600 W, stappen van 100 W, start 500 W"],
        ["Opdrachtcontrole", "Na 2 s, daarna elke 2 s, maximaal 12 s"],
        ["Controlemarge", "20% van doel, minimaal 25 W"],
        ["Korte nacontrole", "Elke 5 s gedurende 30 s"],
        ["Statusrefresh", "10 s actief, 60 s rustig, 20 s na fout"],
        ["Actief-drempel", "|BAT| vanaf 100 W"],
        ["Scherm", "Helderheid 230; dim 55 na 120 s"],
        ["Power-off", "Uitgeschakeld; DIM dimt alleen"],
        ["Ingebouwde accu", "3,7 V / 500 mAh 1S; circa 1,85 Wh"],
        ["Wifi", "2,4 GHz; radio uit na elke request"],
        ["Timeouts", "Wifi 9 s; HTTP 4,5 s"],
    ]
    y = draw_table(c, ["Onderdeel", "Instelling"], rows, M, y - 18, [145, W - 2 * M - 145], font_size=7.25, row_pad=4.0)
    label(c, "M5Dial hardware", M, y - 1, color=BLUE)
    rows2 = [
        ["Model", "M5Stack Dial / SKU K130 / ESP32-S3"],
        ["Scherm", "1,28 inch rond TFT, 240 x 240 pixels"],
        ["Encoder", "16 detents, 64 pulsen per omwenteling"],
        ["Voeding", "USB-C 5 V; achterklem 6-36 V; accu 3,7 V"],
        ["Accuconnector", "1,25 mm - 2 polig"],
        ["Temperatuur", "0 tot 40 °C volgens M5Stack"],
    ]
    draw_table(c, ["Onderdeel", "Specificatie"], rows2, M, y - 18, [145, W - 2 * M - 145], font_size=7.7, row_pad=4.8)
    c.showPage()


def installer_page_8(c: canvas.Canvas) -> None:
    y = section_title(c, "Oplevering", "Oplevering, herstel en bronnen", 8, document_name="Installateurshandleiding")
    label(c, "Oplevercheck met de gebruiker", M, y, color=GREEN)
    y = bullets(
        c,
        [
            "Laat STATUS zien en vergelijk SOC met het officiële Sonnen-dashboard.",
            "Laat CHARGE en DISCH alleen zien als schrijftoegang bewust is ingeschakeld.",
            "Demonstreer dat AUTO de batterij terugzet in Mode 2 en wijs Mode 2 boven in het scherm aan.",
            "Leg uit dat de ingebouwde M5Dial-accu 500 mAh is en praktisch circa 1,5 tot 2 uur meegaat.",
            "Overhandig de gebruikershandleiding en spreek af wie configuratie- en firmwarewijzigingen beheert.",
        ],
        M,
        y - 20,
        W - 2 * M,
        size=8.5,
        leading=11.6,
        gap=3,
    )
    y -= 3
    y = callout(c, "Privégegevens", "Bewaar wifi-naam, wachtwoord, lokaal batterijadres en API-token alleen in een beveiligde privéback-up van sonnen_config.h. Zet deze gegevens nooit in Git, GitHub, screenshots, de PDF of een openbaar servicerapport.", M, y, W - 2 * M, fill=PALE_RED, accent=RED, body_size=8.5)
    label(c, "Snelle herstelkaart", M, y - 2, color=ORANGE)
    rows = [
        ["Zwart scherm", "Voeding en kabel controleren; USB 5 seconden los; opnieuw aansluiten."],
        ["Wifi timeout", "2,4 GHz, SSID, wachtwoord, bereik en gastnetwerkisolatie controleren."],
        ["HTTP 401 / 403", "API-token en lokale API-rechten controleren."],
        ["Geen actuele status", "Lokaal batterijadres en netwerkroute testen met sonnen-probe status."],
        ["Doel niet bereikt", "Echte BAT controleren; limieten nagaan; AUTO herstellen; niet herhalen."],
        ["AUTO niet bevestigd", "AUTO via officieel dashboard herstellen en Mode 2 controleren."],
        ["Verkeerd gedrag", "STATUS, daarna AUTO; Mode 2 controleren; zo nodig firmware opnieuw uploaden."],
    ]
    y = draw_table(c, ["Probleem", "Eerste actie"], rows, M, y - 18, [125, W - 2 * M - 125], font_size=7.25, row_pad=4.6)
    label(c, "Bronnen", M, y - 1, color=BLUE)
    sources = [
        ("Project en firmware", "github.com/Tallestxxl/M5Dial-Sonnenbatterie-afstandsbediening", "https://github.com/Tallestxxl/M5Dial-Sonnenbatterie-afstandsbediening"),
        ("M5Dial-documentatie", "docs.m5stack.com/en/core/M5Dial", "https://docs.m5stack.com/en/core/M5Dial"),
        ("Behuizing", "printables.com/model/992288-m5stack-dial-case/files", "https://www.printables.com/model/992288-m5stack-dial-case/files"),
        ("Sonnen release notes", "sonnen.de/rln-sb", "https://www.sonnen.de/rln-sb"),
    ]
    source_y = y - 21
    for i, (title, display, url) in enumerate(sources):
        yy = source_y - i * 35
        c.setFillColor(white)
        c.setStrokeColor(LINE)
        c.roundRect(M, yy - 24, 350, 28, 5, fill=1, stroke=1)
        c.setFont("DV-Bold", 7.2)
        c.setFillColor(INK)
        c.drawString(M + 9, yy - 8, title)
        c.setFont("DV", 6.1)
        c.setFillColor(BLUE)
        c.drawString(M + 9, yy - 18, display)
        c.linkURL(url, (M, yy - 24, M + 350, yy + 4), relative=0)
    draw_qr(c, sources[0][2], W - M - 96, source_y - 82, 92)
    c.setFont("DV", 6.3)
    c.setFillColor(MUTED)
    c.drawCentredString(W - M - 50, source_y - 95, "QR: GitHub-repository")
    c.showPage()


def user_page_16(c: canvas.Canvas) -> None:
    y = section_title(c, "Naslag", "Snelle bedieningskaart", 16)
    c.setFillColor(DARK)
    c.roundRect(M, y - 178, W - 2 * M, 178, 10, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont("DV-Bold", 12)
    c.drawString(M + 18, y - 27, "DAGELIJKS")
    quick = [
        "Draai: kies STATUS / AUTO / CHARGE / DISCH / DIM",
        "Kort drukken: uitvoeren of bevestigen",
        "Lang drukken (1,2 s): annuleren of dimmen",
        "CHARGE: eerste druk kiest wattage, tweede druk verzendt",
        "DISCH: eerste druk kiest wattage, tweede druk verzendt",
        "Na een opdracht: wacht op echte BAT; kies daarna AUTO en wacht op Mode 2",
    ]
    bullets(c, quick, M + 16, y - 52, W - 2 * M - 32, size=8.7, leading=11.5, gap=2.5, color=white, dot=GREEN)
    y -= 198
    label(c, "Tekens", M, y, color=ORANGE)
    rows = [
        ["GRID +", "teruglevering aan het net"],
        ["GRID -", "afname van het net"],
        ["BAT +", "batterij laadt"],
        ["BAT -", "batterij ontlaadt"],
        ["Mode 2", "AUTO / zelfverbruik"],
        ["Mode 1", "handmatige regeling"],
    ]
    y = draw_table(c, ["Scherm", "Betekenis"], rows, M, y - 18, [110, 235], font_size=7.7, row_pad=4.4)
    bx = M + 365
    c.setFillColor(PALE_RED)
    c.setStrokeColor(RED)
    c.roundRect(bx, y + 5, W - M - bx, 184, 7, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DV-Bold", 9)
    c.drawString(bx + 12, y + 166, "BIJ TWIJFEL")
    paragraph(c, "1. Wacht 10 seconden.\n2. Kies STATUS.\n3. Kies AUTO.\n4. Controleer Mode 2.\n5. Gebruik bij storing het officiële Sonnen-dashboard.", bx + 12, y + 145, W - M - bx - 24, size=7.8, leading=15, font="DV-Bold")
    y -= 18
    label(c, "Bronnen en downloads", M, y, color=BLUE)
    source_y = y - 20
    sources = [
        ("Project en firmware", "github.com/Tallestxxl/M5Dial-Sonnenbatterie-afstandsbediening", "https://github.com/Tallestxxl/M5Dial-Sonnenbatterie-afstandsbediening"),
        ("Installateurshandleiding", "GitHub: docs/gebruikershandleiding/installateurshandleiding", "https://github.com/Tallestxxl/M5Dial-Sonnenbatterie-afstandsbediening/blob/main/docs/gebruikershandleiding/M5Dial-Sonnenbatterie-installateurshandleiding-versie-1.1.pdf"),
        ("Officiële M5Dial-documentatie", "docs.m5stack.com/en/core/M5Dial", "https://docs.m5stack.com/en/core/M5Dial"),
        ("3D-behuizing", "printables.com/model/992288-m5stack-dial-case/files", "https://www.printables.com/model/992288-m5stack-dial-case/files"),
        ("Sonnen release notes", "sonnen.de/rln-sb", "https://www.sonnen.de/rln-sb"),
    ]
    for i, (title, display, url) in enumerate(sources):
        yy = source_y - i * 42
        c.setFillColor(white)
        c.setStrokeColor(LINE)
        c.roundRect(M, yy - 29, 355, 34, 5, fill=1, stroke=1)
        c.setFont("DV-Bold", 7.7)
        c.setFillColor(INK)
        c.drawString(M + 10, yy - 8, title)
        c.setFont("DV", 6.5)
        c.setFillColor(BLUE)
        c.drawString(M + 10, yy - 20, display)
        c.linkURL(url, (M, yy - 29, M + 355, yy + 5), relative=0)
    draw_qr(c, sources[0][2], W - M - 98, source_y - 78, 94)
    c.setFont("DV", 6.4)
    c.setFillColor(MUTED)
    c.drawCentredString(W - M - 51, source_y - 91, "QR: GitHub-repository")
    c.setFont("DV-Italic", 6.7)
    c.setFillColor(MUTED)
    c.drawString(M, 49, "Specificaties en software kunnen veranderen. Controleer bij twijfel de actuele documentatie van M5Stack, sonnen en de accufabrikant.")
    c.showPage()


def write_pdf(
    output: Path,
    *,
    title: str,
    subject: str,
    pages: list,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="manual-", suffix=".pdf", dir=output.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        c = canvas.Canvas(str(temporary), pagesize=A4, pageCompression=1, invariant=1)
        c.setTitle(title)
        c.setAuthor("M5Dial Sonnenbatterie project")
        c.setSubject(subject)
        c.setKeywords("M5Dial, Sonnenbatterie, afstandsbediening, handleiding, ESP32")
        for draw_page in pages:
            draw_page(c)
        c.save()
        if output.exists() and filecmp.cmp(temporary, output, shallow=False):
            temporary.unlink()
        else:
            os.replace(temporary, output)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    print(output)


def build() -> None:
    register_fonts()
    write_pdf(
        INSTALLER_OUT,
        title="M5Dial Sonnenbatterie-afstandsbediening - Installateurshandleiding",
        subject="Installatie, configuratie, test en onderhoud van de M5Dial Sonnenbatterie-afstandsbediening",
        pages=[
            installer_cover,
            installer_page_2,
            installer_page_3,
            installer_page_4,
            installer_page_5,
            installer_page_6,
            installer_page_7,
            installer_page_8,
        ],
    )
    write_pdf(
        USER_OUT,
        title="M5Dial Sonnenbatterie-afstandsbediening - Gebruikershandleiding",
        subject="Gebruikershandleiding voor de M5Dial Sonnenbatterie-afstandsbediening",
        pages=[
            cover,
            page_2,
            page_3,
            page_4,
            page_5,
            page_6,
            page_7,
            page_8,
            page_9,
            page_10,
            page_11,
            page_12,
            page_13,
            page_14,
            page_15,
            user_page_16,
        ],
    )


if __name__ == "__main__":
    build()
