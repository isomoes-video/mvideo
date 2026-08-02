from __future__ import annotations

import os
import random
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from mvideo.highlights import HighlightClip


def build_subtitle_filter(subtitle_file: str, gpu: bool) -> str:
    """Build subtitle filter, uploading frames when AMD VAAPI encoding is used."""
    style = (
        "FontName=Source Han Sans SC,"
        "FontSize=20,"
        "PrimaryColour=&HFFFFFF,"
        "OutlineColour=&H000000,"
        "Outline=2,"
        "Shadow=1,"
        "Bold=1,"
        "MarginV=30,"
        "Alignment=2"
    )
    subtitle_filter = f"subtitles={subtitle_file}:force_style='{''.join(style)}'"
    if gpu:
        return f"{subtitle_filter},format=nv12,hwupload"
    return subtitle_filter


def gpu_acceleration_args(gpu: bool) -> list[str]:
    """Return ffmpeg input/global args for AMD GPU acceleration."""
    if gpu:
        return ["-vaapi_device", "/dev/dri/renderD128"]
    return []


def video_encoder_args(gpu: bool) -> list[str]:
    """Return ffmpeg video encoder args for AMD GPU or CPU encoding."""
    if gpu:
        return ["-c:v", "h264_vaapi", "-qp", "28"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]


def _filter_number(value: float) -> str:
    return f"{value:g}"


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_highlight_command(
    input_file: str,
    clips: Sequence[HighlightClip],
    output_file: str,
    label: str | None = None,
    gpu: bool = True,
    subtitle_file: str | None = None,
) -> list[str]:
    """Build a command that prepends clips and optionally burns subtitles."""
    stream_count = len(clips) + 1
    command = ["ffmpeg"]
    command.extend(gpu_acceleration_args(gpu))
    for clip in clips:
        command.extend(
            [
                "-ss",
                _filter_number(clip.start),
                "-t",
                _filter_number(clip.duration),
                "-i",
                input_file,
            ]
        )
    command.extend(["-i", input_file])

    filters = []

    for index, clip in enumerate(clips):
        video_filter = f"[{index}:v]setpts=PTS-STARTPTS"
        if label:
            escaped_label = _escape_drawtext(label)
            video_filter += (
                f",drawtext=text='{escaped_label}':expansion=none:"
                "font='Microsoft YaHei':x=48:y=48:fontcolor=white:fontsize=72:"
                "box=1:boxcolor=0xFB7299@0.92:boxborderw=18"
            )
        filters.append(f"{video_filter}[v{index}]")
        filters.append(f"[{index}:a]asetpts=PTS-STARTPTS[a{index}]")

    full_index = len(clips)
    filters.extend(
        [
            f"[{full_index}:v]setpts=PTS-STARTPTS[v{full_index}]",
            f"[{full_index}:a]asetpts=PTS-STARTPTS[a{full_index}]",
        ]
    )
    concat_inputs = "".join(f"[v{index}][a{index}]" for index in range(stream_count))
    if subtitle_file:
        filters.append(f"{concat_inputs}concat=n={stream_count}:v=1:a=1[vconcat][aout]")
        filters.append(f"[vconcat]{build_subtitle_filter(subtitle_file, gpu)}[vout]")
    elif gpu:
        filters.extend(
            [
                f"{concat_inputs}concat=n={stream_count}:v=1:a=1[vconcat][aout]",
                "[vconcat]format=nv12,hwupload[vout]",
            ]
        )
    else:
        filters.append(f"{concat_inputs}concat=n={stream_count}:v=1:a=1[vout][aout]")

    command.extend(["-filter_complex", ";".join(filters)])
    command.extend(["-map", "[vout]", "-map", "[aout]"])
    command.extend(video_encoder_args(gpu))
    command.extend(
        ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-y", output_file]
    )
    return command


