# Quick Start Guide

Get started with Internet Performance Optimizer in 5 minutes!

## Installation

### Prerequisites
- Windows 10/11, Linux, or macOS
- Python 3.9 or higher
- (Optional) iperf3 for throughput tests

### Install IPO

```bash
# Clone repository
git clone https://github.com/yourusername/internet-performance-optimizer.git
cd internet-performance-optimizer

# Install
pip install -e .

# Verify installation
ipo --version
```

## Your First Benchmark

Run a quick network benchmark:

```bash
ipo bench --target 1.1.1.1
```

This will:
1. Run 1000 ICMP pings
2. Measure jitter and throughput (if iperf3 available)
3. Test for bufferbloat
4. Compare DNS resolvers
5. Save results to JSON

**Output example**:
```
🚀 Starting network benchmark (target: 1.1.1.1)
   Ping samples: 1000

============================================================
📊 BENCHMARK RESULTS
============================================================

🏓 ICMP Ping:
   Min:    8.1 ms
   p50:    12.3 ms
   p90:    18.5 ms
   p99:    45.2 ms
   Max:    120.5 ms
   Loss:   0.2%

🌐 Throughput:
   Download: 95.3 Mbps
   Upload:   18.2 Mbps

🌊 Bufferbloat:
   Idle latency:   12.5 ms
   Loaded latency: 25.3 ms
   Increase:       +12.8 ms (102%)
   Grade:          A

✅ Benchmark complete!
📁 Results saved to: C:\Users\You\AppData\Roaming\IPO\benchmarks\bench_20240216_143000.json
```

## Get Recommendations

Generate optimization recommendations from your benchmark:

```bash
ipo recommend bench_20240216_143000.json
```

**Example output**:
```
📊 Found 2 optimization opportunities:

1. 🟢 Use Faster DNS Resolver (1.1.1.1)
   Category: DNS | Confidence: MEDIUM
   Impact: Reduce DNS lookup time to ~8ms
   Risk: low | Reversible: Yes

2. 🟡 Enable Receive Side Scaling (RSS) on Network Adapter
   Category: NIC | Confidence: MEDIUM
   Impact: Potential 10-30% throughput improvement on fast connections
   Risk: low | Reversible: Yes
   ⚠️  Requires administrator privileges
```

## Fix Bufferbloat (If Detected)

If your benchmark shows high bufferbloat (grade C or worse):

### Step 1: Generate OpenWRT Config

```bash
# Replace with your actual speeds
ipo router openwrt --download 100 --upload 20 --output sqm.sh
```

### Step 2: Apply to Router

```bash
# SSH into your OpenWRT router
ssh root@192.168.1.1

# Upload and run the script
# (copy contents of sqm.sh and paste into router shell)
```

### Step 3: Verify Improvement

```bash
# Run benchmark again
ipo bench --target 1.1.1.1 --output after-sqm.json

# Compare results
# Your bufferbloat grade should improve significantly!
```

## Common Use Cases

### Quick Test (No iperf3 needed)

```bash
ipo bench --target 1.1.1.1 --skip-throughput --skip-dns --count 100
```

### Export to JSON for Scripting

```bash
ipo bench --target 1.1.1.1 --json-only > results.json
```

### Custom Target and Sample Size

```bash
ipo bench --target 8.8.8.8 --count 2000 --output my-bench.json
```

### Show System Information

```bash
ipo info
```

## Interpreting Results

### Bufferbloat Grades

- **A+**: Excellent (< 10ms increase under load)
- **A**: Very Good (10-30ms)
- **B**: Good (30-100ms)
- **C**: Fair (100-200ms) - **Consider SQM**
- **D**: Poor (200-400ms) - **SQM recommended**
- **F**: Bad (> 400ms) - **SQM strongly recommended**

### Packet Loss

- **< 0.5%**: Excellent
- **0.5-1%**: Good
- **1-3%**: Fair - investigate further
- **> 3%**: Poor - check cables, ISP issues

### Jitter

- **< 5ms**: Excellent for gaming/VoIP
- **5-10ms**: Good
- **10-20ms**: Fair - may affect real-time apps
- **> 20ms**: Poor - enable QoS/SQM

## Troubleshooting

### "iperf3 not found"

**Solution**: Skip throughput tests or install iperf3:

```bash
# Windows: Download from https://iperf.fr/iperf-download.php
# Linux: sudo apt install iperf3
# macOS: brew install iperf3

# Or skip these tests:
ipo bench --target 1.1.1.1 --skip-throughput
```

### "Permission denied"

**Solution**: Run as administrator (Windows) or with sudo (Linux):

```bash
# Windows: Right-click terminal → "Run as administrator"
# Linux: sudo ipo bench --target 1.1.1.1
```

### High bufferbloat but fast connection

This is common! Bufferbloat is not about speed, it's about queue management. Your connection can be fast but still have terrible latency under load.

**Solution**: Implement SQM on your router (see above).

## Next Steps

1. **Run regular benchmarks** to monitor your connection quality
2. **Compare before/after** when making network changes
3. **Share results** in bug reports or community forums
4. **Star the repo** on GitHub if you find it useful!

## Getting Help

- **Documentation**: Check `/docs` folder
- **Issues**: https://github.com/yourusername/internet-performance-optimizer/issues
- **Examples**: Check `/examples` folder for sample configs and benchmarks

## Advanced Usage

### Custom DNS Resolvers

Edit `ipo/core/measurement/dns_bench.py` to add custom resolvers.

### Automated Monitoring

```bash
# Run benchmark every hour and log
while true; do
  ipo bench --target 1.1.1.1 --output "bench_$(date +%Y%m%d_%H%M%S).json"
  sleep 3600
done
```

### Integration with Scripts

```python
from ipo.core.measurement.benchmark import run_benchmark

# Run programmatically
result, path = run_benchmark(
    target="1.1.1.1",
    ping_count=500,
    skip_throughput=True
)

print(f"p99 latency: {result.icmp.p99}ms")
print(f"Bufferbloat grade: {result.bufferbloat.grade}")
```

Happy optimizing! 🚀
