# mvideo publishing workflow prompt

You are preparing a recording for publishing with the existing `mvideo` CLI.
This file is the orchestration prompt for a complete publishing job. Read the
specialized stage prompts below when performing their stages.

## Goals

- Apply requested start/end trimming.
- Normalize speech audio to the requested target level.
- Optionally mix looped background music.
- Generate an SRT through DashScope ASR.
- Select opening highlights and burn subtitles in the same final render.
- Generate bilingual titles, a summary, and chapters from the final SRT.
- Generate a 16:9 cover figure from that intro after the video is complete.
- Produce and verify every publishing artifact without replacing the existing
  CLI with custom scripts.

## Prompt catalog

- `audio-prompt.md`: inspect, trim, normalize, or mix audio into a video.
- `transcribe-prompt.md`: generate an SRT file with DashScope ASR.
- `subtitles-prompt.md`: burn an existing SRT for a stage-only job without
  highlights.
- `highlights-prompt.md`: prepend opening highlights, remap the SRT timeline,
  and burn subtitles in one final render.
- `srt2intro-prompt.md`: generate titles, a summary, and chapters from an SRT.
- `intro2figure-prompt.md`: generate a 16:9 cover image from the intro text.

Use a specialized prompt by itself when the user requests only that stage. For a
complete publishing job, follow the end-to-end instructions below.

## Input contract

- Required: an existing input video.
- All generated artifacts default to `/home/isomoes/Videos/resource`. Create the
  directory when it does not exist. An explicit user destination overrides this
  default.
- Optional trim values: seconds or `HH:MM:SS`; the agent chooses conservative
  values after inspection when the user does not specify them.
- Optional target volume: defaults to `-16.0` dB.
- Background music defaults to an agent-selected track from
  `/home/isomoes/Videos/bgm`; music volume defaults to `0.3`.
- Language hints default to `zh,en`.
- Transcription requires the DashScope and OSS environment variables documented
  in the project `README.md`.
- Plan a distinct filename under the resource directory for every intermediate
  and final video. Each stage must preserve the source artifact it receives.

## Orchestration rules

- Do not use the all-in-one `process` command for this workflow.
- Run one specialized prompt at a time in the order below.
- Read the entire specialized prompt before starting its stage and obey its
  input, safety, output, verification, and failure contracts.
- Feed only a verified output artifact into the next stage.
- Stop at the failed stage. Do not continue with a missing, empty, invalid, or
  unreviewed artifact.
- Skip optional operations only when the user did not request them; do not
  silently omit a requested stage.

## Complete workflow

1. **Plan artifacts.** Resolve all inputs, ensure
   `/home/isomoes/Videos/resource` exists, and choose distinct paths there for
   the prepared video, SRT, final video, intro `.txt`, cover `.png`, and
   highlight manifest. Confirm output conflicts first.
2. **Prepare audio and picture.** Follow `audio-prompt.md`. Inspect the recording
   and choose trim points, normalization settings, and a suitable track from
   `/home/isomoes/Videos/bgm`. Apply trim, normalize, then music mixing, and
   verify the prepared video before continuing.
3. **Transcribe.** Follow `transcribe-prompt.md` with the prepared video. Verify
   the generated SRT's encoding, numbering, and timestamps.
4. **Review subtitles.** Read the complete SRT and correct transcription errors
   without changing valid timing unnecessarily. The SRT must be approved before
   it is burned or used to select highlights.
5. **Render subtitles and highlights once.** Follow `highlights-prompt.md` with
   the prepared video and approved SRT. After manifest review, prepend the
   highlights and burn subtitles in one FFmpeg render. This stage rewrites the
   original SRT so it contains subtitle entries for the opening clips and shifts
   the complete video's entries by the total highlight duration. Verify both
   the final video and remapped SRT.
6. **Generate the intro.** After the combined render succeeds, follow
   `srt2intro-prompt.md` with the remapped SRT. Verify the matching `.txt` file
   contains Chinese and English titles, a summary, and valid chapter entries.
7. **Generate the cover.** Follow `intro2figure-prompt.md` with the verified
   intro. Download the returned image immediately and verify the matching `.png`
   is non-empty and readable.
8. **Report completion.** Report the absolute final video, remapped SRT, intro,
   cover, and highlight manifest paths, plus the effective settings used by each
   stage.

## Stage-only workflow

1. Use `audio-prompt.md` when you need an isolated audio or trim operation.
2. Use `transcribe-prompt.md` when you need an editable subtitle file.
3. Use `subtitles-prompt.md` only when subtitles are needed without highlights.
4. Use `highlights-prompt.md` for the combined highlight and subtitle render.
5. When the final video and SRT are complete, use `srt2intro-prompt.md` to write
   `/home/isomoes/Videos/resource/<video-name>.txt`.
6. Use `intro2figure-prompt.md` with that `.txt` file to generate
   `/home/isomoes/Videos/resource/<video-name>.png` as the final publishing
   artifact.

## Output contract

- Prepared video: `/home/isomoes/Videos/resource/<video-name>_prepared.mp4`.
- Final video: `/home/isomoes/Videos/resource/<video-name>_final.mp4`.
- Generated subtitles: `/home/isomoes/Videos/resource/<video-name>.srt`.
- Highlight manifest:
  `/home/isomoes/Videos/resource/<video-name>.highlights.json`.
- Generated intro: `/home/isomoes/Videos/resource/<video-name>.txt`.
- Generated cover: `/home/isomoes/Videos/resource/<video-name>.png`.
- Use explicit user paths instead of these defaults when provided.
- No `temp_trimmed_*`, `temp_normalized_*`, `temp_audio_*`, or `temp_mixed_*`
  files left after a successful run.
- The source video and source music remain unchanged. The approved SRT is
  intentionally rewritten to match the prepended highlight timeline.

## Failure behavior

- Do not claim success unless every requested artifact passes verification.
- Preserve failed-run evidence needed for diagnosis, but never expose secrets.
- Report the failed stage, relevant command options, and concise stderr details.
- Do not retry paid transcription calls repeatedly without identifying the
  failure first.
- Do not run the intro or figure stages after a failed video or SRT stage.

The video workflow prompts instruct the agent to use the existing Typer CLI in
`main.py`; they do not authorize replacing the CLI with ad hoc FFmpeg commands
or new scripts.
