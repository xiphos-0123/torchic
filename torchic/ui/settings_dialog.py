from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from ..runtime import app_data_dir
from ..transcription.config import DEFAULT_LOCAL_MODEL, DEFAULT_OPENAI_MODEL, LOCAL_MODEL_HINTS


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

        self.local_model = QComboBox()
        self.local_model.setEditable(True)
        self.local_model.addItems(list(LOCAL_MODEL_HINTS))
        self.local_model.setCurrentText(settings.value("transcription/local_model", DEFAULT_LOCAL_MODEL, str))
        form.addRow("Local model", self.local_model)

        self.model_hint = QLabel()
        self.model_hint.setWordWrap(True)
        self.model_hint.setProperty("muted", True)
        self.local_model.currentTextChanged.connect(self.update_model_hint)
        self.update_model_hint(self.local_model.currentText())
        form.addRow(self.model_hint)

        self.device = QComboBox()
        self.device.addItems(["Auto", "CUDA", "CPU"])
        self.device.setCurrentText(settings.value("transcription/device", "Auto", str))
        form.addRow("Local device", self.device)

        self.compute = QComboBox()
        self.compute.addItems(["Auto", "float16", "int8_float16", "int8"])
        self.compute.setCurrentText(settings.value("transcription/compute_type", "Auto", str))
        form.addRow("Compute type", self.compute)

        compute_hint = QLabel(
            "Auto uses int8_float16 on NVIDIA CUDA and int8 on CPU. "
            "Choose float16 on a compatible CUDA GPU to avoid 8-bit weight quantization; "
            "it uses more VRAM and is not guaranteed to improve every transcript."
        )
        compute_hint.setWordWrap(True)
        compute_hint.setProperty("muted", True)
        form.addRow(compute_hint)

        self.openai_model = QLineEdit(settings.value("transcription/openai_model", DEFAULT_OPENAI_MODEL, str))
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

    def update_model_hint(self, model: str):
        self.model_hint.setText(LOCAL_MODEL_HINTS.get(
            model.strip() or DEFAULT_LOCAL_MODEL,
            "Custom Hugging Face model ID or local folder; must contain a CTranslate2 Whisper model.",
        ))

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
        self.settings.setValue("transcription/local_model", self.local_model.currentText().strip() or DEFAULT_LOCAL_MODEL)
        self.settings.setValue("transcription/device", self.device.currentText())
        self.settings.setValue("transcription/compute_type", self.compute.currentText())
        self.settings.setValue("transcription/openai_model", self.openai_model.text().strip() or DEFAULT_OPENAI_MODEL)
        self.settings.sync()
        self.session_api_key = self.api_key.text().strip()
        super().accept()
