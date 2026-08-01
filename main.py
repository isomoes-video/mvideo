"""Compatibility entry point for the mvideo command-line application."""

from mvideo.cli import (
    add_subtitles,
    analyze,
    app,
    callback,
    mix,
    normalize,
    process,
    transcribe,
    trim,
)
from mvideo.ffmpeg import (
    analyze_audio_volume_func,
    build_subtitle_filter,
    burn_subtitles_func,
    check_dependencies,
    extract_audio_func,
    get_video_duration,
    get_video_frame_count,
    gpu_acceleration_args,
    mix_with_background_music_func,
    normalize_audio_func,
    parse_time,
    trim_video_func,
    video_encoder_args,
)
from mvideo.subtitles import (
    adjust_srt_timestamps,
    format_srt_timestamp,
    generate_srt_from_transcription,
    parse_srt_timestamp,
)
from mvideo.transcription import (
    delete_oss_file,
    get_oss_client,
    transcribe_audio_func,
    upload_file_to_oss,
)

__all__ = [
    "add_subtitles",
    "adjust_srt_timestamps",
    "analyze",
    "analyze_audio_volume_func",
    "app",
    "build_subtitle_filter",
    "burn_subtitles_func",
    "callback",
    "check_dependencies",
    "delete_oss_file",
    "extract_audio_func",
    "format_srt_timestamp",
    "generate_srt_from_transcription",
    "get_oss_client",
    "get_video_duration",
    "get_video_frame_count",
    "gpu_acceleration_args",
    "mix",
    "mix_with_background_music_func",
    "normalize",
    "normalize_audio_func",
    "parse_srt_timestamp",
    "parse_time",
    "process",
    "transcribe",
    "transcribe_audio_func",
    "trim",
    "trim_video_func",
    "upload_file_to_oss",
    "video_encoder_args",
]


if __name__ == "__main__":
    app()
