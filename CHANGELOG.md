# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive database system with SQLite and FTS5 search
- API clients for Gutendex and direct Project Gutenberg integration
- Multi-level caching system for API responses
- Download queue with priority levels
- Terminal UI (TUI) for interactive browsing
- Smart download system with resume capability
- Export functionality to CSV, JSON, Excel and Markdown
- Configuration system with YAML/TOML support
- GitHub Actions CI/CD workflows
- Comprehensive test suite with 84% code coverage
- MIT License
- Contributing guidelines

### Changed
- Refactored downloader to support both sync and async operations
- Improved error handling and reporting
- Enhanced CLI interface with subcommands and options

## [0.1.0] - 2024-05-19

### Added
- Initial release
- Basic scraper for Project Gutenberg
- EPUB downloader
- Book discovery
- CLI interface
- Asynchronous download capabilities

[Unreleased]: https://github.com/williamzujkowski/gutenburg_epubs/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/williamzujkowski/gutenburg_epubs/releases/tag/v0.1.0