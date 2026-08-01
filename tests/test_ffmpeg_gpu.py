from mvideo.ffmpeg import (
    build_subtitle_filter,
    gpu_acceleration_args,
    video_encoder_args,
)


def test_gpu_acceleration_uses_default_vaapi_device() -> None:
    assert gpu_acceleration_args(gpu=True) == [
        "-vaapi_device",
        "/dev/dri/renderD128",
    ]


def test_cpu_acceleration_uses_no_gpu_device() -> None:
    assert gpu_acceleration_args(gpu=False) == []


def test_gpu_encoder_uses_amd_vaapi() -> None:
    assert video_encoder_args(gpu=True) == ["-c:v", "h264_vaapi", "-qp", "28"]


def test_cpu_encoder_uses_libx264() -> None:
    assert video_encoder_args(gpu=False) == [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
    ]


def test_gpu_subtitle_filter_uploads_frames_for_vaapi() -> None:
    subtitle_filter = build_subtitle_filter("video.srt", gpu=True)

    assert subtitle_filter.startswith("subtitles=video.srt:force_style='")
    assert subtitle_filter.endswith("',format=nv12,hwupload")


def test_cpu_subtitle_filter_does_not_upload_frames() -> None:
    subtitle_filter = build_subtitle_filter("video.srt", gpu=False)

    assert subtitle_filter.startswith("subtitles=video.srt:force_style='")
    assert not subtitle_filter.endswith(",format=nv12,hwupload")
