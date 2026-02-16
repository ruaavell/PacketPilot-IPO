# Changelog

All notable changes to Internet Performance Optimizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- PyQt6 GUI with real-time graphs
- MikroTik RouterOS config generator
- PowerShell NIC tuning with verification
- One-click rollback functionality
- Long-term monitoring and trending

## [0.1.0] - 2024-02-16

### Added
- **MVP v0.1** - CLI benchmark tool
- ICMP ping distribution measurement with percentiles (p50, p90, p95, p99)
- UDP jitter testing via iperf3
- TCP throughput measurement (download/upload)
- Bufferbloat detection (latency under load)
- DNS resolver performance comparison (Cloudflare, Google)
- Rule-based recommendation engine
- OpenWRT SQM configuration generator with CAKE + fq_codel
- JSON/CSV export of benchmark results
- Comprehensive logging system
- Unit tests with pytest
- GitHub Actions CI/CD pipeline
- Security-first architecture (no direct command execution)
- Full documentation (README, ARCHITECTURE, SECURITY, CONTRIBUTING)

### Features

#### Measurement Engine
- Statistically-sound ICMP ping sampling (configurable count)
- Automatic percentile calculation (p50, p90, p95, p99)
- Packet loss detection
- Jitter measurement with iperf3 integration
- Throughput testing with automatic server selection
- Bufferbloat grading (A+ through F)
- Multi-resolver DNS benchmarking

#### Recommendation Engine
- Bufferbloat-based SQM recommendations
- Confidence levels (high/medium/low)
- Estimated impact descriptions
- Complete rollback instructions
- DNS optimization suggestions
- Packet loss investigation guidance
- NIC tuning recommendations (Windows)

#### Router Integration
- OpenWRT SQM UCI command generator
- Configurable safety margins (default 95%)
- Protocol overhead adaptation (PPPoE, cable, etc.)
- Interface selection
- CAKE qdisc with optimal parameters
- Detailed installation instructions

#### CLI Interface
- `ipo bench`: Run network benchmark
- `ipo recommend`: Generate optimization suggestions
- `ipo router openwrt`: Create OpenWRT SQM config
- `ipo version`: Show version information
- `ipo info`: Display system information
- JSON output mode for scripting
- Verbose logging option

#### Data Management
- Pydantic-based schema validation
- Automatic timestamp and versioning
- Reproducible benchmark artifacts
- JSON export with full metadata
- Example benchmark files included

#### Testing
- 50+ unit tests
- Integration test workflows
- Schema validation tests
- Recommendation logic tests
- Mock-based testing for external tools
- CI/CD with GitHub Actions

#### Documentation
- Comprehensive README with examples
- Architecture documentation
- Security policy and guidelines
- Contributing guidelines
- Example configurations
- Code of conduct

### Security
- No direct command execution (generate-only)
- Input validation and sanitization
- No shell=True with user input
- Path traversal prevention
- No telemetry or PII collection
- Explicit consent for all changes
- Reversible operations with backup
- Security vulnerability disclosure process

### Dependencies
- click >= 8.0.0 (CLI framework)
- psutil >= 5.9.0 (system information)
- pydantic >= 2.0.0 (data validation)
- ping3 >= 4.0.0 (ICMP fallback)
- requests >= 2.28.0 (HTTP client)
- rich >= 13.0.0 (terminal formatting)

### Development Dependencies
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- black >= 23.0.0
- flake8 >= 6.0.0
- mypy >= 1.0.0
- isort >= 5.12.0

### Known Limitations
- Requires iperf3 for throughput/jitter (external dependency)
- Bufferbloat test is simplified (concurrent iperf3+ping in future)
- No GUI yet (planned for v0.2)
- No automated NIC tuning application (generate-only for safety)
- Router configs must be manually applied
- Windows-only NIC recommendations currently

### Platform Support
- Windows 10/11 (primary)
- Linux (tested on Ubuntu 20.04+)
- macOS (basic support, not heavily tested)

## [0.0.1] - 2024-02-01

### Added
- Initial project structure
- Basic README and LICENSE

---

## Release Notes Format

Each release includes:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

## Version Numbering

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

Example: v0.1.0 → v0.2.0 (new feature) → v0.2.1 (bug fix) → v1.0.0 (stable API)
