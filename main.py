import json
import os
import random
import re
import shutil
import subprocess
import sys
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import Optional
from urllib import request

import alibabacloud_oss_v2 as oss
import dashscope
import typer
from dashscope.audio.asr import Transcription
from loguru import logger

# Configure loguru to remove default handler and add a new one with a specific format if needed
# But default loguru is usually good enough.
# Let's just use the default configuration which prints to stderr.

app = typer.Typer(help="Video Processor for OBS Recordings and Subtitles")


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
    return []


def video_encoder_args(gpu: bool) -> list[str]:
    """Return ffmpeg video encoder args for AMD GPU or CPU encoding."""
    if gpu:
        return ["-c:v", "h264_vaapi", "-qp", "28"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]


def check_dependencies():
    """Check if ffmpeg is installed."""
    if not shutil.which("ffmpeg"):
        logger.error("FFmpeg is not installed. Please install it first.")
        sys.exit(1)


def parse_time(time_input: str) -> float:
    """Parse time format (HH:MM:SS or seconds) to seconds."""
    if not time_input:
        return 0.0

    # Check if it's HH:MM:SS
    if re.match(r"^\d+:\d+:\d+$", str(time_input)):
        h, m, s = map(int, time_input.split(":"))
        return float(h * 3600 + m * 60 + s)

    # Check if it's just seconds (integer or float string)
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logger.error(f"Could not determine duration for {input_file}")
        sys.exit(1)


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr  # ffmpeg outputs stats to stderr

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


def get_oss_client() -> tuple[oss.Client, str]:
    """Get OSS client and bucket name from environment variables."""
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    endpoint = os.getenv("OSS_ENDPOINT")
    bucket_name = os.getenv("OSS_BUCKET_NAME")

    if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
        logger.error(
            "OSS environment variables not set. Required: "
            "OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET_NAME"
        )
        sys.exit(1)

    credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id, access_key_secret
    )
    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider
    cfg.endpoint = endpoint
    cfg.region = os.getenv("OSS_REGION", "cn-hangzhou")

    client = oss.Client(cfg)
    return client, str(bucket_name)


def upload_file_to_oss(
    file_path: str, object_key: str | None = None
) -> tuple[str, str]:
    """Upload file to OSS and return (object_key, public_url)."""
    client, bucket_name = get_oss_client()

    if object_key is None:
        # Generate unique object key
        file_ext = Path(file_path).suffix
        object_key = f"mvideo/temp/{uuid.uuid4().hex}{file_ext}"

    logger.info(f"Uploading {file_path} to OSS: {object_key}")

    with open(file_path, "rb") as f:
        result = client.put_object(
            oss.PutObjectRequest(
                bucket=bucket_name,
                key=object_key,
                body=f,
            )
        )

    if result.status_code != 200:
        logger.error(f"Failed to upload file to OSS: {result}")
        sys.exit(1)

    # Generate public URL
    endpoint = os.getenv("OSS_ENDPOINT", "")
    # Remove https:// prefix if present for constructing URL
    endpoint_host = endpoint.replace("https://", "").replace("http://", "")
    public_url = f"https://{bucket_name}.{endpoint_host}/{object_key}"

    logger.success(f"File uploaded: {public_url}")
    return object_key, public_url


def delete_oss_file(object_key: str) -> None:
    """Delete file from OSS."""
    client, bucket_name = get_oss_client()

    try:
        client.delete_object(
            oss.DeleteObjectRequest(
                bucket=bucket_name,
                key=object_key,
            )
        )
        logger.info(f"Deleted OSS file: {object_key}")
    except Exception as e:
        logger.warning(f"Failed to delete OSS file {object_key}: {e}")


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


