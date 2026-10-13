from __future__ import annotations

# Torchic self-relaunches through the project venv so the .pyw itself is the launcher.
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
if VENV_PYTHONW.exists() and Path(sys.executable).resolve() != VENV_PYTHONW.resolve():
    os.execv(str(VENV_PYTHONW), [str(VENV_PYTHONW), str(Path(__file__).resolve()), *sys.argv[1:]])

import ctypes
import shutil
import traceback

if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Torchic.App")
    except Exception:
        pass

from PySide6.QtCore import QObject, QSettings, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine import TranscriptionConfig, transcribe


APP_NAME = "Torchic"
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


def app_data_dir() -> Path:
    path = APP_DIR / ".torchic"
    path.mkdir(exist_ok=True)
    return path


def load_app_icon(settings: QSettings) -> QIcon:
    custom = settings.value("appearance/custom_icon", "", str)
    if custom and Path(custom).is_file():
        icon = QIcon(custom)
        if not icon.isNull():
            return icon
    return fallback_icon()


class Worker(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, audio_path: str, config: TranscriptionConfig):
        super().__init__()
        self.audio_path = audio_path
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            text = transcribe(
                self.audio_path,
                self.config,
                APP_DIR,
                lambda value, message: self.progress.emit(value, message),
                lambda: self._cancelled,
            )
        except InterruptedError:
            self.stopped.emit()
            return
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(text)


