import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QSettings, QTimer
from PySide6.QtWidgets import QApplication

from torchic.runtime import APP_DIR
from torchic.transcription import TranscriptionConfig
from torchic.ui.appearance import fallback_icon, stylesheet
from torchic.ui.main_window import MainWindow
from torchic.ui.settings_dialog import SettingsDialog
from torchic.ui.worker import Worker


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_directory = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
            QSettings.setPath(QSettings.Format.IniFormat, scope, cls.config_directory.name)
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(stylesheet())

    @classmethod
    def tearDownClass(cls):
        cls.config_directory.cleanup()

    def setUp(self):
        self.settings = QSettings("Torchic", "Torchic")
        self.settings.clear()
        self.settings.sync()

    def test_window_runs_event_loop_and_saves_transcript(self):
        window = MainWindow()
        try:
            window.show()
            self.assertEqual(window.windowTitle(), "Torchic")
            self.assertFalse(fallback_icon().isNull())
            with tempfile.TemporaryDirectory() as directory:
                audio = Path(directory) / "speech.wav"
                window.file_edit.setText(str(audio))
                window.on_finished("Hello Sagittarius.")
                self.assertEqual(audio.with_name("speech_plain.txt").read_text(), "Hello Sagittarius.")
                self.assertEqual(window.transcript.toPlainText(), "Hello Sagittarius.")
                self.assertEqual(window.status.text(), "Finished and saved")
            loop = QEventLoop()
            QTimer.singleShot(10, loop.quit)
            loop.exec()
        finally:
            window.close()

    def test_model_selection_and_custom_path_survive_settings(self):
        for model in ("large-v3-turbo", "C:/models/my-whisper"):
            with self.subTest(model=model):
                self.settings.setValue("transcription/local_model", model)
                dialog = SettingsDialog(self.settings, "session-test-key")
                try:
                    self.assertEqual(dialog.local_model.currentText(), model)
                    dialog.accept()
                    self.assertEqual(self.settings.value("transcription/local_model"), model)
                    self.assertEqual(dialog.session_api_key, "session-test-key")
                    self.assertFalse(any("api_key" in key for key in self.settings.allKeys()))
                finally:
                    dialog.close()

    def test_blank_model_uses_accuracy_default(self):
        dialog = SettingsDialog(self.settings, "")
        try:
            dialog.local_model.setCurrentText("  ")
            dialog.accept()
            self.assertEqual(self.settings.value("transcription/local_model"), "large-v3")
        finally:
            dialog.close()

    def test_window_uses_selected_model_in_label_and_configuration(self):
        self.settings.setValue("transcription/local_model", "medium")
        window = MainWindow()
        try:
            self.assertEqual(window.backend.itemText(0), "Local · medium")
            self.assertEqual(window.build_config().local_model, "medium")
            self.settings.setValue("transcription/local_model", "large-v3-turbo")
            window.update_backend_note()
            self.assertEqual(window.backend.itemText(0), "Local · large-v3-turbo")
            self.assertIn("large-v3-turbo", window.backend_note.text())
            window.language.setCurrentIndex(1)
            self.assertEqual(window.build_config().language, "")
        finally:
            window.close()

    def test_worker_passes_project_root_and_emits_results(self):
        worker = Worker("speech.wav", TranscriptionConfig())
        received = []
        worker.finished.connect(received.append)
        with patch("torchic.ui.worker.transcribe", return_value="Hello.") as transcribe:
            worker.run()
        self.assertEqual(received, ["Hello."])
        self.assertEqual(transcribe.call_args.args[2], APP_DIR)
        self.assertEqual(APP_DIR, Path(__file__).resolve().parent.parent)

    def test_worker_reports_errors_and_cancellation(self):
        for error, signal_name in ((RuntimeError("Bad audio"), "failed"), (InterruptedError(), "stopped")):
            with self.subTest(signal=signal_name):
                worker = Worker("speech.wav", TranscriptionConfig())
                events = []
                getattr(worker, signal_name).connect(lambda *args: events.append(args))
                with patch("torchic.ui.worker.transcribe", side_effect=error):
                    worker.run()
                self.assertEqual(len(events), 1)
                if signal_name == "failed":
                    self.assertIn("Bad audio", events[0][0])


if __name__ == "__main__":
    unittest.main()
