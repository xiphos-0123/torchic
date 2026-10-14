import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import engine
from torchic import transcription
from torchic.transcription.common import _format_timestamp, _vocabulary_items
from torchic.transcription.config import TranscriptionConfig
from torchic.transcription.local import _choose_local_runtime, transcribe_local
from torchic.transcription.openai import transcribe_openai


class TranscriptionTests(unittest.TestCase):
    def test_installed_audio_decoder_reads_a_real_wav(self):
        from faster_whisper.audio import decode_audio

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "speech.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(b"\x00\x00" * 1600)
            decoded = decode_audio(str(audio))
        self.assertEqual(len(decoded), 1600)
        self.assertTrue((decoded == 0).all())

    def test_legacy_engine_exports_use_the_package(self):
        self.assertIs(engine.transcribe, transcription.transcribe)
        self.assertIs(engine.TranscriptionConfig, TranscriptionConfig)

    def test_vocabulary_preserves_names_and_removes_duplicates(self):
        self.assertEqual(
            _vocabulary_items("  Sagittarius ; A0\nPeristyle, sagittarius, A0  "),
            ["Sagittarius", "A0", "Peristyle"],
        )

    def test_timestamp_formats_hours_and_clamps_negative_time(self):
        self.assertEqual(_format_timestamp(3661.9), "01:01:01")
        self.assertEqual(_format_timestamp(-5), "00:00:00")

    def test_missing_audio_fails_before_selecting_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                transcription.transcribe(
                    Path(directory) / "missing.wav", TranscriptionConfig(),
                    directory, lambda *_: None, lambda: False,
                )

    def test_dispatches_to_the_selected_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "sample.wav"
            audio.touch()
            for backend in ("local", "openai"):
                with self.subTest(backend=backend):
                    config = TranscriptionConfig(backend=backend)
                    with patch(f"torchic.transcription.transcribe_{backend}", return_value="Words") as selected:
                        result = transcription.transcribe(audio, config, directory, lambda *_: None, lambda: False)
                        self.assertEqual(result, "Words")
                        self.assertEqual(selected.call_args.args[:2], (audio, config))

    def test_auto_runtime_chooses_cpu_or_cuda(self):
        with patch("ctranslate2.get_cuda_device_count", return_value=0):
            self.assertEqual(_choose_local_runtime("Auto", "Auto"), ("cpu", "int8"))
        with patch("ctranslate2.get_cuda_device_count", return_value=1):
            self.assertEqual(_choose_local_runtime("Auto", "Auto"), ("cuda", "int8_float16"))
            self.assertEqual(_choose_local_runtime("CUDA", "float16"), ("cuda", "float16"))

    def test_local_engine_preserves_decoding_vocabulary_and_timestamps(self):
        captured = {}

        class FakeWhisperModel:
            def __init__(self, model, device, compute_type):
                captured["runtime"] = (model, device, compute_type)

            def transcribe(self, path, hotwords=None, hallucination_silence_threshold=None, **kwargs):
                captured.update(kwargs, path=path, hotwords=hotwords)
                return iter([
                    SimpleNamespace(text="  Hello   Sagittarius.  ", start=1.2, end=3),
                    SimpleNamespace(text="  ", start=3, end=4),
                ]), SimpleNamespace(duration=4)

        progress = []
        config = TranscriptionConfig(device="cpu", timestamps=True, vocabulary="Sagittarius, A0")
        with patch("faster_whisper.WhisperModel", FakeWhisperModel):
            result = transcribe_local(
                Path("speech.wav"), config, Path("/tmp/no-torchic-runtime"),
                lambda *event: progress.append(event), lambda: False,
            )
        self.assertEqual(result, "[00:00:01] Hello Sagittarius.")
        self.assertEqual(captured["runtime"], ("large-v3", "cpu", "int8"))
        self.assertEqual(captured["hotwords"], "Sagittarius, A0")
        self.assertEqual(captured["beam_size"], 8)
        self.assertTrue(captured["vad_filter"])
        self.assertFalse(captured["condition_on_previous_text"])
        self.assertEqual(progress[-1], (100, "Finished"))

    def test_auto_cuda_load_failure_retries_cpu(self):
        model = MagicMock()
        model.transcribe.return_value = (iter([]), SimpleNamespace(duration=0))
        with patch("ctranslate2.get_cuda_device_count", return_value=1):
            with patch("faster_whisper.WhisperModel", side_effect=[RuntimeError("CUDA unavailable"), model]) as load:
                result = transcribe_local(
                    Path("speech.wav"), TranscriptionConfig(), Path("/tmp/no-torchic-runtime"),
                    lambda *_: None, lambda: False,
                )
        self.assertEqual(result, "")
        self.assertEqual([call.kwargs["device"] for call in load.call_args_list], ["cuda", "cpu"])

    def test_openai_engine_preserves_keywords_and_response(self):
        client = MagicMock()
        client.audio.transcriptions.create.return_value = SimpleNamespace(text="  Hello Sagittarius.  ")
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "speech.wav"
            audio.write_bytes(b"test fixture")
            with patch("openai.OpenAI", return_value=client):
                result = transcribe_openai(
                    audio, TranscriptionConfig(openai_api_key="test-key", vocabulary="Sagittarius"),
                    lambda *_: None, lambda: False,
                )
        self.assertEqual(result, "Hello Sagittarius.")
        request = client.audio.transcriptions.create.call_args.kwargs
        self.assertEqual(request["model"], "gpt-transcribe")
        self.assertEqual(request["keywords"], ["Sagittarius"])
        self.assertEqual(request["language"], "en")

    def test_openai_cancellation_prevents_upload(self):
        with patch("openai.OpenAI") as client:
            with self.assertRaises(InterruptedError):
                transcribe_openai(Path("speech.wav"), TranscriptionConfig(), lambda *_: None, lambda: True)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
