# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- (placeholder)

### Changed
- (placeholder)

### Fixed
- (placeholder)

## [0.1.2] - 2025-08-25
### Added
- Initial PyPI packaging metadata (classifiers, keywords, optional extras).
- Logging for JSONL retention and persistence failures.
- Ruff lint clean state enforcement.

### Changed
- Refactored long lines and ambiguous characters for lint compliance.

### Fixed
- Strict base64url decode validation (raises on invalid chars) improving error determinism.

## [0.1.0] - 2025-08-25
### Added
- Core library: signing (Ed25519), canonical JSON, usage metering (JSONL + optional SQLite), export + verify helpers.
- FastAPI service with usage recording, export, Stripe billing stubs.
- CLI `omb-cli` with record/export/verify commands.
- Unit tests for signing, export, tamper detection, time windows.
- CI workflow (tests, lint, build, TestPyPI publish on tag).
- SECURITY.md and example usage script.

### Changed
- N/A

### Fixed
- N/A

[Unreleased]: https://github.com/odin-org/omb/compare/omb-v0.1.2...HEAD
[0.1.2]: https://github.com/odin-org/omb/compare/omb-v0.1.0...omb-v0.1.2
[0.1.0]: https://github.com/odin-org/omb/releases/tag/omb-v0.1.0
