import json

import pytest

from mvideo.ffmpeg import build_highlight_command
from mvideo.highlights import (
    HighlightClip,
    create_highlight_video,
    load_highlight_clips,
)


def write_manifest(tmp_path, clips, max_duration=30):
    manifest = tmp_path / "video.highlights.json"
    manifest.write_text(
        json.dumps({"max_duration": max_duration, "clips": clips}),
        encoding="utf-8",
    )
    return manifest


def test_load_highlight_clips_preserves_editorial_order(tmp_path) -> None:
    manifest = write_manifest(
        tmp_path,
        [
            {"start": 40.0, "end": 45.0, "reason": "Strongest hook"},
            {"start": 10.0, "end": 14.5, "reason": "Sets up the topic"},
        ],
    )

    clips = load_highlight_clips(manifest, video_duration=60.0)

    assert clips == [
        HighlightClip(40.0, 45.0),
        HighlightClip(10.0, 14.5),
    ]


@pytest.mark.parametrize(
    ("clips", "message"),
    [
        ([{"start": 4, "end": 4}], "end must be greater than start"),
        ([{"start": -1, "end": 2}], "start must be non-negative"),
        ([{"start": 55, "end": 61}], "exceeds video duration"),
        (
            [{"start": 2, "end": 8}, {"start": 7, "end": 10}],
            "overlaps another clip",
        ),
    ],
)
def test_load_highlight_clips_rejects_invalid_ranges(tmp_path, clips, message) -> None:
    manifest = write_manifest(tmp_path, clips)

    with pytest.raises(ValueError, match=message):
        load_highlight_clips(manifest, video_duration=60.0)


def test_load_highlight_clips_enforces_thirty_second_ceiling(tmp_path) -> None:
    manifest = write_manifest(
        tmp_path,
        [{"start": 0, "end": 20}, {"start": 30, "end": 41}],
    )

    with pytest.raises(ValueError, match="30 seconds"):
        load_highlight_clips(manifest, video_duration=60.0)


def test_load_highlight_clips_honors_smaller_manifest_limit(tmp_path) -> None:
    manifest = write_manifest(
        tmp_path,
        [{"start": 0, "end": 11}],
        max_duration=10,
    )

    with pytest.raises(ValueError, match="10 seconds"):
        load_highlight_clips(manifest, video_duration=60.0)


def test_build_highlight_command_prepends_clips_and_complete_video() -> None:
    command = build_highlight_command(
        "processed.mp4",
        [HighlightClip(40.0, 45.0), HighlightClip(10.0, 14.5)],
        "highlighted.mp4",
        label="Highlights",
        gpu=False,
    )

    filter_graph = command[command.index("-filter_complex") + 1]
    assert command[1:6] == ["-ss", "40", "-t", "5", "-i"]
    assert command[7:12] == ["-ss", "10", "-t", "4.5", "-i"]
    assert "drawtext=text='Highlights'" in filter_graph
    assert "font='Microsoft YaHei'" in filter_graph
    assert "fontsize=72" in filter_graph
    assert "boxcolor=0xFB7299@0.92" in filter_graph
    assert "boxborderw=18" in filter_graph
    assert "concat=n=3:v=1:a=1[vout][aout]" in filter_graph
    assert command[command.index("-c:v") : command.index("-c:v") + 4] == [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
    ]
    assert command[-1] == "highlighted.mp4"


def test_build_highlight_command_can_omit_label() -> None:
    command = build_highlight_command(
        "processed.mp4",
        [HighlightClip(1.0, 4.0)],
        "highlighted.mp4",
        label=None,
        gpu=True,
    )

    filter_graph = command[command.index("-filter_complex") + 1]
    assert "drawtext" not in filter_graph
    assert "format=nv12,hwupload[vout]" in filter_graph


def test_build_highlight_command_uses_independent_inputs_to_avoid_buffering() -> None:
    command = build_highlight_command(
        "processed.mp4",
        [HighlightClip(40.0, 45.0), HighlightClip(10.0, 14.5)],
        "highlighted.mp4",
        gpu=False,
    )

    filter_graph = command[command.index("-filter_complex") + 1]
    assert command.count("-i") == 3
    assert "split=" not in filter_graph
    assert "asplit=" not in filter_graph
    assert "[0:v]" in filter_graph
    assert "[1:v]" in filter_graph
    assert "[2:v]" in filter_graph


def test_create_highlight_video_validates_manifest_before_rendering(
    tmp_path, monkeypatch
) -> None:
    input_video = tmp_path / "processed.mp4"
    input_video.write_bytes(b"video")
    output_video = tmp_path / "highlighted.mp4"
    manifest = write_manifest(tmp_path, [{"start": 2, "end": 6}])
    rendered = []
    monkeypatch.setattr("mvideo.highlights.get_video_duration", lambda _path: 20.0)
    monkeypatch.setattr(
        "mvideo.highlights.create_highlight_video_func",
        lambda *args: rendered.append(args),
    )

    create_highlight_video(
        input_video,
        manifest,
        output_video,
        label="Highlights",
        gpu=False,
    )

    assert rendered == [
        (
            str(input_video),
            [HighlightClip(2.0, 6.0)],
            str(output_video),
            "Highlights",
            False,
        )
    ]


def test_create_highlight_video_refuses_existing_output(tmp_path) -> None:
    input_video = tmp_path / "processed.mp4"
    input_video.write_bytes(b"video")
    output_video = tmp_path / "highlighted.mp4"
    output_video.write_bytes(b"existing")
    manifest = write_manifest(tmp_path, [{"start": 2, "end": 6}])

    with pytest.raises(FileExistsError, match="already exists"):
        create_highlight_video(input_video, manifest, output_video)
