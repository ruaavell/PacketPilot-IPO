# Internet Performance Optimizer (IPO)

A **measurement-first**, **reversible**, and **safe** network optimization tool for Windows users with router integration features.

## ⚠️ Core Principles

- **Measure First**: All optimizations are based on actual network measurements, not blind registry tweaks
- **Reversible**: Every change can be rolled back with one click
- **Transparent**: All commands shown before execution; full audit trail
- **No Snake Oil**: No placebo optimizations or unverifiable claims
- **Ethical**: No permanent security feature disabling, no telemetry without consent

## What This Tool Does

1. **Measures** your network performance (latency distribution, jitter, packet loss, throughput, bufferbloat)
2. **Recommends** evidence-based optimizations (NIC tuning, router SQM configuration, DNS optimization)
3. **Applies** changes safely with explicit consent and automatic backup
4. **Reports** before/after results with exportable artifacts

## What This Tool Does NOT Do

- ❌ Apply blind registry tweaks without measurement
- ❌ Permanently disable Windows Update or security features
- ❌ Install unsigned kernel drivers
- ❌ Make claims about "instant ping reduction" without proof
- ❌ Collect telemetry without explicit opt-in

## Installation

### Prerequisites

- Windows 10 or 11 (x64)
- Python 3.9 or higher
- Administrator privileges (for applying NIC changes)
- iperf3 (automatically downloaded if missing)

### Via pip

```bash
pip install internet-performance-optimizer
```

### From source

```bash
git clone https://github.com/yourusername/internet-performance-optimizer.git
cd internet-performance-optimizer
pip install -e .
```

## Quick Start

### CLI Usage

```bash
# Run basic benchmark
ipo bench --target 1.1.1.1

# Full benchmark with custom packet count
ipo bench --target 8.8.8.8 --count 2000 --output my-bench.json

# Generate recommendations from benchmark
ipo recommend my-bench.json

# View available NIC tuning options
ipo tuner list-nics

# Export router configuration
ipo router openwrt --download 100 --upload 20 --output sqm-config.sh
```

### GUI Usage

```bash
# Launch GUI
ipo gui
```

The GUI provides:
- Real-time network performance graphs
- Visual recommendation engine
- One-click apply/rollback functionality
- Export reports as HTML/JSON/CSV

## Benchmark Metrics

IPO measures:

1. **RTT Distribution**: p50, p90, p95, p99 latencies via ICMP
2. **Jitter**: UDP packet timing variance via iperf3
3. **Throughput**: TCP bandwidth via iperf3
4. **Bufferbloat**: Latency under load test
5. **DNS Performance**: Resolver comparison (Cloudflare, Google, current)

All measurements produce reproducible JSON artifacts.

## Example Benchmark Output

```json
{
  "timestamp": "2024-02-16T14:30:00Z",
  "target": "1.1.1.1",
  "icmp": {
    "samples": 1000,
    "p50": 12.3,
    "p90": 18.7,
    "p95": 22.1,
    "p99": 45.2,
    "packet_loss": 0.2
  },
  "bufferbloat": {
    "idle_latency_ms": 12.5,
    "loaded_latency_ms": 156.3,
    "grade": "C"
  },
  "throughput": {
    "download_mbps": 95.3,
    "upload_mbps": 18.2
  }
}
```

## Router Support

### OpenWRT

Generates complete SQM (Smart Queue Management) configuration with CAKE + fq_codel:

```bash
ipo router openwrt --download 100 --upload 20 --output sqm.sh
# Upload sqm.sh to your router and run
```

### MikroTik

Exports RouterOS script with queue trees:

```bash
ipo router mikrotik --download 100 --upload 20 --output config.rsc
# Import via: /import file=config.rsc
```

## NIC Tuning (Windows)

IPO can optimize network adapter settings via PowerShell. All changes:

- ✅ Require explicit admin consent
- ✅ Show exact commands before execution
- ✅ Create automatic backups
- ✅ Provide one-click rollback

Common optimizations:
- Enable RSS (Receive Side Scaling)
- Adjust interrupt moderation
- Configure offload features
- Optimize receive buffers

## Safety Features

### Backup & Restore

Every change creates a timestamped backup:

```
%APPDATA%\IPO\backups\
  2024-02-16_143000_nic_settings.json
  2024-02-16_143000_rollback.ps1
```

Rollback via GUI or CLI:

```bash
ipo rollback --backup-id 2024-02-16_143000
```

### Change Verification

After applying changes, IPO verifies:
1. Setting was actually changed
2. System is stable
3. Network connectivity maintained

Failed verifications trigger automatic rollback.

## Known Limitations

- Requires administrator privileges for NIC changes
- iperf3 throughput tests need a public iperf3 server
- Router configuration requires manual upload (cannot auto-apply to router)
- Some NIC features are driver/hardware dependent

## Reporting Issues

When reporting issues, please include:

1. Your benchmark artifact: `ipo bench --target 1.1.1.1 --output issue.json`
2. System info: `ipo sysinfo --output sysinfo.json`
3. IPO version: `ipo --version`
4. Steps to reproduce

## Security Disclosure

Found a security issue? Email: security@example.com

Do NOT open public issues for security vulnerabilities.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

All contributors must agree to:
- Code review process
- Test coverage requirements
- Security-first mindset
- No telemetry without opt-in

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- OpenWRT project for SQM documentation
- iperf3 for measurement tools
- The bufferbloat.net community

## Roadmap

- [x] MVP v0.1: CLI benchmark tool
- [ ] MVP v0.2: PyQt6 GUI with apply/rollback
- [ ] v0.3: MikroTik RouterOS integration
- [ ] v0.4: Network path visualization
- [ ] v0.5: Long-term monitoring and trending

---

**Remember**: Measure first, optimize second. No placebo fixes.
