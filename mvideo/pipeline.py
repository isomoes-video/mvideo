import os
import random
import shutil
import sys

from loguru import logger

from mvideo.ffmpeg import (
    burn_subtitles_func,
    extract_audio_func,
    get_video_duration,
    mix_with_background_music_func,
    normalize_audio_func,
    parse_time,
    trim_video_func,
)
from mvideo.subtitles import adjust_srt_timestamps, generate_srt_from_transcription
from mvideo.transcription import transcribe_audio_func


def process_video(
    input_video: str,
    output_video: str,
    start_trim: str = "0",
    end_trim: str = "0",
    background_music: str | None = None,
    target_volume: float = -16.0,
    music_volume: float = 0.3,
    generate_srt: bool = False,
    burn_srt: bool = False,
    srt_output: str | None = None,
    language: str = "zh,en",
    gpu: bool = True,
) -> None:
    """Run the full video processing pipeline."""
    logger.info("Starting full video processing pipeline...")
    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)
    if burn_srt:
        generate_srt = True

    temp_trimmed = f"temp_trimmed_{random.randint(1000, 9999)}.mp4"
    temp_normalized = f"temp_normalized_{random.randint(1000, 9999)}.mp4"
    temp_audio = f"temp_audio_{random.randint(1000, 9999)}.wav"
    temp_mixed = f"temp_mixed_{random.randint(1000, 9999)}.mp4"
    current_input = input_video

    start_seconds = parse_time(start_trim)
    end_seconds_trim = parse_time(end_trim)
    video_duration = get_video_duration(input_video)
    trim_duration = (
        video_duration - start_seconds - end_seconds_trim
        if (start_seconds > 0 or end_seconds_trim > 0)
        else None
    )

    if not burn_srt and (start_trim != "0" or end_trim != "0"):
        trim_video_func(current_input, start_trim, end_trim, temp_trimmed)
        current_input = temp_trimmed

    logger.info("Normalizing video audio...")
    normalize_audio_func(current_input, temp_normalized, target_volume)

    if background_music and os.path.exists(background_music):
        mix_with_background_music_func(
            temp_normalized,
            background_music,
            temp_mixed,
            music_volume,
        )
    else:
        if background_music:
            logger.warning(
                f"Background music file not found: {background_music}. Copying video..."
            )
        shutil.copy(temp_normalized, temp_mixed)

    srt_file = None
    if generate_srt:
        logger.info("Generating SRT subtitles...")
        if srt_output is None:
            filename, _ = os.path.splitext(output_video)
            srt_file = f"{filename}.srt"
        else:
            srt_file = srt_output

        extract_audio_func(temp_normalized, temp_audio)
        language_hints = [lang.strip() for lang in language.split(",")]
        logger.info(f"Language hints: {language_hints}")
        try:
            results = transcribe_audio_func(temp_audio, language_hints)
            if not results:
                logger.warning("No transcription results received")
                srt_file = None
            else:
                srt_content = generate_srt_from_transcription(results)
                if not srt_content.strip():
                    logger.warning("Transcription returned empty results")
                    srt_file = None
                else:
                    with open(srt_file, "w", encoding="utf-8") as file:
                        file.write(srt_content)
                    logger.success(f"Subtitle file saved: {srt_file}")
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    if burn_srt and srt_file and os.path.exists(srt_file):
        if start_seconds > 0:
            adjust_srt_timestamps(srt_file, start_seconds)
        burn_subtitles_func(
            temp_mixed,
            srt_file,
            output_video,
            gpu,
            start_seconds=start_seconds,
            duration=trim_duration,
        )
    elif burn_srt:
        logger.warning("No SRT file available, skipping subtitle burning")
        shutil.copy(temp_mixed, output_video)
    else:
        shutil.copy(temp_mixed, output_video)

    for temp_file in [temp_trimmed, temp_normalized, temp_mixed]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    logger.success(f"Video processing complete: {output_video}")


def transcribe_video(
    input_video: str,
    output_subtitle: str,
    language: str = "zh,en",
    keep_audio: bool = False,
) -> None:
    """Extract video audio, transcribe it, and write an SRT file."""
    temp_audio = f"temp_audio_{random.randint(1000, 9999)}.wav"
    extract_audio_func(input_video, temp_audio)
    language_hints = [lang.strip() for lang in language.split(",")]
    logger.info(f"Language hints: {language_hints}")

    try:
        results = transcribe_audio_func(temp_audio, language_hints)
        if not results:
            logger.error("No transcription results received")
            sys.exit(1)

        srt_content = generate_srt_from_transcription(results)
        if not srt_content.strip():
            logger.warning("Transcription returned empty results")
        else:
            with open(output_subtitle, "w", encoding="utf-8") as file:
                file.write(srt_content)
            logger.success(f"Subtitle file saved: {output_subtitle}")
    finally:
        if not keep_audio and os.path.exists(temp_audio):
            os.remove(temp_audio)
        elif keep_audio:
            logger.info(f"Audio file kept: {temp_audio}")