class SettingsDialog(QDialog):
    icon_changed = Signal()

    def __init__(self, settings: QSettings, session_api_key: str, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.session_api_key = session_api_key
        self.setWindowTitle("Torchic Settings")
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.local_model = QLineEdit(settings.value("transcription/local_model", "large-v3", str))
        self.local_model.setPlaceholderText("large-v3")
        form.addRow("Local model", self.local_model)

        self.device = QComboBox()
        self.device.addItems(["Auto", "CUDA", "CPU"])
        self.device.setCurrentText(settings.value("transcription/device", "Auto", str))
        form.addRow("Local device", self.device)

        self.compute = QComboBox()
        self.compute.addItems(["Auto", "float16", "int8_float16", "int8"])
        self.compute.setCurrentText(settings.value("transcription/compute_type", "Auto", str))
        form.addRow("Compute type", self.compute)

        self.openai_model = QLineEdit(settings.value("transcription/openai_model", "gpt-transcribe", str))
        form.addRow("OpenAI model", self.openai_model)

        self.api_key = QLineEdit(session_api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Session only; or use OPENAI_API_KEY")
        form.addRow("OpenAI API key", self.api_key)

        layout.addLayout(form)

        icon_row = QHBoxLayout()
        self.icon_label = QLabel("Fallback Torchic icon")
        custom = settings.value("appearance/custom_icon", "", str)
        if custom and Path(custom).is_file():
            self.icon_label.setText(Path(custom).name)
        choose_icon = QPushButton("Choose icon image")
        reset_icon = QPushButton("Use fallback")
        choose_icon.clicked.connect(self.choose_icon)
        reset_icon.clicked.connect(self.reset_icon)
        icon_row.addWidget(self.icon_label, 1)
        icon_row.addWidget(choose_icon)
        icon_row.addWidget(reset_icon)
        layout.addLayout(icon_row)

        note = QLabel(
            "Custom icons are runtime icons only. Torchic does not modify .pyw associations, "
            "Explorer file icons, System32, or the Windows icon cache."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Torchic icon image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower() or ".png"
        target = app_data_dir() / f"custom_icon{suffix}"
        for old in app_data_dir().glob("custom_icon.*"):
            try:
                old.unlink()
            except OSError:
                pass
        shutil.copy2(path, target)
        self.settings.setValue("appearance/custom_icon", str(target))
        self.icon_label.setText(target.name)
        self.icon_changed.emit()

    def reset_icon(self):
        self.settings.remove("appearance/custom_icon")
        for old in app_data_dir().glob("custom_icon.*"):
            try:
                old.unlink()
            except OSError:
                pass
        self.icon_label.setText("Fallback Torchic icon")
        self.icon_changed.emit()

    def accept(self):
        self.settings.setValue("transcription/local_model", self.local_model.text().strip() or "large-v3")
        self.settings.setValue("transcription/device", self.device.currentText())
        self.settings.setValue("transcription/compute_type", self.compute.currentText())
        self.settings.setValue("transcription/openai_model", self.openai_model.text().strip() or "gpt-transcribe")
        self.settings.sync()
        self.session_api_key = self.api_key.text().strip()
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Torchic", "Torchic")
        self.session_api_key = ""
        self.thread: QThread | None = None
        self.worker: Worker | None = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(650, 440)
        self.resize(1050, 690)
        self.apply_icon()
        self.build_ui()
        self.restore_ui_state()

    def apply_icon(self):
        icon = load_app_icon(self.settings)
        QApplication.instance().setWindowIcon(icon)
        self.setWindowIcon(icon)

    def build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Torchic")
        title.setObjectName("title")
        subtitle = QLabel("Precise audio transcription")
        subtitle.setProperty("muted", True)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)
        header.addWidget(settings_button)
        root_layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)

        controls = QFrame()
        controls.setObjectName("panel")
        controls.setMinimumWidth(255)
        controls.setMaximumWidth(390)
        left = QVBoxLayout(controls)
        left.setContentsMargins(14, 14, 14, 14)
        left.setSpacing(10)

        file_label = QLabel("Audio")
        file_label.setObjectName("section")
        left.addWidget(file_label)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Choose an audio file")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_audio)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse)
        left.addLayout(file_row)

        backend_label = QLabel("Engine")
        backend_label.setObjectName("section")
        left.addWidget(backend_label)
        self.backend = QComboBox()
        self.backend.addItem("Local · Whisper large-v3", "local")
        self.backend.addItem("OpenAI · GPT Transcribe", "openai")
        self.backend.currentIndexChanged.connect(self.update_backend_note)
        left.addWidget(self.backend)

        self.backend_note = QLabel()
        self.backend_note.setWordWrap(True)
        self.backend_note.setProperty("muted", True)
        left.addWidget(self.backend_note)

        lang_row = QHBoxLayout()
        lang_label = QLabel("Language")
        self.language = QComboBox()
        self.language.setEditable(True)
        self.language.addItem("English", "en")
        self.language.addItem("Auto detect", "")
        self.language.setCurrentIndex(0)
        lang_row.addWidget(lang_label)
        lang_row.addStretch()
        lang_row.addWidget(self.language)
        left.addLayout(lang_row)

        self.timestamps = QCheckBox("Local timestamps")
        self.timestamps.setChecked(False)
        left.addWidget(self.timestamps)

        vocab_label = QLabel("Vocabulary / names")
        vocab_label.setObjectName("section")
        left.addWidget(vocab_label)
        self.vocabulary = QTextEdit()
        self.vocabulary.setAcceptRichText(False)
        self.vocabulary.setPlaceholderText(
            "A0, B1, Peristyle, Sagittarius, Echelon…\n\nNames and terms only — no transcription instructions."
        )
        self.vocabulary.setMinimumHeight(110)
        self.vocabulary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left.addWidget(self.vocabulary, 1)

        self.transcribe_button = QPushButton("Transcribe")
        self.transcribe_button.setObjectName("primary")
        self.transcribe_button.clicked.connect(self.start_or_cancel)
        left.addWidget(self.transcribe_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        left.addWidget(self.progress)

        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        self.status.setProperty("muted", True)
        left.addWidget(self.status)

        splitter.addWidget(controls)

        output = QFrame()
        output.setObjectName("panel")
        right = QVBoxLayout(output)
        right.setContentsMargins(14, 14, 14, 14)
        right.setSpacing(10)

        out_header = QHBoxLayout()
        out_title = QLabel("Transcript")
        out_title.setObjectName("section")
        out_header.addWidget(out_title)
        out_header.addStretch()
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_text)
        save_button = QPushButton("Save as")
        save_button.clicked.connect(self.save_as)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_text)
        out_header.addWidget(copy_button)
        out_header.addWidget(save_button)
        out_header.addWidget(clear_button)
        right.addLayout(out_header)

        self.transcript = QTextEdit()
        self.transcript.setAcceptRichText(False)
        self.transcript.setPlaceholderText("The transcript will appear here.")
        right.addWidget(self.transcript, 1)

        self.saved_path = QLabel("")
        self.saved_path.setProperty("muted", True)
        self.saved_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right.addWidget(self.saved_path)

        splitter.addWidget(output)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([315, 725])
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(root)
        self.update_backend_note()

    def restore_ui_state(self):
        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.file_edit.setText(self.settings.value("session/last_audio", "", str))
        self.vocabulary.setPlainText(self.settings.value("transcription/vocabulary", "", str))
        backend = self.settings.value("transcription/backend", "local", str)
        idx = self.backend.findData(backend)
        if idx >= 0:
            self.backend.setCurrentIndex(idx)
        self.timestamps.setChecked(self.settings.value("transcription/timestamps", False, bool))

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("session/last_audio", self.file_edit.text().strip())
        self.settings.setValue("transcription/vocabulary", self.vocabulary.toPlainText().strip())
        self.settings.setValue("transcription/backend", self.backend.currentData())
        self.settings.setValue("transcription/timestamps", self.timestamps.isChecked())
        self.settings.sync()
        if self.worker:
            self.worker.cancel()
        super().closeEvent(event)

    def update_backend_note(self):
        if self.backend.currentData() == "openai":
            self.backend_note.setText("Highest-quality cloud option; requires an OpenAI API key and uses paid API transcription.")
            self.timestamps.setEnabled(False)
        else:
            self.backend_note.setText("Free/local. Defaults to large-v3 with VAD and hotword guidance; CUDA is used automatically when available.")
            self.timestamps.setEnabled(True)

    def choose_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio",
            self.file_edit.text().strip() or str(Path.home()),
            "Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.oga *.aac *.mp4 *.mpeg *.mpga *.webm);;All files (*.*)",
        )
        if path:
            self.file_edit.setText(path)
            self.saved_path.clear()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self.session_api_key, self)
        dialog.icon_changed.connect(self.apply_icon)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session_api_key = dialog.session_api_key
            self.apply_icon()

    def language_code(self) -> str:
        data = self.language.currentData()
        if data is not None and self.language.currentText() in {"English", "Auto detect"}:
            return str(data)
        text = self.language.currentText().strip()
        return text if len(text) <= 8 else "en"

    def build_config(self) -> TranscriptionConfig:
        return TranscriptionConfig(
            backend=str(self.backend.currentData()),
            language=self.language_code(),
            vocabulary=self.vocabulary.toPlainText().strip(),
            local_model=self.settings.value("transcription/local_model", "large-v3", str),
            device=self.settings.value("transcription/device", "Auto", str).lower(),
            compute_type=self.settings.value("transcription/compute_type", "Auto", str).lower(),
            openai_model=self.settings.value("transcription/openai_model", "gpt-transcribe", str),
            openai_api_key=self.session_api_key,
            timestamps=self.timestamps.isChecked() and self.backend.currentData() == "local",
        )

    def start_or_cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("Stopping after the current segment…")
            self.transcribe_button.setEnabled(False)
            return

        audio = Path(self.file_edit.text().strip())
        if not audio.is_file():
            QMessageBox.warning(self, APP_NAME, "Choose a valid audio file first.")
            return

        config = self.build_config()
        if config.backend == "openai" and not (config.openai_api_key or os.environ.get("OPENAI_API_KEY")):
            QMessageBox.information(
                self,
                APP_NAME,
                "OpenAI mode needs an API key. Open Settings and enter one for this session, or set OPENAI_API_KEY in Windows.",
            )
            return

        self.transcript.clear()
        self.saved_path.clear()
        self.progress.setValue(0)
        self.status.setText("Starting…")
        self.transcribe_button.setText("Cancel")

        self.thread = QThread(self)
        self.worker = Worker(str(audio), config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.stopped.connect(self.on_stopped)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.stopped.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup_worker)
        self.thread.start()

    def on_progress(self, value: int, message: str):
        self.progress.setValue(value)
        self.status.setText(message)

    def default_output_path(self) -> Path:
        audio = Path(self.file_edit.text().strip())
        return audio.with_name(f"{audio.stem}_plain.txt")

    def on_finished(self, text: str):
        self.transcript.setPlainText(text)
        output = self.default_output_path()
        try:
            output.write_text(text, encoding="utf-8")
            self.saved_path.setText(f"Saved: {output}")
            self.status.setText("Finished and saved")
        except OSError as exc:
            self.saved_path.setText("")
            self.status.setText("Finished; automatic save failed")
            QMessageBox.warning(self, APP_NAME, f"Transcription finished, but Torchic could not save the file automatically.\n\n{exc}")
        self.progress.setValue(100)

    def on_failed(self, details: str):
        self.progress.setValue(0)
        self.status.setText("Transcription failed")
        short = details.strip().splitlines()[-1] if details.strip() else "Unknown error"
        QMessageBox.critical(self, APP_NAME, f"{short}\n\nFull technical details were copied to the transcript pane.")
        self.transcript.setPlainText(details)

    def on_stopped(self):
        self.progress.setValue(0)
        self.status.setText("Cancelled")

    def cleanup_worker(self):
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None
        self.transcribe_button.setText("Transcribe")
        self.transcribe_button.setEnabled(True)

    def copy_text(self):
        text = self.transcript.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.status.setText("Transcript copied")

    def save_as(self):
        if not self.transcript.toPlainText().strip():
            return
        default = str(self.default_output_path()) if self.file_edit.text().strip() else "transcript.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Save transcript", default, "Text (*.txt)")
        if path:
            try:
                Path(path).write_text(self.transcript.toPlainText(), encoding="utf-8")
                self.saved_path.setText(f"Saved: {path}")
                self.status.setText("Saved")
            except OSError as exc:
                QMessageBox.warning(self, APP_NAME, str(exc))

    def clear_text(self):
        self.transcript.clear()
        self.saved_path.clear()


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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setStyleSheet(stylesheet())
    settings = QSettings("Torchic", "Torchic")
    app.setWindowIcon(load_app_icon(settings))
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
