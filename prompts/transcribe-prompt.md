# mvideo transcription prompt

You are generating an editable SRT subtitle file from a video with the existing
`mvideo` CLI.

## Goals

- Extract and transcribe the video's speech with DashScope ASR.
- Preserve subtitle timing and ordering returned by the transcription service.
- Write one SRT file under `/home/isomoes/Videos/resource` by default.
- Remove temporary extracted audio unless the user asks to keep it.

## Input contract

- The user provides an existing input video path.
- The output defaults to
  `/home/isomoes/Videos/resource/<input-video-stem>.srt`.
- Language hints default to `zh,en`; pass a comma-separated list when the user
  specifies different languages.
- `DASHSCOPE_API_KEY`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`,
  `OSS_ENDPOINT`, and `OSS_BUCKET_NAME` must be available in the environment.
- `OSS_REGION` is optional and defaults to `cn-hangzhou`.

## Running the CLI

```bash
uv run main.py transcribe <input-video> \
  --output-subtitle <output.srt> \
  --language zh,en
```

Use `--keep-audio` only when the user explicitly needs the extracted WAV for
debugging or reuse.

## Instructions

1. Confirm the input video exists, ensure `/home/isomoes/Videos/resource`
   exists, and use its default SRT path unless the user supplied another path.
2. Check only whether required environment variables are present. Never print
   their values or place secrets in commands, logs, prompts, or files.
3. Run the existing `transcribe` command; do not call DashScope or OSS with an
   ad hoc script.
4. If credentials are missing, stop and report the missing variable names.
5. After completion, validate that the SRT is non-empty, numbered in sequence,
   and contains parseable `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamp lines.
6. Read the complete SRT and automatically correct high-confidence ASR errors,
   especially product names, project names, versions, commands, APIs, and
   English technical terms. Use visible UI text, project documentation, and
   closely related existing subtitles or introductions as evidence when
   available. Preserve valid cue numbering, ordering, and timestamps, and leave
   uncertain wording unchanged rather than guessing.
7. Revalidate the corrected SRT, then report its absolute path and the types of
   terminology corrected.

## Output contract

- One reviewed and terminology-corrected UTF-8 SRT file at the requested path.
- No extracted temporary audio unless `--keep-audio` was requested.
- Temporary OSS content is deleted by the existing CLI after transcription.
