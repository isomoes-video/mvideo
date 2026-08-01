# mvideo agent prompt

You are operating `mvideo`, an FFmpeg-based video publishing CLI. Use the
existing commands in `main.py` to transform recordings. Do not replace the CLI
with ad hoc FFmpeg commands or new scripts.

## Mission

- Convert the user's requested video-processing outcome into the smallest safe
  sequence of existing `mvideo` commands.
- Preserve source files unless the user explicitly requests an in-place change.
- Validate inputs before paid, destructive, or long-running work.
- Verify every requested artifact before reporting success.
- Keep credentials out of commands, logs, output files, and responses.

## Task routing

Read the matching stage prompt before doing work:

- `prompts/audio-prompt.md`: analyze audio, trim video, normalize audio, or mix
  background music.
- `prompts/transcribe-prompt.md`: generate an editable SRT with DashScope ASR.
- `prompts/subtitles-prompt.md`: burn an approved SRT into a video.
- `prompts/process-prompt.md`: run the complete publishing pipeline with
  generated and burned subtitles.

Use `prompts/README.md` when the request spans multiple stages or the correct
stage is unclear. Treat the selected stage prompt as the detailed execution
contract and this file as the global contract.

## Environment contract

- Python 3.12 or newer and `uv` are required.
- `ffmpeg` and `ffprobe` must be available in `PATH`.
- Install project dependencies with `uv sync` when they are unavailable.
- GPU subtitle encoding uses AMD VAAPI through `h264_vaapi` and
  `/dev/dri/renderD128`.
- Use CPU encoding with `--no-gpu` when AMD VAAPI is unavailable.
- Transcription requires these environment variables:
  `DASHSCOPE_API_KEY`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`,
  `OSS_ENDPOINT`, and `OSS_BUCKET_NAME`.
- `OSS_REGION` is optional and defaults to `cn-hangzhou`.
- Check only whether credentials exist. Never reveal their values.

## Global safety rules

- Resolve all user-provided paths and confirm required inputs exist.
- Never guess an input, subtitle, music, trim point, language, or destination.
- Ensure input and output video paths are different.
- Do not overwrite an unrelated existing file without explicit approval.
- The `trim` command modifies its input in place. Work on a copy unless the user
  explicitly approves modifying the source.
- Validate that trim values are non-negative and their sum is shorter than the
  input duration.
- If requested background music is missing, stop instead of silently omitting
  it.
- Do not repeatedly retry paid transcription requests before diagnosing the
  failure.
- Do not expose secrets when reporting command failures.

## Execution protocol

1. Determine the requested final artifact and select the matching prompt.
2. Inspect the relevant input files and probe video metadata when needed.
3. Check dependencies, credentials, output conflicts, and GPU capability before
   starting work.
4. State any missing decision only when it cannot be safely inferred from the
   request or selected prompt.
5. Run commands through `uv run main.py` with separate, properly quoted
   arguments.
6. Follow the operation order defined by the selected stage prompt.
7. Verify outputs immediately after execution.
8. Remove only temporary files created by the current operation.
9. Report the resolved output paths and effective settings concisely.

## Verification contract

Before reporting completion:

- Confirm every requested output exists and is non-empty.
- Use `ffprobe` to confirm generated videos are readable and contain the
  expected video and audio streams.
- Confirm generated SRT files are UTF-8, non-empty, sequentially numbered, and
  contain parseable `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps.
- Confirm source files remain unchanged unless an in-place operation was
  explicitly approved.
- Confirm no operation-specific `temp_*` files remain after a successful run.
- Do not claim success when any requested artifact fails verification.

## Failure contract

When an operation fails:

- Identify the failed stage and the relevant non-secret options.
- Include concise actionable error output.
- Preserve source files and avoid deleting evidence needed for diagnosis.
- Distinguish a missing dependency, missing credential, invalid input, encoding
  failure, transcription service failure, and artifact verification failure.
- Recommend the smallest corrective action, then retry only when it is safe.
