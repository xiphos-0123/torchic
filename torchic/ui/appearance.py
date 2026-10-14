from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

PALETTE = {
    "orange": "#ff7b39",
    "amber": "#ffa439",
    "gold": "#ffc552",
    "cream": "#ffde73",
    "pale": "#ffde94",
    "ink": "#2d211b",
    "muted": "#77655b",
    "surface": "#fffaf3",
    "line": "#efd8c7",
}


def fallback_icon(size: int = 256) -> QIcon:
    """Runtime-only Torchic mark: a T with a small chick/crest motif."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    rect = pix.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(PALETTE["amber"]))
    p.drawRoundedRect(rect, size * 0.21, size * 0.21)

    # Small three-point crest, deliberately simple rather than a character drawing.
    crest = QPainterPath()
    crest.moveTo(size * 0.31, size * 0.34)
    crest.lineTo(size * 0.40, size * 0.17)
    crest.lineTo(size * 0.49, size * 0.32)
    crest.lineTo(size * 0.60, size * 0.16)
    crest.lineTo(size * 0.68, size * 0.35)
    crest.closeSubpath()
    p.setBrush(QColor(PALETTE["orange"]))
    p.drawPath(crest)

    pen = QPen(QColor(PALETTE["ink"]), size * 0.085, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(int(size * 0.31), int(size * 0.43), int(size * 0.69), int(size * 0.43))
    p.drawLine(int(size * 0.50), int(size * 0.43), int(size * 0.50), int(size * 0.76))

    # tiny beak-like accent
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(PALETTE["pale"]))
    beak = QPainterPath()
    beak.moveTo(size * 0.50, size * 0.62)
    beak.lineTo(size * 0.61, size * 0.67)
    beak.lineTo(size * 0.50, size * 0.71)
    beak.closeSubpath()
    p.drawPath(beak)
    p.end()
    return QIcon(pix)


def load_app_icon(settings: QSettings) -> QIcon:
    custom = settings.value("appearance/custom_icon", "", str)
    if custom and Path(custom).is_file():
        icon = QIcon(custom)
        if not icon.isNull():
            return icon
    return fallback_icon()


def stylesheet() -> str:
    return f"""
    QWidget {{
        background: {PALETTE['surface']};
        color: {PALETTE['ink']};
        font-family: "Segoe UI";
        font-size: 10pt;
    }}
    QLabel#title {{ font-size: 20pt; font-weight: 700; color: {PALETTE['orange']}; }}
    QLabel#section {{ font-weight: 650; }}
    QLabel[muted="true"] {{ color: {PALETTE['muted']}; font-size: 9pt; }}
    QFrame#panel {{
        background: #ffffff;
        border: 1px solid {PALETTE['line']};
        border-radius: 10px;
    }}
    QLineEdit, QTextEdit, QComboBox {{
        background: #ffffff;
        border: 1px solid {PALETTE['line']};
        border-radius: 7px;
        padding: 7px;
        selection-background-color: {PALETTE['gold']};
        selection-color: {PALETTE['ink']};
    }}
    QTextEdit:focus, QLineEdit:focus, QComboBox:focus {{ border: 1px solid {PALETTE['amber']}; }}
    QPushButton {{
        background: {PALETTE['pale']};
        border: 1px solid {PALETTE['gold']};
        border-radius: 7px;
        padding: 7px 11px;
    }}
    QPushButton:hover {{ background: {PALETTE['cream']}; }}
    QPushButton:pressed {{ background: {PALETTE['gold']}; }}
    QPushButton#primary {{
        background: {PALETTE['orange']};
        color: #ffffff;
        border: none;
        font-weight: 700;
        padding: 9px 12px;
    }}
    QPushButton#primary:hover {{ background: {PALETTE['amber']}; color: {PALETTE['ink']}; }}
    QProgressBar {{
        background: #f8eadf;
        border: none;
        border-radius: 4px;
        min-height: 7px;
        max-height: 7px;
    }}
    QProgressBar::chunk {{ background: {PALETTE['orange']}; border-radius: 4px; }}
    QSplitter::handle {{ background: transparent; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    """
