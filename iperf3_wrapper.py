"""iperf3 wrapper for throughput and jitter measurement."""

import subprocess
import json
import logging
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

from ipo.core.utils.json_schema import JitterResult, ThroughputResult
from ipo.core.utils.logging import get_logger

logger = get_logger(__name__)


class Iperf3Wrapper:
    """Wrapper for iperf3 command-line tool."""
    
    # Public iperf3 servers for testing
    PUBLIC_SERVERS = [
        "iperf.he.net",  # Hurricane Electric
        "ping.online.net",  # Online.net
        "iperf.scottlinux.com",  # Scott Linux
        "speedtest.uztelecom.uz",  # UzTelecom (Asia)
        "bouygues.iperf.fr",  # Bouygues Telecom
    ]
    
    def __init__(self, server: Optional[str] = None, port: int = 5201):
        """
        Initialize iperf3 wrapper.
        
        Args:
            server: iperf3 server address (defaults to first available public server)
            port: Server port
        """
        self.server = server or self.PUBLIC_SERVERS[0]
        self.port = port
        self.logger = get_logger(f"{__name__}.Iperf3Wrapper")
        
        # Check if iperf3 is available
        if not self._check_iperf3():
            self.logger.warning("iperf3 not found in PATH")
    
    def _check_iperf3(self) -> bool:
        """Check if iperf3 is available in system PATH."""
        return shutil.which("iperf3") is not None
    
    def _run_iperf3(self, args: list, timeout: int = 30) -> Dict[str, Any]:
        """
        Run iperf3 command and parse JSON output.
        
        Args:
            args: Additional iperf3 arguments
            timeout: Command timeout in seconds
        
        Returns:
            Parsed JSON output from iperf3
        
        Raises:
            RuntimeError: If iperf3 fails or is not installed
        """
        if not self._check_iperf3():
            raise RuntimeError(
                "iperf3 is not installed. Please install iperf3:\n"
                "  Windows: Download from https://iperf.fr/iperf-download.php\n"
                "  Linux: sudo apt install iperf3\n"
                "  macOS: brew install iperf3"
            )
        
        cmd = [
            "iperf3",
            "-c", self.server,
            "-p", str(self.port),
            "-J",  # JSON output
        ] + args
        
        self.logger.debug(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"iperf3 failed: {result.stderr}")
                raise RuntimeError(f"iperf3 error: {result.stderr}")
            
            return json.loads(result.stdout)
        
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"iperf3 timed out after {timeout} seconds")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse iperf3 JSON: {e}")
            raise RuntimeError(f"Invalid iperf3 output: {e}")
        except FileNotFoundError:
            raise RuntimeError("iperf3 executable not found")
    
    def measure_throughput(self, duration: int = 10, parallel: int = 1) -> ThroughputResult:
        """
        Measure TCP throughput (download and upload).
        
        Args:
            duration: Test duration in seconds
            parallel: Number of parallel streams
        
        Returns:
            ThroughputResult with download/upload speeds
        """
        self.logger.info(f"Measuring throughput to {self.server} ({duration}s, {parallel} streams)")
        
        try:
            # Download test
            download_data = self._run_iperf3([
                "-t", str(duration),
                "-P", str(parallel),
            ])
            
            download_mbps = download_data["end"]["sum_received"]["bits_per_second"] / 1_000_000
            download_retrans = download_data["end"]["sum_sent"].get("retransmits", 0)
            
            # Upload test
            upload_data = self._run_iperf3([
                "-t", str(duration),
                "-P", str(parallel),
                "-R",  # Reverse mode (upload)
            ])
            
            upload_mbps = upload_data["end"]["sum_received"]["bits_per_second"] / 1_000_000
            upload_retrans = upload_data["end"]["sum_sent"].get("retransmits", 0)
            
            result = ThroughputResult(
                download_mbps=round(download_mbps, 2),
                upload_mbps=round(upload_mbps, 2),
                retransmits=download_retrans + upload_retrans
            )
            
            self.logger.info(
                f"Throughput: ↓{result.download_mbps} Mbps, ↑{result.upload_mbps} Mbps, "
                f"{result.retransmits} retransmissions"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Throughput measurement failed: {e}")
            # Return zero values on failure
            return ThroughputResult(
                download_mbps=0.0,
                upload_mbps=0.0,
                retransmits=0
            )
    
    def measure_jitter(self, duration: int = 10, bandwidth: str = "10M") -> JitterResult:
        """
        Measure UDP jitter and packet loss.
        
        Args:
            duration: Test duration in seconds
            bandwidth: Target bandwidth (e.g., "10M")
        
        Returns:
            JitterResult with jitter and packet loss
        """
        self.logger.info(f"Measuring jitter to {self.server} ({duration}s, {bandwidth})")
        
        try:
            data = self._run_iperf3([
                "-u",  # UDP mode
                "-b", bandwidth,  # Target bandwidth
                "-t", str(duration),
            ])
            
            # Extract UDP statistics
            end_sum = data["end"]["sum"]
            
            result = JitterResult(
                mean_jitter_ms=round(end_sum.get("jitter_ms", 0.0), 3),
                max_jitter_ms=round(end_sum.get("jitter_ms", 0.0), 3),  # iperf3 only provides mean
                packet_loss=round(end_sum.get("lost_percent", 0.0), 2),
                out_of_order=end_sum.get("out_of_order", 0)
            )
            
            self.logger.info(
                f"Jitter: {result.mean_jitter_ms}ms, loss: {result.packet_loss}%"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Jitter measurement failed: {e}")
            return JitterResult(
                mean_jitter_ms=0.0,
                max_jitter_ms=0.0,
                packet_loss=0.0,
                out_of_order=0
            )


def measure_throughput(
    server: Optional[str] = None,
    duration: int = 10,
    parallel: int = 1
) -> ThroughputResult:
    """
    Convenience function for throughput measurement.
    
    Args:
        server: iperf3 server (optional, uses public server if None)
        duration: Test duration in seconds
        parallel: Number of parallel streams
    
    Returns:
        ThroughputResult
    """
    wrapper = Iperf3Wrapper(server=server)
    return wrapper.measure_throughput(duration=duration, parallel=parallel)


def measure_jitter(
    server: Optional[str] = None,
    duration: int = 10,
    bandwidth: str = "10M"
) -> JitterResult:
    """
    Convenience function for jitter measurement.
    
    Args:
        server: iperf3 server (optional, uses public server if None)
        duration: Test duration in seconds
        bandwidth: Target bandwidth
    
    Returns:
        JitterResult
    """
    wrapper = Iperf3Wrapper(server=server)
    return wrapper.measure_jitter(duration=duration, bandwidth=bandwidth)
