# mvideo opening highlights prompt

You are selecting and rendering a short opening highlight reel for a Bilibili
video. Use the final processed video and its matching, reviewed SRT so selected
timestamps match the video that will be rendered.

## Goals

- Hook the viewer quickly with the strongest moments from the complete video.
- Create an editable JSON manifest before any video encoding.
- Keep the highlight reel at 30 seconds or less, preferably 15-25 seconds.
- Prepend the selected clips to the complete video without removing content.
- Render through the existing `mvideo highlight` command, not an ad hoc script.

## Input contract

- Required: an existing final processed video and its matching reviewed SRT.
- Required: a distinct output video path.
- The manifest defaults to `<video-stem>.highlights.json` when the user does not
  specify a path.
- Select against final-video timestamps. Do not use timestamps from an
  unadjusted source transcript after trimming or other timeline changes.
- The default reel label is `精彩预告`; use `--no-label` only when requested.

## Selection rules

- Select 3-6 clips when enough strong material exists.
- Each clip should normally be 2.5-7 seconds and contain a complete thought or
  understandable visual action.
- Put the strongest hook first, even when it occurs later in the source video.
- Prefer surprising results, clear benefits, strong opinions, humor, conflict,
  concise questions, and visually interesting demonstrations.
- Avoid greetings, housekeeping, repeated points, advertisements, unfinished
  sentences, misleading excerpts, and major spoilers.
- Add enough context around speech to avoid clipped words, but remove silence
  and weak setup.
- Do not select overlapping clips or repeat substantially identical moments.
- Transcript quality alone is not evidence of visual quality. When frames or a
  video preview are available, confirm that each selected interval is visually
  usable.

## Manifest contract

Write UTF-8 JSON only, with no Markdown fence, using this structure:

```json
{
  "max_duration": 30,
  "clips": [
    {
      "start": 42.5,
      "end": 47.0,
      "reason": "A concise question that establishes the viewer's problem"
    },
    {
      "start": 318.2,
      "end": 324.0,
      "reason": "The finished result is clearly demonstrated"
    }
  ]
}
```

`start` and `end` are seconds on the final processed video's timeline. Manifest
order is playback order. The combined clip duration must not exceed
`max_duration`, and `max_duration` must not exceed 30.

## Running the CLI

```bash
uv run main.py highlight <processed-video> <manifest.json> <output-video> \
  --max-duration 30 \
  --label "精彩预告"
```

Add `--no-gpu` when AMD VAAPI is unavailable. Add `--no-label` only when the
creator does not want the default overlay. Never add `--overwrite` without the
creator's approval when the output already exists.

## Instructions

1. Resolve the final video and matching SRT paths and confirm both exist.
2. Probe the final video duration and inspect the complete SRT before choosing
   clips.
3. Create the manifest according to the selection and manifest contracts.
4. Present the selected timestamps, total duration, and reasons for creator
   review before starting the potentially long encode.
5. Check output conflicts and GPU capability, then run `mvideo highlight` once.
6. Verify that the output is readable, contains video and audio streams, starts
   with the selected clips in manifest order, continues with the complete
   video, and has the expected duration.
7. Report the absolute manifest and output paths and the effective reel length.

## Output contract

- One editable `<video-stem>.highlights.json` manifest.
- One output video containing `[highlight clips][complete processed video]`.
- Source video, SRT, and manifest remain unchanged during rendering.
- Reel duration is the sum of clip durations and never exceeds 30 seconds.

## Failure behavior

- Stop when timestamps overlap, exceed video duration, or exceed the configured
  reel limit; do not silently modify the creator-approved selection.
- Stop when the final video and SRT timelines do not match.
- Preserve the manifest when encoding fails so the job can be diagnosed and
  retried without repeating selection work.
- Do not claim success until the rendered artifact passes verification.
