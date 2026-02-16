"""ICMP ping distribution measurement."""

import statistics
import asyncio
import platform
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import re
import logging

from ipo.core.utils.json_schema import ICMPResult
from ipo.core.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PingConfig:
    """Configuration for ping tests."""
    target: str
    count: int = 1000
    timeout: int = 2
    packet_size: int = 32
    interval: float = 0.01  # 10ms between pings for speed


class PingMeasurement:
    """ICMP ping distribution measurement engine."""
    
    def __init__(self, config: PingConfig):
        """
        Initialize ping measurement.
        
        Args:
            config: Ping configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.PingMeasurement")
    
    async def run_async(self) -> ICMPResult:
        """
        Run async ping measurement.
        
        Returns:
            ICMPResult with latency distribution
        """
        self.logger.info(f"Starting ICMP measurement to {self.config.target} ({self.config.count} samples)")
        
        if platform.system() == "Windows":
            return await self._run_windows_ping()
        else:
            return await self._run_unix_ping()
    
    def run(self) -> ICMPResult:
        """
        Run synchronous ping measurement.
        
        Returns:
            ICMPResult with latency distribution
        """
        return asyncio.run(self.run_async())
    
    async def _run_windows_ping(self) -> ICMPResult:
        """Run ping on Windows using built-in ping command."""
        samples: List[float] = []
        failures = 0
        
        # Windows ping is synchronous, run in batches
        batch_size = 100
        batches = (self.config.count + batch_size - 1) // batch_size
        
        for batch in range(batches):
            current_count = min(batch_size, self.config.count - batch * batch_size)
            
            try:
                cmd = [
                    "ping",
                    "-n", str(current_count),
                    "-l", str(self.config.packet_size),
                    "-w", str(self.config.timeout * 1000),  # Windows uses ms
                    self.config.target
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout * current_count + 10
                )
                
                # Parse Windows ping output
                # Example: "Reply from 1.1.1.1: bytes=32 time=12ms TTL=57"
                for line in result.stdout.split('\n'):
                    match = re.search(r'time[=<](\d+)ms', line)
                    if match:
                        latency = float(match.group(1))
                        samples.append(latency)
                    elif 'Request timed out' in line or 'Destination host unreachable' in line:
                        failures += 1
                
                self.logger.debug(f"Batch {batch + 1}/{batches}: {len(samples)} samples, {failures} failures")
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Ping batch {batch + 1} timed out")
                failures += current_count
            except Exception as e:
                self.logger.error(f"Error in ping batch {batch + 1}: {e}")
                failures += current_count
        
        return self._compute_statistics(samples, failures)
    
    async def _run_unix_ping(self) -> ICMPResult:
        """Run ping on Unix-like systems."""
        samples: List[float] = []
        failures = 0
        
        try:
            # Use -i 0.01 for 10ms interval (requires root on some systems)
            cmd = [
                "ping",
                "-c", str(self.config.count),
                "-s", str(self.config.packet_size),
                "-W", str(self.config.timeout),
                "-i", "0.2",  # 200ms interval to avoid rate limiting
                self.config.target
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout * self.config.count + 30
            )
            
            # Parse Unix ping output
            # Example: "64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=12.3 ms"
            for line in result.stdout.split('\n'):
                match = re.search(r'time[=](\d+\.?\d*)\s*ms', line)
                if match:
                    latency = float(match.group(1))
                    samples.append(latency)
            
            # Count failures from summary
            # Example: "1000 packets transmitted, 998 received, 0.2% packet loss"
            summary_match = re.search(r'(\d+) packets transmitted, (\d+) received', result.stdout)
            if summary_match:
                transmitted = int(summary_match.group(1))
                received = int(summary_match.group(2))
                failures = transmitted - received
            
        except subprocess.TimeoutExpired:
            self.logger.error("Ping command timed out")
            failures = self.config.count
        except Exception as e:
            self.logger.error(f"Error running ping: {e}")
            failures = self.config.count
        
        return self._compute_statistics(samples, failures)
    
    def _compute_statistics(self, samples: List[float], failures: int) -> ICMPResult:
        """
        Compute statistical summary of ping samples.
        
        Args:
            samples: List of successful latency measurements
            failures: Number of failed pings
        
        Returns:
            ICMPResult with computed statistics
        """
        if not samples:
            self.logger.error("No successful ping samples collected")
            # Return empty result with 100% loss
            return ICMPResult(
                samples=self.config.count,
                p50=0, p90=0, p95=0, p99=0,
                min=0, max=0, mean=0, stddev=0,
                packet_loss=100.0,
                raw_samples=[]
            )
        
        sorted_samples = sorted(samples)
        total_attempts = len(samples) + failures
        
        # Calculate percentiles
        def percentile(data: List[float], p: float) -> float:
            """Calculate percentile from sorted data."""
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = int(k) + 1
            if c >= len(data):
                return data[-1]
            return data[f] + (k - f) * (data[c] - data[f])
        
        result = ICMPResult(
            samples=total_attempts,
            p50=percentile(sorted_samples, 0.50),
            p90=percentile(sorted_samples, 0.90),
            p95=percentile(sorted_samples, 0.95),
            p99=percentile(sorted_samples, 0.99),
            min=min(samples),
            max=max(samples),
            mean=statistics.mean(samples),
            stddev=statistics.stdev(samples) if len(samples) > 1 else 0.0,
            packet_loss=(failures / total_attempts * 100.0) if total_attempts > 0 else 100.0,
            raw_samples=samples[:100]  # Store first 100 for space efficiency
        )
        
        self.logger.info(
            f"ICMP results: p50={result.p50:.1f}ms, p99={result.p99:.1f}ms, "
            f"loss={result.packet_loss:.1f}%"
        )
        
        return result


def run_icmp(target: str, count: int = 1000, **kwargs: Any) -> ICMPResult:
    """
    Convenience function to run ICMP measurement.
    
    Args:
        target: Target host to ping
        count: Number of pings
        **kwargs: Additional PingConfig parameters
    
    Returns:
        ICMPResult with latency distribution
    """
    config = PingConfig(target=target, count=count, **kwargs)
    measurement = PingMeasurement(config)
    return measurement.run()
