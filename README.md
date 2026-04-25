# mvideo

A command-line video processing tool for preparing recordings for publishing. It wraps FFmpeg workflows for trimming, audio normalization, background music mixing, subtitle transcription, and hardcoded subtitle rendering.

## Features

- Trim videos by start/end offsets.
- Analyze and normalize audio volume.
- Mix a video with looped background music.
- Transcribe video audio to SRT subtitles with DashScope ASR.
- Burn SRT subtitles into video with FFmpeg.
- Run a full publishing pipeline: trim, normalize, mix, generate subtitles, and optionally burn subtitles.

## Requirements

- Python 3.12+
- `uv`
- FFmpeg and FFprobe available in `PATH`
- Optional NVIDIA encoder support for GPU subtitle burning (`h264_nvenc`)
- DashScope and Alibaba Cloud OSS credentials for transcription commands

## Setup

```bash
make setup
```

Or directly:

```bash
uv sync
```

## Usage

Show CLI help:

```bash
make run args="--help"
```

Run a command:

```bash
uv run main.py <command> [arguments]
```

## Commands

### Analyze Audio

Print detected mean and max volume for a video.

```bash
uv run main.py analyze input.mp4
```

### Normalize Audio

Normalize audio to a target dB level. The default target is `-16.0` dB.

```bash
uv run main.py normalize input.mp4 output.mp4 --target-volume -16
```

### Trim Video

Trim from the start and/or end. Time values can be seconds or `HH:MM:SS`.

This command modifies the input file in place.

```bash
uv run main.py trim input.mp4 00:00:05 10
```

### Mix Background Music

Loop background music to the video duration and mix both audio tracks.

```bash
uv run main.py mix input.mp4 music.mp3 output.mp4 --music-volume 0.3 --video-volume 1.0
```

### Transcribe To SRT

Extract audio from a video, upload it temporarily to OSS, transcribe it with DashScope ASR, and save an SRT file.

```bash
uv run main.py transcribe input.mp4 --output-subtitle input.srt --language zh,en
```

By default, the extracted temporary audio file is removed. Keep it with:

```bash
uv run main.py transcribe input.mp4 --keep-audio
```

### Add Hardcoded Subtitles

Burn an existing SRT file into a video. If no subtitle file is provided, the tool uses the same base path as the video with a `.srt` extension.

```bash
uv run main.py add-subtitles input.mp4 input.srt --output-video output.mp4
```

Use CPU encoding instead of GPU encoding:

```bash
uv run main.py add-subtitles input.mp4 input.srt --no-gpu
```

### Full Process Pipeline

Run the full pipeline: optional trim, audio normalization, optional background music mix, optional SRT generation, and optional subtitle burning.

```bash
uv run main.py process input.mp4 output.mp4 \
  --start-trim 5 \
  --end-trim 10 \
  --background-music music.mp3 \
  --target-volume -16 \
  --music-volume 0.3 \
  --srt \
  --burn-srt \
  --language zh,en
```

When `--burn-srt` is enabled, subtitle generation is automatically enabled. Trimming and subtitle burning are combined in one FFmpeg pass to avoid keyframe alignment issues.

## Transcription Configuration

Transcription requires DashScope and Alibaba Cloud OSS environment variables:

```bash
export DASHSCOPE_API_KEY="your-dashscope-api-key"
export OSS_ACCESS_KEY_ID="your-oss-access-key-id"
export OSS_ACCESS_KEY_SECRET="your-oss-access-key-secret"
export OSS_ENDPOINT="https://oss-cn-hangzhou.aliyuncs.com"
export OSS_BUCKET_NAME="your-bucket-name"
export OSS_REGION="cn-hangzhou"
```

`OSS_REGION` defaults to `cn-hangzhou` if it is not set.

The tool uploads extracted audio to `mvideo/temp/...` in your OSS bucket, sends the public URL to DashScope ASR, and deletes the temporary OSS object after transcription completes.

## Development

Install dependencies:

```bash
make setup
```

Run the CLI:

```bash
make run args="analyze input.mp4"
```

Clean local caches and the virtual environment:

```bash
make clean
```
