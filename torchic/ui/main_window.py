from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSizePolicy, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from ..transcription import TranscriptionConfig
from ..transcription.config import APP_NAME, DEFAULT_LOCAL_MODEL, DEFAULT_OPENAI_MODEL
from .appearance import load_app_icon
from .settings_dialog import SettingsDialog
from .worker import Worker


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
        self.backend.addItem("Local", "local")
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
        local_model = self.settings.value("transcription/local_model", DEFAULT_LOCAL_MODEL, str)
        self.backend.setItemText(self.backend.findData("local"), f"Local · {local_model}")
        if self.backend.currentData() == "openai":
            self.backend_note.setText("Cloud transcription; requires an OpenAI API key and uses paid API transcription.")
            self.timestamps.setEnabled(False)
        else:
            self.backend_note.setText(f"Free/local. Uses {local_model} with VAD and vocabulary guidance; CUDA is used automatically when available.")
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
            self.update_backend_note()

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
            local_model=self.settings.value("transcription/local_model", DEFAULT_LOCAL_MODEL, str),
            device=self.settings.value("transcription/device", "Auto", str).lower(),
            compute_type=self.settings.value("transcription/compute_type", "Auto", str).lower(),
            openai_model=self.settings.value("transcription/openai_model", DEFAULT_OPENAI_MODEL, str),
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
