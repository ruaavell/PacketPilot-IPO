"""Command-line interface for Internet Performance Optimizer."""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from ipo import __version__
from ipo.core.measurement.benchmark import run_benchmark
from ipo.core.recommendation import generate_recommendations, RecommendationEngine
from ipo.core.tuner.openwrt_generator import (
    generate_openwrt_config,
    OpenWRTGenerator
)
from ipo.core.utils.json_schema import BenchmarkResult
from ipo.core.utils.logging import setup_logging, get_logger


@click.group()
@click.version_option(version=__version__, prog_name="ipo")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None:
    """
    Internet Performance Optimizer (IPO)
    
    A measurement-first, reversible network optimization tool.
    """
    setup_logging(verbose=verbose)


@cli.command()
@click.option(
    "--target", "-t",
    default="1.1.1.1",
    help="Target host for testing (default: 1.1.1.1)"
)
@click.option(
    "--count", "-c",
    default=1000,
    type=int,
    help="Number of ping samples (default: 1000)"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path (default: auto-generated)"
)
@click.option(
    "--skip-throughput",
    is_flag=True,
    help="Skip throughput/jitter tests (no iperf3 required)"
)
@click.option(
    "--skip-dns",
    is_flag=True,
    help="Skip DNS benchmark"
)
@click.option(
    "--json-only",
    is_flag=True,
    help="Output only JSON (no human-readable summary)"
)
def bench(
    target: str,
    count: int,
    output: Optional[str],
    skip_throughput: bool,
    skip_dns: bool,
    json_only: bool
) -> None:
    """
    Run network performance benchmark.
    
    This will measure:
    - ICMP ping distribution (latency percentiles)
    - UDP jitter and packet loss
    - TCP throughput (download/upload)
    - Bufferbloat (latency under load)
    - DNS resolver performance
    
    Examples:
    
      ipo bench --target 1.1.1.1
      ipo bench --target 8.8.8.8 --count 2000 --output my-bench.json
      ipo bench --skip-throughput  # Skip tests that require iperf3
    """
    logger = get_logger("cli.bench")
    
    if not json_only:
        click.echo(f"🚀 Starting network benchmark (target: {target})")
        click.echo(f"   Ping samples: {count}")
        if skip_throughput:
            click.echo("   ⚠️  Skipping throughput/jitter tests")
        if skip_dns:
            click.echo("   ⚠️  Skipping DNS benchmark")
        click.echo()
    
    try:
        # Run benchmark
        benchmark_result, output_path = run_benchmark(
            target=target,
            ping_count=count,
            skip_throughput=skip_throughput,
            skip_dns=skip_dns,
            output=output
        )
        
        if json_only:
            # Output only JSON
            print(json.dumps(benchmark_result.model_dump(mode='json'), indent=2))
        else:
            # Human-readable summary
            _print_benchmark_summary(benchmark_result)
            click.echo(f"\n✅ Benchmark complete!")
            click.echo(f"📁 Results saved to: {output_path}")
            click.echo(f"\n💡 Generate recommendations: ipo recommend {output_path}")
    
    except Exception as e:
        logger.error(f"Benchmark failed: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


def _print_benchmark_summary(benchmark: BenchmarkResult) -> None:
    """Print human-readable benchmark summary."""
    click.echo("=" * 60)
    click.echo("📊 BENCHMARK RESULTS")
    click.echo("=" * 60)
    
    # ICMP results
    click.echo("\n🏓 ICMP Ping:")
    click.echo(f"   Min:    {benchmark.icmp.min:.1f} ms")
    click.echo(f"   p50:    {benchmark.icmp.p50:.1f} ms")
    click.echo(f"   p90:    {benchmark.icmp.p90:.1f} ms")
    click.echo(f"   p99:    {benchmark.icmp.p99:.1f} ms")
    click.echo(f"   Max:    {benchmark.icmp.max:.1f} ms")
    click.echo(f"   Loss:   {benchmark.icmp.packet_loss:.1f}%")
    
    # Throughput
    if benchmark.throughput.download_mbps > 0:
        click.echo("\n🌐 Throughput:")
        click.echo(f"   Download: {benchmark.throughput.download_mbps:.1f} Mbps")
        click.echo(f"   Upload:   {benchmark.throughput.upload_mbps:.1f} Mbps")
        if benchmark.throughput.retransmits > 0:
            click.echo(f"   ⚠️  Retransmissions: {benchmark.throughput.retransmits}")
    
    # Jitter
    if benchmark.jitter.mean_jitter_ms > 0:
        click.echo("\n📡 Jitter:")
        click.echo(f"   Mean: {benchmark.jitter.mean_jitter_ms:.2f} ms")
        click.echo(f"   Loss: {benchmark.jitter.packet_loss:.1f}%")
    
    # Bufferbloat
    click.echo("\n🌊 Bufferbloat:")
    click.echo(f"   Idle latency:   {benchmark.bufferbloat.idle_latency_ms:.1f} ms")
    click.echo(f"   Loaded latency: {benchmark.bufferbloat.loaded_latency_ms:.1f} ms")
    click.echo(f"   Increase:       +{benchmark.bufferbloat.latency_increase_ms:.1f} ms ({benchmark.bufferbloat.latency_increase_pct:.0f}%)")
    
    # Grade with color
    grade_colors = {
        "A+": "green", "A": "green", "B": "yellow",
        "C": "yellow", "D": "red", "F": "red"
    }
    grade = benchmark.bufferbloat.grade
    click.echo(f"   Grade:          ", nl=False)
    click.secho(f"{grade}", fg=grade_colors.get(grade, "white"), bold=True)
    
    # DNS
    if benchmark.dns:
        click.echo("\n🔍 DNS Resolvers:")
        for dns in benchmark.dns[:3]:  # Top 3
            click.echo(f"   {dns.resolver:20} {dns.median_ms:6.1f} ms (success: {dns.success_rate:.0f}%)")


@cli.command()
@click.argument("benchmark_file", type=click.Path(exists=True))
@click.option(
    "--json-only",
    is_flag=True,
    help="Output only JSON"
)
def recommend(benchmark_file: str, json_only: bool) -> None:
    """
    Generate optimization recommendations from benchmark results.
    
    Examples:
    
      ipo recommend bench_20240216_143000.json
    """
    logger = get_logger("cli.recommend")
    
    try:
        # Load benchmark
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        benchmark = BenchmarkResult(**data)
        
        # Generate recommendations
        engine = RecommendationEngine()
        recommendations = engine.generate(benchmark)
        
        if json_only:
            output = [rec.model_dump(mode='json') for rec in recommendations]
            print(json.dumps(output, indent=2))
        else:
            engine.print_summary(recommendations)
    
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def router() -> None:
    """Router configuration generators."""
    pass


@router.command("openwrt")
@click.option(
    "--download", "-d",
    required=True,
    type=float,
    help="Download speed in Mbps"
)
@click.option(
    "--upload", "-u",
    required=True,
    type=float,
    help="Upload speed in Mbps"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path"
)
@click.option(
    "--interface", "-i",
    default="eth1",
    help="WAN interface name (default: eth1)"
)
@click.option(
    "--margin",
    default=0.95,
    type=float,
    help="Safety margin (default: 0.95 = 95%% of line speed)"
)
@click.option(
    "--show-instructions",
    is_flag=True,
    help="Show usage instructions"
)
def openwrt(
    download: float,
    upload: float,
    output: Optional[str],
    interface: str,
    margin: float,
    show_instructions: bool
) -> None:
    """
    Generate OpenWRT SQM configuration.
    
    This creates a shell script with UCI commands to configure
    Smart Queue Management with CAKE + fq_codel on your OpenWRT router.
    
    Examples:
    
      ipo router openwrt --download 100 --upload 20 --output sqm.sh
      ipo router openwrt -d 250 -u 35 --interface eth0.2
    """
    if show_instructions:
        click.echo(OpenWRTGenerator.get_usage_instructions())
        return
    
    logger = get_logger("cli.router.openwrt")
    
    try:
        click.echo(f"🔧 Generating OpenWRT SQM configuration")
        click.echo(f"   Download: {download} Mbps")
        click.echo(f"   Upload:   {upload} Mbps")
        click.echo(f"   Interface: {interface}")
        click.echo(f"   Margin:   {margin * 100:.0f}%")
        click.echo()
        
        commands = generate_openwrt_config(
            download_mbps=download,
            upload_mbps=upload,
            output=Path(output) if output else None,
            interface=interface,
            margin=margin
        )
        
        if output:
            click.echo(f"✅ Configuration saved to: {output}")
            click.echo(f"\n📋 Next steps:")
            click.echo(f"   1. SSH into your OpenWRT router")
            click.echo(f"   2. Copy the script: {output}")
            click.echo(f"   3. Run the script on your router")
            click.echo(f"\n💡 Show instructions: ipo router openwrt --show-instructions")
        else:
            click.echo("=" * 60)
            click.echo(commands)
            click.echo("=" * 60)
    
    except Exception as e:
        logger.error(f"Failed to generate config: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"Internet Performance Optimizer v{__version__}")
    click.echo("License: MIT")
    click.echo("https://github.com/yourusername/internet-performance-optimizer")


@cli.command()
def info() -> None:
    """Show system and network information."""
    import platform
    import psutil
    
    click.echo("System Information:")
    click.echo(f"  OS: {platform.system()} {platform.release()}")
    click.echo(f"  Python: {platform.python_version()}")
    click.echo(f"  CPU cores: {psutil.cpu_count()}")
    click.echo(f"  Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    
    click.echo("\nNetwork Interfaces:")
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # IPv4
                click.echo(f"  {iface}: {addr.address}")


if __name__ == "__main__":
    cli()
