from loguru import logger


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_timestamp(timestamp: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
    timestamp = timestamp.replace(",", ".")
    parts = timestamp.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def generate_srt_from_transcription(transcription_results: list[dict]) -> str:
    """Generate SRT content from transcription results."""
    srt_lines = []
    subtitle_index = 1

    for result in transcription_results:
        if "transcripts" not in result:
            continue
        for transcript in result["transcripts"]:
            if "sentences" not in transcript:
                continue
            for sentence in transcript["sentences"]:
                start_time = sentence.get("begin_time", 0) / 1000.0
                end_time = sentence.get("end_time", 0) / 1000.0
                text = sentence.get("text", "")
                if not text.strip():
                    continue

                srt_lines.append(str(subtitle_index))
                srt_lines.append(
                    f"{format_srt_timestamp(start_time)} --> "
                    f"{format_srt_timestamp(end_time)}"
                )
                srt_lines.append(text)
                srt_lines.append("")
                subtitle_index += 1

    return "\n".join(srt_lines)


def adjust_srt_timestamps(srt_file: str, offset_seconds: float) -> None:
    """Subtract an offset from all timestamps in an SRT file."""
    if offset_seconds <= 0:
        return

    logger.info(f"Adjusting SRT timestamps by -{offset_seconds}s")
    with open(srt_file, encoding="utf-8") as file:
        content = file.read()

    entries = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        parts = lines[1].split(" --> ")
        if len(parts) != 2:
            continue
        entries.append(
            (
                parse_srt_timestamp(parts[0].strip()),
                parse_srt_timestamp(parts[1].strip()),
                "\n".join(lines[2:]),
            )
        )

    adjusted_entries = []
    for start_time, end_time, text in entries:
        new_start = start_time - offset_seconds
        new_end = end_time - offset_seconds
        if new_end <= 0:
            continue
        adjusted_entries.append((max(0, new_start), new_end, text))

    srt_lines = []
    for index, (start_time, end_time, text) in enumerate(adjusted_entries, 1):
        srt_lines.append(str(index))
        srt_lines.append(
            f"{format_srt_timestamp(start_time)} --> {format_srt_timestamp(end_time)}"
        )
        srt_lines.append(text)
        srt_lines.append("")

    with open(srt_file, "w", encoding="utf-8") as file:
        file.write("\n".join(srt_lines))
    logger.success(f"SRT timestamps adjusted: {srt_file}")
