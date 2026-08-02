import os
import sys

import typer
from loguru import logger

from mvideo.ffmpeg import (
    add_subtitles_func,
    analyze_audio_volume_func,
    check_dependencies,
    mix_with_background_music_func,
    normalize_audio_func,
    trim_video_func,
)
from mvideo.highlights import create_highlight_video
from mvideo.pipeline import process_video, transcribe_video

app = typer.Typer(help="Video Processor for OBS Recordings and Subtitles")


@app.callback()
def callback() -> None:
    """Video Processor for OBS Recordings and Subtitles."""
    check_dependencies()


@app.command()
def trim(input_video: str, start_trim: str, end_trim: str) -> None:
    """Trim video from start/end (modifies original file in-place)."""
    trim_video_func(input_video, start_trim, end_trim)


@app.command()
def normalize(
    input_video: str,
    output_video: str,
    target_volume: float = typer.Option(-16.0, help="Target volume in dB"),
) -> None:
    """Normalize audio to a target volume."""
    normalize_audio_func(input_video, output_video, target_volume)


@app.command()
def analyze(input_video: str) -> None:
    """Analyze audio volume."""
    analyze_audio_volume_func(input_video)


@app.command()
def mix(
    input_video: str,
    background_music: str,
    output_video: str,
    music_volume: float = typer.Option(0.3, help="Music volume (0.0-1.0)"),
    video_volume: float = typer.Option(1.0, help="Video audio volume (0.0-1.0)"),
) -> None:
    """Mix video with background music."""
    mix_with_background_music_func(
        input_video,
        background_music,
        output_video,
        music_volume,
        video_volume,
    )


@app.command()
def process(
    input_video: str,
    output_video: str,
    start_trim: str = typer.Option("0", help="Trim from start (HH:MM:SS or seconds)"),
    end_trim: str = typer.Option("0", help="Trim from end (HH:MM:SS or seconds)"),
    background_music: str | None = typer.Option(None, help="Background music file"),
    target_volume: float = typer.Option(-16.0, help="Target volume in dB"),
    music_volume: float = typer.Option(0.3, help="Music volume"),
    generate_srt: bool = typer.Option(False, "--srt", help="Generate SRT subtitles"),
    burn_srt: bool = typer.Option(
        False,
        "--burn-srt",
        help="Burn subtitles into output video",
    ),
    srt_output: str | None = typer.Option(None, help="Output SRT file path"),
    language: str = typer.Option(
        "zh,en",
        help="Language hints for transcription (comma-separated)",
    ),
    gpu: bool = typer.Option(
        True,
        help="Use AMD GPU acceleration for subtitle burning",
    ),
) -> None:
    """Run full processing pipeline with optional subtitle generation."""
    process_video(
        input_video=input_video,
        output_video=output_video,
        start_trim=start_trim,
        end_trim=end_trim,
        background_music=background_music,
        target_volume=target_volume,
        music_volume=music_volume,
        generate_srt=generate_srt,
        burn_srt=burn_srt,
        srt_output=srt_output,
        language=language,
        gpu=gpu,
    )


@app.command()
def add_subtitles(
    input_video: str,
    subtitle_file: str | None = typer.Argument(
        None,
        help="Subtitle file (default: same path as video, .srt extension)",
    ),
    output_video: str | None = typer.Option(None, help="Output video filename"),
    gpu: bool = typer.Option(True, help="Use AMD GPU acceleration"),
) -> None:
    """Add hardcoded subtitles to video with Source Han font."""
    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)

    if subtitle_file is None:
        filename, _ = os.path.splitext(input_video)
        subtitle_file = f"{filename}.srt"
    if not output_video:
        filename, extension = os.path.splitext(input_video)
        output_video = f"{filename}_with_subs{extension}"
    if not os.path.exists(subtitle_file):
        logger.error(f"Subtitle file not found: {subtitle_file}")
        sys.exit(1)

    logger.info(f"Input video: {input_video}")
    logger.info(f"Subtitle file: {subtitle_file}")
    logger.info(f"Output video: {output_video}")
    add_subtitles_func(input_video, subtitle_file, output_video, gpu)


@app.command()
def transcribe(
    input_video: str,
    output_subtitle: str | None = typer.Option(
        None,
        help="Output SRT subtitle file",
    ),
    language: str = typer.Option(
        "zh,en",
        help="Language hints (comma-separated, e.g., 'zh,en')",
    ),
    keep_audio: bool = typer.Option(False, help="Keep extracted audio file"),
) -> None:
    """Transcribe audio from video to text using DashScope ASR."""
    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)
    if not output_subtitle:
        filename, _ = os.path.splitext(input_video)
        output_subtitle = f"{filename}.srt"

    logger.info(f"Input video: {input_video}")
    logger.info(f"Output subtitle: {output_subtitle}")
    transcribe_video(input_video, output_subtitle, language, keep_audio)


@app.command()
def highlight(
    input_video: str,
    manifest_file: str,
    output_video: str,
    max_duration: float = typer.Option(
        30.0,
        min=0.1,
        max=30.0,
        help="Maximum total highlight duration in seconds",
    ),
    label: str = typer.Option("精彩预告", help="Label shown over highlight clips"),
    no_label: bool = typer.Option(False, "--no-label", help="Do not show a label"),
    gpu: bool = typer.Option(
        True,
        "--gpu/--no-gpu",
        help="Use AMD GPU acceleration",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Replace an existing output video",
    ),
) -> None:
    """Prepend selected clips from a JSON manifest to a complete video."""
    try:
        create_highlight_video(
            input_video,
            manifest_file,
            output_video,
            max_duration=max_duration,
            label=None if no_label else label,
            gpu=gpu,
            overwrite=overwrite,
        )
    except (FileNotFoundError, FileExistsError, TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
