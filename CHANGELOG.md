# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.1.2] - 2026-08-02

### Added

- Opening highlight reels with reviewed clip selection, subtitle remapping, and a single final render. (@isomoes)
- Post-processing stages for bilingual titles, summaries, chapters, and cover images. (@isomoes)

### Changed

- Publishing now uses a unified staged workflow with automated highlight and subtitle review. (@isomoes)

## [0.1.1] - 2026-08-01

### Added

- Agent-native prompts for audio processing, transcription, subtitles, and the complete publishing workflow. (@isomoes)
- Changelog-backed GitHub Release automation and release preparation instructions. (@isomoes)

### Changed

- The CLI is organized into focused application, FFmpeg, pipeline, subtitle, and transcription modules. (@isomoes)
- CLI documentation now describes the current video publishing workflow and its safety requirements. (@isomoes)
- Release instructions now live with the agent prompts and push the branch and tag atomically. (@isomoes)

### Fixed

- AMD GPU subtitle encoding now initializes and uses the VAAPI device correctly. (@isomoes)

## [0.2.4] - 2026-02-23

### Fixed

- Editor routing works correctly when deployed as a static site on GitHub Pages. (@isomoes)

## [0.2.2] - 2026-02-23

### Fixed

- Web build imports and static export routes work in the GitHub Pages build. (@isomoes)

## [0.2.1] - 2026-02-23

### Changed

- GitHub Pages dependency installation and the Bun lockfile were updated for reliable deployments. (@isomoes)

## [0.2.0] - 2026-02-23

### Added

- OpenCut-based web editor with tag-triggered GitHub Pages deployment. (@isomoes)

## [0.1.0] - 2026-02-22

### Changed

- Project was reset to establish a clean foundation for the next implementation. (@isomoes)
