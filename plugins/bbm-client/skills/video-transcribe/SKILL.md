---
name: video-transcribe
description: "Transcribe a local audio/video recording using an available local Whisper engine; produces a labeled machine transcript without uploading media."
---

Resolve the selected workspace using `bbm-client.json` or explicit `BBM_CLIENT_CONFIG`, following [workspace-start](../workspace-start/SKILL.md). Read its map and boundaries before saving. Resolve paths from that config, never from the plugin cache or another workspace. If no workspace is configured, conversation-only work can continue; use workspace-setup before filing. Preserve existing files and keep private information in its selected scope.

Inspect the supplied file and the available OS/runtime. Preserve the original. Check for an installed local Whisper-compatible engine and ffmpeg; do not assume Apple Silicon, a particular Python environment or an existing model. Tell the owner the missing prerequisites and download size when known before installing tools or downloading model weights. Cloud transcription is a separate explicit opt-in, never a fallback.

For an installed OpenAI Whisper CLI, inspect `whisper --help` and use its supported options. A typical command is:

```
whisper "INPUT_FILE" --model base --output_format all --output_dir "NEW_OUTPUT_DIRECTORY"
```

Use a fresh output directory chosen from the workspace's local media/scratch area, outside vault Git. Model choice trades speed for accuracy; preserve the owner's selection. Check the model is cached or obtain approval for its initial download. On supported Apple Silicon, an already installed mlx-whisper engine is also suitable; inspect that installation's documented interface rather than guessing a command. Windows can use an installed Whisper CLI without requiring MLX. No engine or model is bundled with this skill.

Verify process completion and nonempty text. Inspect the beginning/end and suspicious repeated phrases, music or silence segments. If output is implausible, flag it rather than inventing speech. Extract text and available timestamps from the engine's actual output into a new Markdown file, preserving wording rather than summarizing. Label engine, model, language, date and **machine transcript, not proofread**. Local Whisper does not identify speakers: never infer named speakers from turn-taking. Keep timestamps only where the engine supplies them.

Return the transcript path and limitations. If meeting ingestion was requested, pass the transcript to meeting-ingest/source-capture. Analysis and action extraction are separate from the verbatim record. Never overwrite an existing transcript or delete recordings without explicit authorization. Do not upload audio, read unrelated credentials or enable background capture.
