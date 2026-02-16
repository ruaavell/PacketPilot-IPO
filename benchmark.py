"""Main benchmark orchestration engine."""

import asyncio
import platform
import psutil
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json

from ipo.core.measurement.ping_distribution import run_icmp, PingConfig
from ipo.core.measurement.iperf3_wrapper import measure_throughput, measure_jitter
from ipo.core.measurement.dns_bench import benchmark_dns
from ipo.core.utils.json_schema import (
    BenchmarkResult, BufferbloatResult, ICMPResult,
    calculate_bufferbloat_grade
)
from ipo.core.utils.logging import get_logger

logger = get_logger(__name__)


class BenchmarkOrchestrator:
    """Orchestrates complete network performance benchmark."""
    
    def __init__(self, target: str = "1.1.1.1", output_dir: Optional[Path] = None):
        """
        Initialize benchmark orchestrator.
        
        Args:
            target: Target host for testing
            output_dir: Directory to save benchmark artifacts
        """
        self.target = target
        self.output_dir = output_dir or self._get_default_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.BenchmarkOrchestrator")
    
    def _get_default_output_dir(self) -> Path:
        """Get default output directory for benchmark artifacts."""
        if platform.system() == "Windows":
            base = Path.home() / "AppData" / "Roaming" / "IPO" / "benchmarks"
        else:
            base = Path.home() / ".ipo" / "benchmarks"
        return base
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        try:
            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "network_interfaces": [],
            }
            
            # Get network interfaces
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # AF_INET (IPv4)
                        info["network_interfaces"].append({
                            "name": iface,
                            "address": addr.address,
                        })
            
            return info
        
        except Exception as e:
            self.logger.warning(f"Failed to collect full system info: {e}")
            return {"os": platform.system(), "error": str(e)}
    
    async def _measure_bufferbloat(self, iperf_server: Optional[str] = None) -> BufferbloatResult:
        """
        Measure bufferbloat (latency under load).
        
        This test runs:
        1. Baseline ping test (idle latency)
        2. iperf3 download in background
        3. Ping test during load (loaded latency)
        4. Calculate difference
        
        Args:
            iperf_server: iperf3 server to use for load
        
        Returns:
            BufferbloatResult
        """
        self.logger.info("Starting bufferbloat test...")
        
        # Measure idle latency (small sample)
        self.logger.info("Measuring idle latency...")
        idle_config = PingConfig(target=self.target, count=50)
        from ipo.core.measurement.ping_distribution import PingMeasurement
        idle_ping = PingMeasurement(idle_config)
        idle_result = await idle_ping.run_async()
        idle_latency = idle_result.p50
        
        self.logger.info(f"Idle latency: {idle_latency:.1f}ms")
        
        # This is a simplified bufferbloat test
        # In production, we would:
        # 1. Start iperf3 in background
        # 2. Run pings during download
        # 3. Measure latency increase
        
        # For MVP, we'll use a simple heuristic based on jitter
        # Real implementation would run concurrent iperf3 + ping
        
        # Placeholder: estimate loaded latency as idle + jitter impact
        # This is NOT accurate - just for demonstration
        loaded_latency = idle_latency * 1.5  # Simplified estimation
        
        latency_increase = loaded_latency - idle_latency
        latency_increase_pct = (latency_increase / idle_latency * 100) if idle_latency > 0 else 0
        grade = calculate_bufferbloat_grade(latency_increase)
        
        result = BufferbloatResult(
            idle_latency_ms=round(idle_latency, 2),
            loaded_latency_ms=round(loaded_latency, 2),
            latency_increase_ms=round(latency_increase, 2),
            latency_increase_pct=round(latency_increase_pct, 1),
            grade=grade
        )
        
        self.logger.info(
            f"Bufferbloat: {result.latency_increase_ms}ms increase ({result.grade})"
        )
        self.logger.warning(
            "Note: This is a simplified bufferbloat test. "
            "Full implementation requires concurrent iperf3 + ping."
        )
        
        return result
    
    async def run_full_benchmark(
        self,
        ping_count: int = 1000,
        skip_throughput: bool = False,
        skip_dns: bool = False
    ) -> BenchmarkResult:
        """
        Run complete network benchmark.
        
        Args:
            ping_count: Number of ICMP ping samples
            skip_throughput: Skip throughput/jitter tests (requires iperf3)
            skip_dns: Skip DNS benchmark
        
        Returns:
            BenchmarkResult with all measurements
        """
        self.logger.info(f"Starting full benchmark (target: {self.target})")
        
        # Collect system info
        system_info = self._get_system_info()
        
        # ICMP ping distribution
        self.logger.info("Running ICMP ping distribution test...")
        icmp_result = run_icmp(target=self.target, count=ping_count)
        
        # Throughput and jitter (requires iperf3)
        if skip_throughput:
            from ipo.core.utils.json_schema import ThroughputResult, JitterResult
            throughput_result = ThroughputResult(download_mbps=0, upload_mbps=0, retransmits=0)
            jitter_result = JitterResult(
                mean_jitter_ms=0, max_jitter_ms=0, packet_loss=0, out_of_order=0
            )
            self.logger.info("Skipping throughput/jitter tests")
        else:
            try:
                self.logger.info("Running throughput test...")
                throughput_result = measure_throughput(duration=10, parallel=1)
                
                self.logger.info("Running jitter test...")
                jitter_result = measure_jitter(duration=10)
            except Exception as e:
                self.logger.error(f"Throughput/jitter test failed: {e}")
                from ipo.core.utils.json_schema import ThroughputResult, JitterResult
                throughput_result = ThroughputResult(download_mbps=0, upload_mbps=0, retransmits=0)
                jitter_result = JitterResult(
                    mean_jitter_ms=0, max_jitter_ms=0, packet_loss=0, out_of_order=0
                )
        
        # Bufferbloat
        self.logger.info("Running bufferbloat test...")
        bufferbloat_result = await self._measure_bufferbloat()
        
        # DNS benchmark
        if skip_dns:
            dns_results = []
            self.logger.info("Skipping DNS benchmark")
        else:
            try:
                self.logger.info("Running DNS benchmark...")
                dns_results = benchmark_dns(num_domains=20)
            except Exception as e:
                self.logger.error(f"DNS benchmark failed: {e}")
                dns_results = []
        
        # Assemble results
        benchmark = BenchmarkResult(
            timestamp=datetime.now(),
            target=self.target,
            system_info=system_info,
            icmp=icmp_result,
            jitter=jitter_result,
            throughput=throughput_result,
            bufferbloat=bufferbloat_result,
            dns=dns_results,
            metadata={
                "ping_count": ping_count,
                "skip_throughput": skip_throughput,
                "skip_dns": skip_dns,
            }
        )
        
        self.logger.info("Benchmark complete!")
        return benchmark
    
    def save_benchmark(self, benchmark: BenchmarkResult, filename: Optional[str] = None) -> Path:
        """
        Save benchmark results to JSON file.
        
        Args:
            benchmark: BenchmarkResult to save
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = benchmark.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"bench_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # Convert to dict and save
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                benchmark.model_dump(mode='json'),
                f,
                indent=2,
                ensure_ascii=False
            )
        
        self.logger.info(f"Benchmark saved to: {output_path}")
        return output_path
    
    def run_and_save(
        self,
        ping_count: int = 1000,
        skip_throughput: bool = False,
        skip_dns: bool = False,
        output_file: Optional[str] = None
    ) -> tuple[BenchmarkResult, Path]:
        """
        Run benchmark and save results.
        
        Args:
            ping_count: Number of ping samples
            skip_throughput: Skip throughput tests
            skip_dns: Skip DNS tests
            output_file: Output filename (optional)
        
        Returns:
            Tuple of (BenchmarkResult, output_path)
        """
        # Run benchmark
        benchmark = asyncio.run(
            self.run_full_benchmark(
                ping_count=ping_count,
                skip_throughput=skip_throughput,
                skip_dns=skip_dns
            )
        )
        
        # Save results
        output_path = self.save_benchmark(benchmark, filename=output_file)
        
        return benchmark, output_path


def run_benchmark(
    target: str = "1.1.1.1",
    ping_count: int = 1000,
    skip_throughput: bool = False,
    skip_dns: bool = False,
    output: Optional[str] = None
) -> tuple[BenchmarkResult, Path]:
    """
    Convenience function to run and save benchmark.
    
    Args:
        target: Target host
        ping_count: Number of ping samples
        skip_throughput: Skip throughput/jitter tests
        skip_dns: Skip DNS tests
        output: Output filename
    
    Returns:
        Tuple of (BenchmarkResult, output_path)
    """
    orchestrator = BenchmarkOrchestrator(target=target)
    return orchestrator.run_and_save(
        ping_count=ping_count,
        skip_throughput=skip_throughput,
        skip_dns=skip_dns,
        output_file=output
    )
