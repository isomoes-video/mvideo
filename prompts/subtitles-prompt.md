# mvideo subtitle burning prompt

You are burning an approved SRT subtitle file into a video with the existing
`mvideo` CLI.

Use this prompt only for a stage-only subtitle job without opening highlights.
For the complete publishing workflow, use `highlights-prompt.md` to prepend
highlights and burn subtitles in one render.

## Goals

- Use the provided SRT file, or the input video's same-base-name `.srt` file.
- Render subtitles with the CLI's existing Source Han style.
- Prefer AMD VAAPI acceleration when the host supports it and use CPU encoding
  when it does not.
- Write a new video and preserve the input video and SRT.

## Input contract

- The user provides an existing input video.
- The subtitle path is optional only when `<input-stem>.srt` exists.
- The output defaults to
  `/home/isomoes/Videos/resource/<input-stem>_with_subs<input-extension>`.
- GPU mode uses AMD VAAPI and `/dev/dri/renderD128`; it is not NVIDIA NVENC.

## Running the CLI

```bash
# AMD VAAPI, enabled by default
uv run main.py add-subtitles <input-video> <subtitle.srt> \
  --output-video <output-video>

# Portable CPU fallback
uv run main.py add-subtitles <input-video> <subtitle.srt> \
  --output-video <output-video> --no-gpu
```

## Instructions

1. Confirm that the input video and resolved SRT file exist, and ensure
   `/home/isomoes/Videos/resource` exists for the default output.
2. Check that the SRT is non-empty and has parseable timestamps before a
   potentially long encode.
3. Use GPU mode only when `/dev/dri/renderD128` exists and FFmpeg exposes the
   `h264_vaapi` encoder. Otherwise use `--no-gpu`.
4. Run `add-subtitles`; do not duplicate its subtitle filter in a separate
   FFmpeg command.
5. Verify the output exists, is non-empty, and has video and audio streams.
6. Report the output path and whether AMD VAAPI or CPU encoding was used.

## Output contract

- One playable MP4 with permanently visible subtitles.
- The input video and source SRT remain unchanged.
- No temporary files remain after a successful run.
