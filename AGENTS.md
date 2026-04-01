# Project Notes

## Qwen Voice Cloning

- Qwen voice cloning uses `Qwen/Qwen3-TTS-12Hz-0.6B-Base` and the `generate_voice_clone(...)` API from `qwen-tts`.
- The built-in named speakers use `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` and `generate_custom_voice(...)`.
- This repo keeps both checkpoints:
  - `runtime/models/qwen3_0_6b` for built-in named voices
  - `runtime/models/qwen3_0_6b_base` for saved voice cloning
- Saved voices are persisted under `runtime/data/voices/<sample_id>/` as:
  - `reference.wav`
  - `metadata.json`
- The saved metadata stores the exact transcript alongside the recording because Qwen cloning quality depends on `ref_text` matching the reference audio.

## Voice Sample Guidance

- Prefer a clean single-speaker clip in a quiet room.
- Qwen shows cloning from a short reference clip; for this app, 5-15 seconds of clean speech is a safer practical target than trying to use the shortest possible sample.
- The transcript should match the recording exactly.
- Natural continuous speech is better than filler words, long pauses, overlapping speakers, music, or very noisy audio.
