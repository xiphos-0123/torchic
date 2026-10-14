TORCHIC
=======

Windows desktop application for converting speech recordings to written text.

FILES
-----
Torchic.pyw       Small double-click launcher; activates the Windows venv.
torchic/app.py    Qt application startup.
torchic/runtime.py
                 Project paths, custom icon directory, portable CUDA support.
torchic/ui/      Main window, settings dialog, appearance, background worker.
torchic/transcription/
                 Configuration, Local/OpenAI engines, shared text utilities.
engine.py         Compatibility imports for existing engine users.
tests/           Transcription and headless UI regression checks.
requirements.txt Python packages.
install.bat       The only setup BAT file.
README.txt        This file.

FIRST RUN
---------
1. Run install.bat once.
2. Double-click Torchic.pyw.
3. Choose an audio file.
4. Add fantasy names / unusual vocabulary if useful.
5. Choose Local or OpenAI transcription and click Transcribe.

Torchic automatically saves completed transcripts beside the source audio as:
    <audio name>_plain.txt

LOCAL ACCURATE MODE
-------------------
Default model: Whisper large-v3 through faster-whisper.

Settings > Local model offers these choices:
- large-v3: full multilingual model; the accuracy-first default.
- large-v3-turbo: faster multilingual model with fewer decoder layers.
- distil-large-v3: faster distilled model for English recordings.
- medium or small: lower memory demand for smaller GPUs or CPU use.

You can also enter a Hugging Face model ID or local folder containing a
CTranslate2-converted Whisper model. Existing model settings are preserved.
The Engine label always displays the selected local model.

The default was already large-v3. Turbo and distilled variants prioritize
speed; their accuracy depends on the recording and language. A larger download
or higher memory use alone does not establish a better transcription model.

For an NVIDIA GPU with enough free VRAM, CUDA + float16 avoids 8-bit weight
quantization. Auto uses int8_float16 on CUDA or int8 on CPU to reduce memory use.
float16 needs more VRAM and is not guaranteed to improve every transcript.
Choose based on your GPU/VRAM and recording; CPU large-v3 may run slowly.

Torchic uses:
- beam search
- voice activity detection (VAD)
- repetition safeguards
- condition_on_previous_text disabled for long-session robustness
- vocabulary as hotwords where supported

The first local transcription downloads the model automatically.

GPU
---
CUDA is used automatically when available. Current faster-whisper/CTranslate2
GPU builds require CUDA 12 cuBLAS and cuDNN 9.

Torchic also supports the existing portable approach: if a folder named
"gpu_runtime" is placed beside Torchic.pyw, Torchic adds its runtime/bin/lib
folders to the process DLL search path. Nothing is copied to System32.

If CUDA cannot be used while Device is set to Auto, Torchic falls back to CPU.

OPENAI MODE
-----------
OpenAI mode defaults to gpt-transcribe and uses keyword hints from the same
Vocabulary / names box. It requires a paid OpenAI API key.

The key entered in Settings is kept only for the current Torchic process. It is
not written to Torchic settings. You can instead define OPENAI_API_KEY in
Windows.

ICON
----
Torchic generates a fallback runtime icon in code using the Torchic palette.
Settings > Choose icon image copies your chosen image into .torchic and applies
it as the Qt application/window/taskbar runtime icon.

Torchic intentionally does not create .ico files, change .pyw associations,
modify Explorer icons, write to System32, or use Windows icon-cache tricks.

WINDOW
------
Torchic uses an ordinary resizable Windows window and works with Windows Snap / split-screen layouts.

DEVELOPMENT
-----------
Windows installation and double-click startup are unchanged. To launch from
a terminal after install.bat:
    .venv\Scripts\python.exe -m torchic

To run the regression checks on Windows:
    .venv\Scripts\python.exe -m unittest discover -s tests -v

For Linux development, create a Python 3.10+ environment and install
requirements.txt, then run:
    python -m unittest discover -s tests -v

The UI checks use Qt's offscreen platform and isolated temporary settings.
Engine checks use controlled model/API doubles to check request parameters,
formatting, cancellation, and CPU fallback without model downloads or charges.
One decoder check also opens a real WAV file to catch incompatible audio
dependencies; PyAV is limited below version 19 for faster-whisper compatibility.
They do not measure real transcription accuracy or verify Windows integration.

For a headless application session on Linux:
    QT_QPA_PLATFORM=offscreen python -m torchic

Runtime icons, the project venv, portable CUDA libraries and Python caches are
ignored by Git. Completed transcripts are saved beside the input recording.
