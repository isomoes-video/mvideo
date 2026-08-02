from pathlib import Path

from mvideo import pipeline


def test_process_video_writes_output_without_burned_subtitles(
    tmp_path, monkeypatch
) -> None:
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "output.mp4"
    input_video.write_bytes(b"processed video")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline, "get_video_duration", lambda _path: 60.0)
    monkeypatch.setattr(
        pipeline,
        "normalize_audio_func",
        lambda source, destination, _volume: Path(destination).write_bytes(
            Path(source).read_bytes()
        ),
    )

    pipeline.process_video(str(input_video), str(output_video))

    assert output_video.read_bytes() == b"processed video"