def create_highlight_video_func(
    input_file: str,
    clips: Sequence[HighlightClip],
    output_file: str,
    label: str | None = None,
    gpu: bool = True,
    subtitle_file: str | None = None,
) -> None:
    """Prepend clips and optionally burn subtitles in one render."""
    logger.info(f"Creating opening highlight reel with {len(clips)} clips")
    subprocess.run(
        build_highlight_command(
            input_file,
            clips,
            output_file,
            label,
            gpu,
            subtitle_file,
        ),
        check=True,
    )
    logger.success(f"Highlight video created: {output_file}")


def check_dependencies() -> None:
    """Check if ffmpeg is installed."""
    if not shutil.which("ffmpeg"):
        logger.error("FFmpeg is not installed. Please install it first.")
        sys.exit(1)


def parse_time(time_input: str) -> float:
    """Parse time format (HH:MM:SS or seconds) to seconds."""
    if not time_input:
        return 0.0

    if re.match(r"^\d+:\d+:\d+$", str(time_input)):
        hours, minutes, seconds = map(int, time_input.split(":"))
        return float(hours * 3600 + minutes * 60 + seconds)

    if re.match(r"^\d+(\.\d+)?$", str(time_input)):
        return float(time_input)

    logger.error(f"Invalid time format: {time_input}. Use HH:MM:SS or seconds")
    sys.exit(1)