def transcribe_audio_func(
    audio_file: str,
    language_hints: list[str] | None = None,
) -> list[dict]:
    """Transcribe audio file using DashScope ASR SDK."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("DASHSCOPE_API_KEY environment variable is not set")
        sys.exit(1)

    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    if language_hints is None:
        language_hints = ["zh", "en"]

    # Upload audio file to user's OSS bucket
    logger.info("Uploading audio file to OSS...")
    object_key, oss_url = upload_file_to_oss(audio_file)
    logger.info(f"Audio uploaded: {oss_url}")

    try:
        # Start transcription using DashScope SDK
        logger.info("Starting transcription...")
        task_response = Transcription.async_call(
            model="fun-asr",
            file_urls=[oss_url],
            language_hints=language_hints,
        )

        if task_response.status_code != HTTPStatus.OK:
            logger.error(
                f"Failed to start transcription: {task_response.output.message}"
            )
            sys.exit(1)

        logger.info(f"Task created: {task_response.output.task_id}")

        # Wait for transcription to complete
        logger.info("Waiting for transcription to complete...")
        transcription_response = Transcription.wait(task=task_response.output.task_id)

        if transcription_response.status_code != HTTPStatus.OK:
            logger.error(
                f"Transcription failed: {transcription_response.output.message}"
            )
            sys.exit(1)

        logger.success("Transcription completed successfully")

        # Fetch transcription results
        results = []
        for transcription in transcription_response.output.get("results", []):
            if transcription.get("subtask_status") == "SUCCEEDED":
                url = transcription.get("transcription_url")
                if url:
                    result = json.loads(request.urlopen(url).read().decode("utf8"))
                    results.append(result)
            else:
                logger.warning(f"Subtask failed: {transcription}")

        return results
    finally:
        # Clean up OSS file after transcription completes
        delete_oss_file(object_key)


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
                start_time = sentence.get("begin_time", 0) / 1000.0  # ms to seconds
                end_time = sentence.get("end_time", 0) / 1000.0
                text = sentence.get("text", "")

                if not text.strip():
                    continue

                # Format timestamps for SRT (HH:MM:SS,mmm)
                start_srt = format_srt_timestamp(start_time)
                end_srt = format_srt_timestamp(end_time)

                srt_lines.append(str(subtitle_index))
                srt_lines.append(f"{start_srt} --> {end_srt}")
                srt_lines.append(text)
                srt_lines.append("")

                subtitle_index += 1

    return "\n".join(srt_lines)


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_timestamp(timestamp: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
    # Handle both comma and period as decimal separator
    timestamp = timestamp.replace(",", ".")
    parts = timestamp.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def adjust_srt_timestamps(srt_file: str, offset_seconds: float) -> None:
    """Adjust all timestamps in SRT file by subtracting offset_seconds.

    This is needed when trimming video from the start - the SRT timestamps
    are based on the original video, but need to be shifted to match
    the trimmed video.

    Args:
        srt_file: Path to SRT file to modify in-place
        offset_seconds: Seconds to subtract from all timestamps
    """
    if offset_seconds <= 0:
        return

    logger.info(f"Adjusting SRT timestamps by -{offset_seconds}s")

    with open(srt_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse SRT into entries (each entry: index, timestamp, text lines)
    entries = []
    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            # lines[0] = index, lines[1] = timestamp, lines[2:] = text
            timestamp_line = lines[1]
            if " --> " in timestamp_line:
                parts = timestamp_line.split(" --> ")
                if len(parts) == 2:
                    start_time = parse_srt_timestamp(parts[0].strip())
                    end_time = parse_srt_timestamp(parts[1].strip())
                    text = "\n".join(lines[2:])
                    entries.append((start_time, end_time, text))

    # Adjust timestamps and filter out entries before trim point
    adjusted_entries = []
    for start_time, end_time, text in entries:
        new_start = start_time - offset_seconds
        new_end = end_time - offset_seconds

        # Skip subtitles that end before or at the trim point
        if new_end <= 0:
            continue

        # Clamp start to 0 if it's negative
        new_start = max(0, new_start)
        adjusted_entries.append((new_start, new_end, text))

    # Rebuild SRT content with new index numbers
    srt_lines = []
    for idx, (start_time, end_time, text) in enumerate(adjusted_entries, 1):
        srt_lines.append(str(idx))
        srt_lines.append(
            f"{format_srt_timestamp(start_time)} --> {format_srt_timestamp(end_time)}"
        )
        srt_lines.append(text)
        srt_lines.append("")

    # Write back
    with open(srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    logger.success(f"SRT timestamps adjusted: {srt_file}")


def trim_video_func(
    input_file: str, start_trim: str, end_trim: str, output_file: str | None = None
) -> None:
    """Trim video from start/end.

    Args:
        input_file: Path to input video
        start_trim: Trim from start (HH:MM:SS or seconds)
        end_trim: Trim from end (HH:MM:SS or seconds)
        output_file: Output file path (if None, modifies input file in-place for backward compatibility)
    """
    logger.info(f"Trimming video: {input_file}")

    duration = get_video_duration(input_file)
    logger.info(f"Original video duration: {int(duration)} seconds")

    start_seconds = parse_time(start_trim)
    end_seconds_trim = parse_time(end_trim)

    if start_seconds > 0:
        logger.info(f"Trimming {start_seconds} seconds from start")

    if end_seconds_trim > 0:
        logger.info(f"Trimming {end_seconds_trim} seconds from end")

    end_time = duration - end_seconds_trim
    duration_trim = end_time - start_seconds

    if duration_trim <= 0:
        logger.error(
            "Invalid trim parameters. Resulting duration would be negative or zero."
        )
        sys.exit(1)

    logger.info(f"New duration: {duration_trim} seconds")

    # Use provided output file or input file for backward compatibility
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

    # If output_file is different from input_file, move temp to output
    if output_file != input_file:
        shutil.move(temp_file, output_file)
        logger.success(f"Video trimmed successfully: {output_file}")
    else:
        # Replace original file with trimmed version
        shutil.move(temp_file, input_file)
        logger.success(f"Video trimmed successfully: {input_file}")


def normalize_audio_func(
    input_file: str, output_file: str, target_volume: float = -16.0
):
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def burn_subtitles_func(
    input_file: str,
    subtitle_file: str,
    output_file: str,
    gpu: bool = True,
    start_seconds: float = 0,
    duration: float | None = None,
) -> None:
    """Burn subtitles into video with optional trim.

    Combining trim and burn in one ffmpeg pass avoids keyframe alignment issues
    that occur when using stream copy (-c copy) for trimming separately.

    Args:
        input_file: Path to input video
        subtitle_file: Path to SRT subtitle file
        output_file: Path to output video
        gpu: Use AMD GPU acceleration (h264_vaapi)
        start_seconds: Start time in seconds (for trim)
        duration: Duration in seconds (for trim), None means until end
    """
    logger.info(f"Burning subtitles into video: {input_file}")
    if start_seconds > 0 or duration is not None:
        logger.info(f"With trim: start={start_seconds}s, duration={duration}s")

    vf_filter = build_subtitle_filter(subtitle_file, gpu)

    # Build ffmpeg command
    # -fflags +genpts regenerates timestamps to fix keyframe alignment issues
    # from stream-copy trimming, ensuring video plays correctly on YouTube
    cmd = ["ffmpeg", "-fflags", "+genpts"]
    cmd.extend(gpu_acceleration_args(gpu))

    # Add trim start time before input (fast seek)
    if start_seconds > 0:
        cmd.extend(["-ss", str(start_seconds)])

    cmd.extend(["-i", input_file, "-vf", vf_filter])

    # Add duration if specified
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


def mix_with_background_music_func(
    video_file: str,
    background_music: str,
    output_file: str,
    music_volume: float = 0.3,
    video_audio_volume: float = 1.0,
):
    logger.info("Mixing video with background music")
    logger.info(f"Background music volume: {music_volume}")
    logger.info(f"Video audio volume: {video_audio_volume}")

    video_duration = get_video_duration(video_file)

    # Loop background music
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

    # Mix audio tracks
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

    # Cleanup
    if os.path.exists(temp_music):
        os.remove(temp_music)

    logger.success(f"Audio mixed successfully: {output_file}")


@app.callback()
def callback():
    """
    Video Processor for OBS Recordings and Subtitles
    """
    check_dependencies()


@app.command()
def trim(input_video: str, start_trim: str, end_trim: str):
    """Trim video from start/end (modifies original file in-place)."""
    trim_video_func(input_video, start_trim, end_trim)


@app.command()
def normalize(
    input_video: str,
    output_video: str,
    target_volume: float = typer.Option(-16.0, help="Target volume in dB"),
):
    """Normalize audio to a target volume."""
    normalize_audio_func(input_video, output_video, target_volume)


@app.command()
def analyze(input_video: str):
    """Analyze audio volume."""
    analyze_audio_volume_func(input_video)


@app.command()
def mix(
    input_video: str,
    background_music: str,
    output_video: str,
    music_volume: float = typer.Option(0.3, help="Music volume (0.0-1.0)"),
    video_volume: float = typer.Option(1.0, help="Video audio volume (0.0-1.0)"),
):
    """Mix video with background music."""
    mix_with_background_music_func(
        input_video, background_music, output_video, music_volume, video_volume
    )


@app.command()
def process(
    input_video: str,
    output_video: str,
    start_trim: str = typer.Option("0", help="Trim from start (HH:MM:SS or seconds)"),
    end_trim: str = typer.Option("0", help="Trim from end (HH:MM:SS or seconds)"),
    background_music: Optional[str] = typer.Option(None, help="Background music file"),
    target_volume: float = typer.Option(-16.0, help="Target volume in dB"),
    music_volume: float = typer.Option(0.3, help="Music volume"),
    generate_srt: bool = typer.Option(False, "--srt", help="Generate SRT subtitles"),
    burn_srt: bool = typer.Option(
        False, "--burn-srt", help="Burn subtitles into output video"
    ),
    srt_output: Optional[str] = typer.Option(None, help="Output SRT file path"),
    language: str = typer.Option(
        "zh,en", help="Language hints for transcription (comma-separated)"
    ),
    gpu: bool = typer.Option(
        True, help="Use AMD GPU acceleration for subtitle burning"
    ),
):
    """Run full processing pipeline with optional subtitle generation."""
    logger.info("Starting full video processing pipeline...")

    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)

    # If burn_srt is requested, generate_srt must also be enabled
    if burn_srt:
        generate_srt = True

    temp_trimmed = f"temp_trimmed_{random.randint(1000, 9999)}.mp4"
    temp_normalized = f"temp_normalized_{random.randint(1000, 9999)}.mp4"
    temp_audio = f"temp_audio_{random.randint(1000, 9999)}.wav"
    temp_mixed = f"temp_mixed_{random.randint(1000, 9999)}.mp4"

    current_input = input_video

    # Calculate trim parameters for later use
    start_seconds = parse_time(start_trim)
    end_seconds_trim = parse_time(end_trim)
    video_duration = get_video_duration(input_video)
    trim_duration = (
        video_duration - start_seconds - end_seconds_trim
        if (start_seconds > 0 or end_seconds_trim > 0)
        else None
    )

    # Step 1: Trim (only if NOT burning subtitles - otherwise combine with burn step)
    if not burn_srt and (start_trim != "0" or end_trim != "0"):
        trim_video_func(current_input, start_trim, end_trim, temp_trimmed)
        current_input = temp_trimmed

    # Step 2: Normalize
    logger.info("Normalizing video audio...")
    normalize_audio_func(current_input, temp_normalized, target_volume)
    current_input = temp_normalized

    # Step 3: Mix
    if background_music and os.path.exists(background_music):
        mix_with_background_music_func(
            current_input, background_music, temp_mixed, music_volume
        )
    else:
        if background_music:
            logger.warning(
                f"Background music file not found: {background_music}. Copying video..."
            )
        shutil.copy(current_input, temp_mixed)

    # Step 4: Generate SRT subtitles
    srt_file = None
    if generate_srt:
        logger.info("Generating SRT subtitles...")

        # Determine SRT output path
        if srt_output is None:
            filename, _ = os.path.splitext(output_video)
            srt_file = f"{filename}.srt"
        else:
            srt_file = srt_output

        # Extract audio from the intermediate video
        extract_audio_func(temp_normalized, temp_audio)

        # Transcribe audio
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
                    with open(srt_file, "w", encoding="utf-8") as f:
                        f.write(srt_content)
                    logger.success(f"Subtitle file saved: {srt_file}")
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    # Step 5: Burn subtitles into final video (with trim if needed)
    # Combining trim + burn in one ffmpeg pass avoids keyframe alignment issues
    if burn_srt and srt_file and os.path.exists(srt_file):
        # Adjust SRT timestamps when trimming from start
        # SRT was generated from original video, need to shift timestamps
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

    # Cleanup
    for f in [temp_trimmed, temp_normalized, temp_mixed]:
        if os.path.exists(f):
            os.remove(f)

    logger.success(f"Video processing complete: {output_video}")


@app.command()
def add_subtitles(
    input_video: str,
    subtitle_file: Optional[str] = typer.Argument(
        None, help="Subtitle file (default: same path as video, .srt extension)"
    ),
    output_video: Optional[str] = typer.Option(None, help="Output video filename"),
    gpu: bool = typer.Option(True, help="Use AMD GPU acceleration"),
):
    """Add hardcoded subtitles to video with Source Han font."""
    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)

    # Auto-generate subtitle path from input_video if not provided
    if subtitle_file is None:
        filename, _ = os.path.splitext(input_video)
        subtitle_file = f"{filename}.srt"

    if not output_video:
        filename, ext = os.path.splitext(input_video)
        output_video = f"{filename}_with_subs{ext}"

    if not os.path.exists(subtitle_file):
        logger.error(f"Subtitle file not found: {subtitle_file}")
        sys.exit(1)

    logger.info(f"Input video: {input_video}")
    logger.info(f"Subtitle file: {subtitle_file}")
    logger.info(f"Output video: {output_video}")

    vf_filter = build_subtitle_filter(subtitle_file, gpu)

    cmd = ["ffmpeg"]
    cmd.extend(gpu_acceleration_args(gpu))
    cmd.extend(["-i", input_video, "-vf", vf_filter])

    cmd.extend(video_encoder_args(gpu))

    cmd.extend(["-c:a", "copy", "-y", output_video])

    try:
        subprocess.run(cmd, check=True)
        logger.success(f"Success! Output saved to: {output_video}")
    except subprocess.CalledProcessError:
        logger.error("ffmpeg command failed")
        sys.exit(1)


@app.command()
def transcribe(
    input_video: str,
    output_subtitle: Optional[str] = typer.Option(
        None, help="Output SRT subtitle file"
    ),
    language: str = typer.Option(
        "zh,en", help="Language hints (comma-separated, e.g., 'zh,en')"
    ),
    keep_audio: bool = typer.Option(False, help="Keep extracted audio file"),
):
    """Transcribe audio from video to text using DashScope ASR."""
    if not os.path.exists(input_video):
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)

    if not output_subtitle:
        filename, _ = os.path.splitext(input_video)
        output_subtitle = f"{filename}.srt"

    logger.info(f"Input video: {input_video}")
    logger.info(f"Output subtitle: {output_subtitle}")

    # Extract audio
    temp_audio = f"temp_audio_{random.randint(1000, 9999)}.wav"
    extract_audio_func(input_video, temp_audio)

    # Transcribe audio
    language_hints = [lang.strip() for lang in language.split(",")]
    logger.info(f"Language hints: {language_hints}")

    try:
        results = transcribe_audio_func(temp_audio, language_hints)

        if not results:
            logger.error("No transcription results received")
            sys.exit(1)

        # Generate SRT content
        srt_content = generate_srt_from_transcription(results)

        if not srt_content.strip():
            logger.warning("Transcription returned empty results")
        else:
            with open(output_subtitle, "w", encoding="utf-8") as f:
                f.write(srt_content)
            logger.success(f"Subtitle file saved: {output_subtitle}")

    finally:
        # Cleanup
        if not keep_audio and os.path.exists(temp_audio):
            os.remove(temp_audio)
        elif keep_audio:
            logger.info(f"Audio file kept: {temp_audio}")


if __name__ == "__main__":
    app()
