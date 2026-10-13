TORCHIC
=======

Minimal Windows transcription application.

FILES
-----
Torchic.pyw       Main application and UI.
engine.py         Local/OpenAI transcription engines.
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
