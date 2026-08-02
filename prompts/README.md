# mvideo agent prompts

These prompts turn `mvideo` into a stage-based, agent-friendly video processing
workflow. Give an agent the prompt for the artifact you want and the paths and
options for the current job.

## Prompt catalog

- `audio-prompt.md`: inspect, trim, normalize, or mix audio into a video.
- `transcribe-prompt.md`: generate an SRT file with DashScope ASR.
- `subtitles-prompt.md`: burn an existing SRT file into a video.
- `process-prompt.md`: run the complete publishing pipeline.
- `highlights-prompt.md`: select and prepend a Bilibili opening highlight reel.

## Recommended workflow

1. Use `audio-prompt.md` when you need an isolated audio or trim operation.
2. Use `transcribe-prompt.md` when you need an editable subtitle file.
3. Review and correct the SRT before using `subtitles-prompt.md`.
4. Use `process-prompt.md` when all desired operations should run together.
5. Use `highlights-prompt.md` after processing to prepend reviewed highlights.

The video workflow prompts instruct the agent to use the existing Typer CLI in
`main.py`; they do not authorize replacing the CLI with ad hoc FFmpeg commands
or new scripts.
