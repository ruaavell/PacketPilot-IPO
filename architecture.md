# Architecture Documentation

## Overview

Internet Performance Optimizer (IPO) follows a modular, measurement-first architecture with clear separation between measurement, analysis, recommendation, and application layers.

## Core Principles

1. **Measure First**: All optimizations are based on actual measurements, not assumptions
2. **Reversible**: Every change can be rolled back
3. **Transparent**: All operations are logged and visible to users
4. **Safe**: No silent changes; explicit consent required
5. **Auditable**: All configurations and scripts are generated, not executed directly

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                  CLI / GUI Layer                     │
│  (User Interface - Click CLI, PyQt6 GUI)            │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────┐
│              Orchestration Layer                     │
│  (BenchmarkOrchestrator, workflow coordination)     │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼──┐  ┌───▼────┐  ┌──▼───────┐
│Measurement│  │Recommend│  │ Tuner   │
│  Layer    │  │ Layer   │  │ Layer   │
└───────────┘  └─────────┘  └──────────┘
```

### 1. Measurement Layer

**Location**: `ipo/core/measurement/`

**Purpose**: Collect network performance metrics

**Modules**:
- `ping_distribution.py`: ICMP latency measurement with percentile distribution
- `iperf3_wrapper.py`: TCP throughput and UDP jitter via iperf3
- `dns_bench.py`: DNS resolver performance comparison
- `benchmark.py`: Orchestrates all measurements

**Key Classes**:
- `PingMeasurement`: Runs ICMP pings and computes statistics
- `Iperf3Wrapper`: Wraps iperf3 for throughput/jitter
- `DNSBenchmark`: Tests multiple DNS resolvers
- `BenchmarkOrchestrator`: Coordinates full benchmark

**Data Flow**:
```
User Request → BenchmarkOrchestrator
    ↓
    ├→ PingMeasurement → ICMPResult
    ├→ Iperf3Wrapper → ThroughputResult, JitterResult
    ├→ DNSBenchmark → List[DNSResult]
    └→ Bufferbloat Test → BufferbloatResult
    ↓
BenchmarkResult (validated via Pydantic)
    ↓
JSON file + human summary
```

### 2. Recommendation Layer

**Location**: `ipo/core/recommendation.py`

**Purpose**: Analyze measurements and suggest optimizations

**Key Class**: `RecommendationEngine`

**Rule System**:
```python
if bufferbloat.latency_increase_ms > 100:
    → recommend SQM (confidence: high/medium based on severity)

if icmp.packet_loss > 1.0:
    → recommend investigation (confidence: high if >5%)

if dns_alternative.median_ms < current_dns - 10ms:
    → recommend DNS change (confidence: medium)

if jitter.mean_jitter_ms > 10:
    → recommend jitter reduction (confidence: medium)
```

**Recommendation Schema**:
```python
Recommendation:
    - id: unique identifier
    - title: short description
    - description: detailed explanation
    - confidence: high/medium/low
    - estimated_impact: expected improvement
    - category: Router/NIC/DNS/System
    - commands: list of commands to execute
    - rollback_commands: list of rollback commands
    - requires_admin: bool
    - reversible: bool
    - risk_level: low/medium/high
