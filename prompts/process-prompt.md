# mvideo publishing pipeline prompt

You are preparing a recording for publishing with the existing `mvideo`
pipeline.

## Goals

- Apply requested start/end trimming.
- Normalize speech audio to the requested target level.
- Optionally mix looped background music.
- Generate an SRT through DashScope ASR.
- Burn generated subtitles into the final video.
- Produce and verify the requested publishing artifact without replacing the
  existing CLI with custom scripts.

## Input contract

- Required: existing input video and a distinct output video path.
- Optional trim values: seconds or `HH:MM:SS`; both default to `0`.
- Optional target volume: defaults to `-16.0` dB.
- Optional background music: existing audio file; music volume defaults to
  `0.3`.
- Language hints default to `zh,en`.
- This end-to-end workflow uses `--burn-srt`, which implies SRT generation.
- Transcription requires the DashScope and OSS environment variables documented
  in `README.md`.

## Running the CLI

```bash
uv run main.py process <input-video> <output-video> \
  --start-trim <start> \
  --end-trim <end> \
  --target-volume -16 \
  --background-music <music-file> \
  --music-volume 0.3 \
  --srt \
  --burn-srt \
  --language zh,en
```

Omit trim and music options the user did not request. Keep `--srt --burn-srt`
for this workflow because the current `process` command writes its final output
in the subtitle-burning path. For a workflow without burned subtitles, use the
stage prompts in `prompts/README.md`. Use `--no-gpu` when AMD VAAPI is
unavailable.

## Instructions

1. Resolve and validate all input paths. The output path must not be the input
   path.
2. Confirm trim values are non-negative and their sum is shorter than the
   probed input duration.
3. If background music was requested but is missing, stop rather than silently
   publishing without it.
4. Before transcription, check that required credential variables are present
   without exposing their values.
5. Before GPU subtitle burning, verify `/dev/dri/renderD128` and FFmpeg's
   `h264_vaapi` encoder; otherwise add `--no-gpu`.
6. Run the existing `process` command once with the resolved options.
7. Verify every requested artifact exists and is non-empty. Probe the output
   video for playable video and audio streams. If SRT was requested, validate
   its numbering and timestamp syntax.
8. Report the absolute output path, SRT path when generated, and effective
   processing settings.

## Output contract

- Final video: the exact requested output path.
- Generated subtitles: `<output-stem>.srt` unless `--srt-output` is supplied.
- No `temp_trimmed_*`, `temp_normalized_*`, `temp_audio_*`, or `temp_mixed_*`
  files left after a successful run.
- The source video and source music remain unchanged.

## Failure behavior

- Do not claim success unless requested artifacts pass verification.
- Preserve failed-run evidence needed for diagnosis, but never expose secrets.
- Report the failed stage, relevant command options, and concise stderr details.
- Do not retry paid transcription calls repeatedly without identifying the
  failure first.
