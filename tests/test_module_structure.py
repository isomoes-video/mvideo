from typer.testing import CliRunner

from mvideo.cli import app
from mvideo.ffmpeg import build_subtitle_filter


def test_cli_keeps_existing_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "trim",
        "normalize",
        "analyze",
        "mix",
        "process",
        "add-subtitles",
        "transcribe",
    ):
        assert command in result.stdout


def test_main_keeps_ffmpeg_helper_compatibility() -> None:
    from main import build_subtitle_filter as compatibility_helper

    assert compatibility_helper is build_subtitle_filter
