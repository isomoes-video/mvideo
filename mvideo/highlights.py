from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from mvideo.ffmpeg import create_highlight_video_func, get_video_duration
from mvideo.subtitles import format_srt_timestamp, parse_srt_timestamp

MAX_HIGHLIGHT_DURATION = 30.0


@dataclass(frozen=True)
class HighlightClip:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def remap_srt_for_highlights(content: str, clips: list[HighlightClip]) -> str:
    """Prepend subtitle excerpts and offset the complete video's subtitles."""
    entries = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start_text, end_text = lines[1].split(" --> ", 1)
        entries.append(
            (
                parse_srt_timestamp(start_text.strip()),
                parse_srt_timestamp(end_text.strip()),
                "\n".join(lines[2:]),
            )
        )

    remapped = []
    reel_position = 0.0
    for clip in clips:
        for start, end, text in entries:
            clipped_start = max(start, clip.start)
            clipped_end = min(end, clip.end)
            if clipped_end > clipped_start:
                remapped.append(
                    (
                        reel_position + clipped_start - clip.start,
                        reel_position + clipped_end - clip.start,
                        text,
                    )
                )
        reel_position += clip.duration

    remapped.extend(
        (start + reel_position, end + reel_position, text)
        for start, end, text in entries
    )

    lines = []
    for index, (start, end, text) in enumerate(remapped, 1):
        lines.extend(
            [
                str(index),
                f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                text,
                "",
            ]
        )
    return "\n".join(lines)


def _number(value: object, field: str, index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Clip {index} {field} must be a number")
    return float(value)


def load_highlight_clips(
    manifest_file: str | Path,
    video_duration: float,
    max_duration: float = MAX_HIGHLIGHT_DURATION,
) -> list[HighlightClip]:
    """Load and validate highlight clips from a JSON manifest."""
    if max_duration <= 0 or max_duration > MAX_HIGHLIGHT_DURATION:
        raise ValueError("Maximum highlight duration must be between 0 and 30 seconds")

    with Path(manifest_file).open(encoding="utf-8") as file:
        manifest = json.load(file)
    if not isinstance(manifest, dict):
        raise TypeError("Highlight manifest must be a JSON object")

    manifest_limit = manifest.get("max_duration", max_duration)
    if isinstance(manifest_limit, bool) or not isinstance(manifest_limit, (int, float)):
        raise TypeError("Manifest max_duration must be a number")
    if manifest_limit <= 0 or manifest_limit > MAX_HIGHLIGHT_DURATION:
        raise ValueError("Manifest max_duration must be between 0 and 30 seconds")
    effective_limit = min(float(manifest_limit), max_duration)

    raw_clips = manifest.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise ValueError("Highlight manifest must contain at least one clip")

    clips = []
    for index, raw_clip in enumerate(raw_clips, 1):
        if not isinstance(raw_clip, dict):
            raise TypeError(f"Clip {index} must be a JSON object")
        start = _number(raw_clip.get("start"), "start", index)
        end = _number(raw_clip.get("end"), "end", index)
        if start < 0:
            raise ValueError(f"Clip {index} start must be non-negative")
        if end <= start:
            raise ValueError(f"Clip {index} end must be greater than start")
        if end > video_duration:
            raise ValueError(f"Clip {index} exceeds video duration")
        clips.append(HighlightClip(start, end))

    source_order = sorted(clips, key=lambda clip: clip.start)
    for previous, current in pairwise(source_order):
        if current.start < previous.end:
            raise ValueError("A highlight clip overlaps another clip")

    total_duration = sum(clip.duration for clip in clips)
    if total_duration > effective_limit:
        raise ValueError(
            f"Highlight clips exceed the {effective_limit:g} seconds duration limit"
        )
    return clips


def create_highlight_video(
    input_video: str | Path,
    manifest_file: str | Path,
    output_video: str | Path,
    max_duration: float = MAX_HIGHLIGHT_DURATION,
    label: str | None = "精彩预告",
    gpu: bool = True,
    overwrite: bool = False,
    subtitle_file: str | Path | None = None,
) -> None:
    """Validate a highlight job and render it with FFmpeg."""
    input_path = Path(input_video)
    manifest_path = Path(manifest_file)
    output_path = Path(output_video)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Highlight manifest not found: {manifest_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output video paths must be different")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output video already exists: {output_path}")

    subtitle_path = Path(subtitle_file) if subtitle_file is not None else None
    if subtitle_path is not None and not subtitle_path.is_file():
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

    clips = load_highlight_clips(
        manifest_path,
        video_duration=get_video_duration(str(input_path)),
        max_duration=max_duration,
    )
    if subtitle_path is None:
        create_highlight_video_func(
            str(input_path),
            clips,
            str(output_path),
            label,
            gpu,
        )
        return

    remapped_srt = remap_srt_for_highlights(
        subtitle_path.read_text(encoding="utf-8"),
        clips,
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".srt",
        prefix="mvideo_highlights_",
        dir=subtitle_path.parent,
        encoding="utf-8",
        delete=False,
    ) as file:
        file.write(remapped_srt)
        temporary_subtitle = Path(file.name)

    try:
        create_highlight_video_func(
            str(input_path),
            clips,
            str(output_path),
            label,
            gpu,
            str(temporary_subtitle),
        )
        subtitle_path.write_text(remapped_srt, encoding="utf-8")
    finally:
        temporary_subtitle.unlink(missing_ok=True)
