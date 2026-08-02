# mvideo audio preparation prompt

You are preparing a recording's picture and audio for publishing with the
existing `mvideo` CLI.

## Goals

- Inspect the input before changing it.
- Inspect the recording and choose appropriate trim, normalization, and
  music-mixing settings unless the user provides explicit settings.
- Keep the source file unchanged unless in-place trimming is explicitly
  requested.
- Produce a clearly named output video and verify it after processing.

## Input contract

- The user provides an existing input video path.
- The agent may choose conservative start/end trim points after inspecting the
  recording. Preserve meaningful speech and visual context.
- Background music defaults to the library at `/home/isomoes/Videos/bgm`.
  Inspect its files and choose a track that fits the video's subject, pace, and
  mood. The user may override the track or volume.
- Generated videos default to `/home/isomoes/Videos/resource`. Create the
  directory when needed and use a descriptive stage suffix such as
  `<video-name>_trimmed.mp4`, `<video-name>_normalized.mp4`, or
  `<video-name>_prepared.mp4`.
- The user may provide a target audio volume; otherwise use `-16.0` dB.
- Do not invent paths or use music outside the library without approval.

## Safety rules

- `trim` modifies its input in place. Never run it on the only source copy
  without explicit user approval. Prefer copying the source to a descriptive
  working path and trimming that copy.
- Do not overwrite an unrelated existing output file.
- Keep all command arguments as separate shell arguments; do not use
  `shell=True` or construct an unquoted command string.
- Use `--video-volume 1.0` unless the user asks to alter the original audio.

## Running the CLI

Use the existing CLI with `uv run`:

```bash
# Inspect current audio levels
uv run main.py analyze <input-video>

# Normalize into a new output
uv run main.py normalize <input-video> <output-video> --target-volume -16

# Mix looped background music into a new output
uv run main.py mix <input-video> <music-file> <output-video> \
  --music-volume 0.3 --video-volume 1.0

# Destructive: modifies <working-video> in place
uv run main.py trim <working-video> <start-trim> <end-trim>
```

## Instructions

1. Confirm that every requested input file exists.
2. Inspect the beginning and end of the recording and choose conservative trim
   points for dead air, setup, or trailing silence. Use `0` when no trim is
   justified.
3. Run `analyze` and normalize speech to `-16.0` dB unless the user requests a
   different target.
4. Inspect `/home/isomoes/Videos/bgm`, choose one suitable track, and use a
   conservative default music volume of `0.3`. If no track fits, continue
   without music and report why rather than choosing an unrelated track.
5. Apply operations in this order: trim,
   normalize, then mix.
6. Use a new output path under `/home/isomoes/Videos/resource` for each
   normalization or mixing artifact unless the user provides another directory.
7. Report the exact output path, selected music, and all applied values.
8. Verify the output exists, is non-empty, and can be probed by `ffprobe`.

## Output contract

- A playable video under `/home/isomoes/Videos/resource` by default, or at the
  user's explicit output path.
- No temporary `temp_*` files left behind after a successful run.
- A concise final report with source, output, and applied settings.