def get_video_duration(input_file: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logger.error(f"Could not determine duration for {input_file}")
        sys.exit(1)


def get_video_frame_count(input_file: str) -> int | None:
    """Get total frame count of a video file."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_packets",
        "-show_entries",
        "stream=nb_read_packets",
        "-of",
        "csv=p=0",
        input_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def analyze_audio_volume_func(input_file: str) -> float:
    logger.info(f"Analyzing audio volume for: {input_file}")
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-af",
        "volumedetect",
        "-vn",
        "-sn",
        "-dn",
        "-f",
        "null",
        "/dev/null",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = result.stderr

    mean_volume_match = re.search(r"mean_volume: ([\-\d\.]+) dB", output)
    max_volume_match = re.search(r"max_volume: ([\-\d\.]+) dB", output)

    mean_volume = 0.0
    if mean_volume_match:
        mean_volume = float(mean_volume_match.group(1))
        logger.info(f"Mean volume: {mean_volume} dB")
    else:
        logger.warning("Could not find mean volume")

    if max_volume_match:
        max_volume = float(max_volume_match.group(1))
        logger.info(f"Max volume: {max_volume} dB")

    return mean_volume


def extract_audio_func(input_file: str, output_file: str) -> None:
    """Extract audio from video file."""
    logger.info(f"Extracting audio from: {input_file}")
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        output_file,
        "-loglevel",
        "warning",
    ]
    subprocess.run(cmd, check=True)
    logger.success(f"Audio extracted: {output_file}")


def trim_video_func(
    input_file: str,
    start_trim: str,
    end_trim: str,
    output_file: str | None = None,
) -> None:
    """Trim video from start/end."""
    logger.info(f"Trimming video: {input_file}")
    duration = get_video_duration(input_file)
    logger.info(f"Original video duration: {int(duration)} seconds")

    start_seconds = parse_time(start_trim)
    end_seconds_trim = parse_time(end_trim)
    if start_seconds > 0:
        logger.info(f"Trimming {start_seconds} seconds from start")
    if end_seconds_trim > 0:
        logger.info(f"Trimming {end_seconds_trim} seconds from end")

    duration_trim = duration - end_seconds_trim - start_seconds
    if duration_trim <= 0:
        logger.error(
            "Invalid trim parameters. Resulting duration would be negative or zero."
        )
        sys.exit(1)
    logger.info(f"New duration: {duration_trim} seconds")

    if output_file is None:
        output_file = input_file
        temp_file = f"temp_trim_{random.randint(1000, 9999)}.mp4"
    else:
        temp_file = output_file

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-ss",
        str(start_seconds),
        "-t",
        str(duration_trim),
        "-c",
        "copy",
        "-y",
        temp_file,
        "-loglevel",
        "warning",
    ]
    subprocess.run(cmd, check=True)

    if output_file != input_file:
        shutil.move(temp_file, output_file)
        logger.success(f"Video trimmed successfully: {output_file}")
    else:
        shutil.move(temp_file, input_file)
        logger.success(f"Video trimmed successfully: {input_file}")


def normalize_audio_func(
    input_file: str,
    output_file: str,
    target_volume: float = -16.0,
) -> None:
    logger.info(f"Normalizing audio to {target_volume} dB")
    current_volume = analyze_audio_volume_func(input_file)
    adjustment = target_volume - current_volume
    logger.info(f"Adjusting volume by {adjustment:.2f} dB")

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-af",
        f"volume={adjustment}dB",
        "-c:v",
        "copy",
        "-y",
        output_file,
        "-loglevel",
        "warning",
    ]
    subprocess.run(cmd, check=True)
    logger.success(f"Audio normalized: {output_file}")


def burn_subtitles_func(
    input_file: str,
    subtitle_file: str,
    output_file: str,
    gpu: bool = True,
    start_seconds: float = 0,
    duration: float | None = None,
) -> None:
    """Burn subtitles into video with an optional trim."""
    logger.info(f"Burning subtitles into video: {input_file}")
    if start_seconds > 0 or duration is not None:
        logger.info(f"With trim: start={start_seconds}s, duration={duration}s")

    cmd = ["ffmpeg", "-fflags", "+genpts"]
    cmd.extend(gpu_acceleration_args(gpu))
    if start_seconds > 0:
        cmd.extend(["-ss", str(start_seconds)])
    cmd.extend(["-i", input_file, "-vf", build_subtitle_filter(subtitle_file, gpu)])
    if duration is not None:
        cmd.extend(["-t", str(duration)])
    cmd.extend(video_encoder_args(gpu))
    cmd.extend(["-c:a", "aac", "-b:a", "192k", "-y", output_file])

    try:
        subprocess.run(cmd, check=True)
        logger.success(f"Subtitles burned into video: {output_file}")
    except subprocess.CalledProcessError:
        logger.error("Failed to burn subtitles into video")
        sys.exit(1)


def add_subtitles_func(
    input_file: str,
    subtitle_file: str,
    output_file: str,
    gpu: bool = True,
) -> None:
    """Burn subtitles while preserving the source audio stream."""
    cmd = ["ffmpeg"]
    cmd.extend(gpu_acceleration_args(gpu))
    cmd.extend(["-i", input_file, "-vf", build_subtitle_filter(subtitle_file, gpu)])
    cmd.extend(video_encoder_args(gpu))
    cmd.extend(["-c:a", "copy", "-y", output_file])

    try:
        subprocess.run(cmd, check=True)
        logger.success(f"Success! Output saved to: {output_file}")
    except subprocess.CalledProcessError:
        logger.error("ffmpeg command failed")
        sys.exit(1)


def mix_with_background_music_func(
    video_file: str,
    background_music: str,
    output_file: str,
    music_volume: float = 0.3,
    video_audio_volume: float = 1.0,
) -> None:
    logger.info("Mixing video with background music")
    logger.info(f"Background music volume: {music_volume}")
    logger.info(f"Video audio volume: {video_audio_volume}")

    video_duration = get_video_duration(video_file)
    temp_music = f"temp_looped_music_{random.randint(1000, 9999)}.mp3"
    cmd_loop = [
        "ffmpeg",
        "-stream_loop",
        "-1",
        "-i",
        background_music,
        "-t",
        str(video_duration),
        "-c",
        "copy",
        "-y",
        temp_music,
        "-loglevel",
        "warning",
    ]
    subprocess.run(cmd_loop, check=True)

    filter_complex = (
        f"[0:a]volume={video_audio_volume}[va];"
        f"[1:a]volume={music_volume}[ba];"
        f"[va][ba]amix=inputs=2:duration=first"
    )
    cmd_mix = [
        "ffmpeg",
        "-i",
        video_file,
        "-i",
        temp_music,
        "-filter_complex",
        filter_complex,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-y",
        output_file,
        "-loglevel",
        "warning",
    ]
    subprocess.run(cmd_mix, check=True)

    if os.path.exists(temp_music):
        os.remove(temp_music)
    logger.success(f"Audio mixed successfully: {output_file}")