```

### 3. Tuner Layer

**Location**: `ipo/core/tuner/`

**Purpose**: Generate configuration scripts for network optimizations

**Modules**:
- `openwrt_generator.py`: SQM configuration for OpenWRT
- `powershell_generator.py`: (Future) NIC tuning scripts for Windows
- `mikrotik_generator.py`: (Future) RouterOS scripts

**Key Classes**:
- `OpenWRTGenerator`: Creates UCI commands and config files for SQM

**Design Pattern**:
All tuners follow the **Generator Pattern**:
1. Accept optimization parameters (bandwidth, interface, etc.)
2. Generate human-readable configuration scripts
3. Include verification and rollback commands
4. Output to file (never execute directly)

**Security**: Tuners NEVER execute commands directly. They only generate scripts that users manually review and apply.

### 4. Schema Layer

**Location**: `ipo/core/utils/json_schema.py`

**Purpose**: Define data structures with validation

**Implementation**: Pydantic models with strict validation

**Key Schemas**:
- `ICMPResult`: Ping latency distribution
- `ThroughputResult`: Download/upload speeds
- `JitterResult`: UDP jitter metrics
- `BufferbloatResult`: Latency under load
- `DNSResult`: DNS resolver performance
- `BenchmarkResult`: Complete benchmark (composition of above)
- `Recommendation`: Optimization suggestion
- `ApplyResult`: Result of applying a change

**Benefits**:
- Automatic validation (reject negative latencies, packet loss > 100%, etc.)
- JSON serialization/deserialization
- Type safety
- Self-documenting API

## Data Persistence

### Benchmark Artifacts

**Location**: `%APPDATA%\IPO\benchmarks\` (Windows) or `~/.ipo/benchmarks/` (Unix)

**Format**: JSON with ISO 8601 timestamps

**Naming**: `bench_YYYYMMDD_HHMMSS.json`

**Purpose**:
- Reproducible measurements
- Before/after comparison
- Bug report attachments
- Community benchmarking

### Backups

**Location**: `%APPDATA%\IPO\backups\`

**Structure**:
```
backups/
├── YYYYMMDD_HHMMSS_nic_settings.json  # Settings before change
└── YYYYMMDD_HHMMSS_rollback.ps1      # Rollback script
```

**Retention**: Indefinite (user can delete manually)

### Logs

**Location**: `%APPDATA%\IPO\logs\ipo.log`

**Format**: Rotating log files (10 MB each, 5 backups)

**Levels**:
- DEBUG: Detailed execution flow
- INFO: User-facing operations
- WARNING: Non-fatal issues
- ERROR: Operation failures

## CLI Design

**Framework**: Click (Python)

**Commands**:
```
ipo bench          # Run benchmark
ipo recommend      # Generate recommendations
ipo router         # Router config generators
  ├── openwrt      # OpenWRT SQM
  └── mikrotik     # (Future) MikroTik
ipo tuner          # (Future) NIC tuning
ipo rollback       # (Future) Rollback changes
ipo version        # Show version
ipo info           # System information
```

**Design Principles**:
- Progressive disclosure (simple by default, detailed with flags)
- JSON output mode for scripting
- Verbose mode for debugging
- Consistent error handling

## GUI Design (Future - MVP v0.2)

**Framework**: PyQt6

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ ■ Internet Performance Optimizer                │
├──────────┬──────────────────────────────────────┤
│Dashboard │  📊 Real-time Graphs                 │
│Benchmarks│  ━━━━━━━━━━━━━━━━━                   │
│Recommend │  Latency: 12ms p50, 25ms p99         │
│Router    │  Throughput: 95 Mbps ↓ / 18 Mbps ↑   │
│Settings  │  Bufferbloat: Grade B (75ms)         │
│          │                                       │
│          │  [Measure] [Stop] [Export]            │
├──────────┴──────────────────────────────────────┤
│ Status: Ready | Last bench: 2024-02-16 14:30    │
└─────────────────────────────────────────────────┘
```

**Features**:
- Live graphs during measurement (matplotlib)
- Progress indicators
- Recommendation cards with apply/dismiss
- One-click rollback
- Export to HTML/PDF reports

## Testing Strategy

### Unit Tests

**Framework**: pytest

**Coverage Target**: >80% for core modules

**Key Test Categories**:
1. Schema validation (Pydantic models)
2. Measurement parsing (ping, iperf3 output)
3. Recommendation logic (rule triggers)
4. Configuration generation (OpenWRT, etc.)

**Mocking**: Mock external commands (ping, iperf3) for fast, reproducible tests

### Integration Tests

**Scope**: End-to-end workflows

**Examples**:
```python
def test_bench_to_recommend_workflow():
    """Test: bench → save → load → recommend"""
    benchmark, path = run_benchmark(target="1.1.1.1", count=50)
    with open(path) as f:
        loaded = BenchmarkResult(**json.load(f))
    recommendations = generate_recommendations(loaded)
    assert len(recommendations) > 0
```

### CI/CD Pipeline

**Platform**: GitHub Actions

**Stages**:
1. **Lint**: black, flake8, isort, mypy
2. **Test**: pytest on Ubuntu + Windows, Python 3.9-3.12
3. **Build**: Create wheel
4. **Integration**: Install wheel, run CLI tests

**Artifacts**: Coverage reports, wheel packages

## Security Considerations

### No Direct Execution

**Rule**: IPO NEVER executes system-modifying commands directly

**Implementation**: All tuners generate scripts that users manually review and run

**Rationale**: Prevent privilege escalation, allow user verification

### Privilege Handling

**Windows NIC Tuning**: Requires admin (detected via `ctypes.windll.shell32.IsUserAnAdmin()`)

**Prompts**: Clear warnings before any admin operation

**Logs**: All admin operations logged

### Data Privacy

**No Telemetry**: Default is zero data collection

**Opt-in Only**: If telemetry is added, it must be opt-in with clear disclosure

**PII**: Never collect IP addresses, hostnames, or personally identifiable information

### Dependency Security

**Policy**: Pin major versions, review dependencies regularly

**Scanning**: Dependabot alerts enabled (GitHub)

**Minimal Dependencies**: Keep dependency tree small

## Error Handling

### Graceful Degradation

Example: If iperf3 is not installed:
```python
try:
    throughput = measure_throughput()
except RuntimeError as e:
    logger.warning("iperf3 not available, skipping throughput test")
    throughput = ThroughputResult(download_mbps=0, upload_mbps=0, retransmits=0)
```

### User-Friendly Errors

Bad:
```
Traceback (most recent call last):
  File "ping.py", line 42, in <module>
    result = subprocess.run(...)
CalledProcessError: Command '['ping']' returned non-zero exit status 1
```

Good:
```
❌ Error: Ping test failed
   Target 1.1.1.1 is unreachable. Please check:
   1. Your internet connection
   2. Firewall settings
   3. Target host is valid
```

### Logging Strategy

```python
logger.debug("Executing: ping -n 100 1.1.1.1")  # Detailed
logger.info("Running ICMP benchmark (100 samples)")  # User-facing
logger.warning("iperf3 not found, skipping throughput")  # Degradation
logger.error("Benchmark failed: connection timeout")  # Failure
```

## Future Enhancements

### Phase 2 (v0.3-0.5)
- MikroTik RouterOS integration
- PowerShell NIC tuning with verification
- Long-term monitoring and trending
- Historical comparison (before/after graphs)

### Phase 3 (v0.6+)
- Network path visualization (traceroute + AS lookup)
- Advanced bufferbloat test (concurrent iperf3 + ping)
- Plugin system for custom measurements
- Web dashboard (optional local server)

## Performance Targets

- Benchmark completion: < 60 seconds (1000 pings + throughput + DNS)
- GUI responsiveness: < 100ms for all UI operations
- Memory usage: < 200 MB during benchmark
- JSON artifact size: < 1 MB per benchmark

## Versioning

**Scheme**: Semantic Versioning (semver)

**Format**: MAJOR.MINOR.PATCH

**Example**: v0.1.0 (MVP), v0.2.0 (GUI), v1.0.0 (stable)

**Compatibility**: Benchmark JSON schema is versioned; older formats can be read by newer versions

## License and Contribution

**License**: MIT

**Contributor Agreement**: All contributors agree code is MIT-licensed

**Code Review**: All PRs require approval and passing CI

**Release Process**:
1. Update CHANGELOG.md
2. Tag release: `git tag v0.1.0`
3. GitHub Actions builds and publishes to PyPI (future)
