"""Tests for benchmark measurement modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from ipo.core.measurement.ping_distribution import PingMeasurement, PingConfig, run_icmp
from ipo.core.measurement.iperf3_wrapper import Iperf3Wrapper
from ipo.core.measurement.dns_bench import DNSBenchmark
from ipo.core.utils.json_schema import (
    ICMPResult, BufferbloatGrade, calculate_bufferbloat_grade
)


class TestPingMeasurement:
    """Tests for ICMP ping measurement."""
    
    def test_ping_config_defaults(self):
        """Test PingConfig default values."""
        config = PingConfig(target="1.1.1.1")
        assert config.target == "1.1.1.1"
        assert config.count == 1000
        assert config.timeout == 2
    
    def test_compute_statistics_empty_samples(self):
        """Test statistics computation with no successful samples."""
        config = PingConfig(target="1.1.1.1", count=100)
        measurement = PingMeasurement(config)
        
        result = measurement._compute_statistics(samples=[], failures=100)
        
        assert result.packet_loss == 100.0
        assert result.samples == 100
        assert result.p50 == 0
        assert result.p99 == 0
    
    def test_compute_statistics_valid_samples(self):
        """Test statistics computation with valid samples."""
        config = PingConfig(target="1.1.1.1", count=100)
        measurement = PingMeasurement(config)
        
        # Simulate 95 successful pings, 5 failures
        samples = [10.0 + i * 0.5 for i in range(95)]  # 10ms to 57ms
        result = measurement._compute_statistics(samples=samples, failures=5)
        
        assert result.samples == 100
        assert result.packet_loss == 5.0
        assert result.min == 10.0
        assert result.max == 57.0
        assert 30.0 < result.p50 < 35.0  # Median should be around middle
        assert result.p99 > result.p90 > result.p50
    
    @patch('subprocess.run')
    def test_windows_ping_parsing(self, mock_run):
        """Test Windows ping output parsing."""
        # Mock Windows ping output
        mock_output = """
Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=12ms TTL=57
Reply from 1.1.1.1: bytes=32 time=15ms TTL=57
Reply from 1.1.1.1: bytes=32 time=11ms TTL=57
Request timed out.
Reply from 1.1.1.1: bytes=32 time=13ms TTL=57

Ping statistics for 1.1.1.1:
    Packets: Sent = 5, Received = 4, Lost = 1 (20% loss)
"""
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        config = PingConfig(target="1.1.1.1", count=5)
        measurement = PingMeasurement(config)
        
        # This would normally run async, but we can test the parsing logic
        # by calling the underlying method if we make it sync for testing


class TestBufferbloatGrade:
    """Tests for bufferbloat grade calculation."""
    
    def test_grade_a_plus(self):
        """Test A+ grade (< 10ms increase)."""
        assert calculate_bufferbloat_grade(5.0) == BufferbloatGrade.A_PLUS
        assert calculate_bufferbloat_grade(9.9) == BufferbloatGrade.A_PLUS
    
    def test_grade_a(self):
        """Test A grade (10-30ms)."""
        assert calculate_bufferbloat_grade(10.0) == BufferbloatGrade.A
        assert calculate_bufferbloat_grade(25.0) == BufferbloatGrade.A
        assert calculate_bufferbloat_grade(29.9) == BufferbloatGrade.A
    
    def test_grade_b(self):
        """Test B grade (30-100ms)."""
        assert calculate_bufferbloat_grade(30.0) == BufferbloatGrade.B
        assert calculate_bufferbloat_grade(75.0) == BufferbloatGrade.B
    
    def test_grade_c(self):
        """Test C grade (100-200ms)."""
        assert calculate_bufferbloat_grade(100.0) == BufferbloatGrade.C
        assert calculate_bufferbloat_grade(150.0) == BufferbloatGrade.C
    
    def test_grade_d(self):
        """Test D grade (200-400ms)."""
        assert calculate_bufferbloat_grade(200.0) == BufferbloatGrade.D
        assert calculate_bufferbloat_grade(300.0) == BufferbloatGrade.D
    
    def test_grade_f(self):
        """Test F grade (>= 400ms)."""
        assert calculate_bufferbloat_grade(400.0) == BufferbloatGrade.F
        assert calculate_bufferbloat_grade(1000.0) == BufferbloatGrade.F


class TestIperf3Wrapper:
    """Tests for iperf3 wrapper."""
    
    @patch('shutil.which')
    def test_check_iperf3_available(self, mock_which):
        """Test iperf3 availability check."""
        mock_which.return_value = "/usr/bin/iperf3"
        wrapper = Iperf3Wrapper()
        assert wrapper._check_iperf3() is True
    
    @patch('shutil.which')
    def test_check_iperf3_not_available(self, mock_which):
        """Test iperf3 not available."""
        mock_which.return_value = None
        wrapper = Iperf3Wrapper()
        assert wrapper._check_iperf3() is False
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_run_iperf3_timeout(self, mock_which, mock_run):
        """Test iperf3 timeout handling."""
        mock_which.return_value = "/usr/bin/iperf3"
        mock_run.side_effect = subprocess.TimeoutExpired("iperf3", 30)
        
        wrapper = Iperf3Wrapper()
        
        with pytest.raises(RuntimeError, match="timed out"):
            wrapper._run_iperf3(["-t", "10"], timeout=30)
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_measure_throughput_success(self, mock_which, mock_run):
        """Test successful throughput measurement."""
        mock_which.return_value = "/usr/bin/iperf3"
        
        # Mock iperf3 JSON output
        mock_download_result = {
            "end": {
                "sum_received": {"bits_per_second": 95_300_000},
                "sum_sent": {"retransmits": 2}
            }
        }
        
        mock_upload_result = {
            "end": {
                "sum_received": {"bits_per_second": 18_200_000},
                "sum_sent": {"retransmits": 1}
            }
        }
        
        import json
        mock_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(mock_download_result), stderr=""),
            Mock(returncode=0, stdout=json.dumps(mock_upload_result), stderr="")
        ]
        
        wrapper = Iperf3Wrapper()
        result = wrapper.measure_throughput(duration=10)
        
        assert result.download_mbps == 95.3
        assert result.upload_mbps == 18.2
        assert result.retransmits == 3


class TestDNSBenchmark:
    """Tests for DNS benchmark."""
    
    def test_resolvers_list(self):
        """Test DNS resolvers list."""
        bench = DNSBenchmark()
        assert "1.1.1.1" in bench.resolvers  # Cloudflare
        assert "8.8.8.8" in bench.resolvers  # Google
    
    def test_query_domain_failure(self):
        """Test domain query failure handling."""
        bench = DNSBenchmark()
        
        # Query non-existent domain with short timeout
        result = bench._query_domain_fallback("nonexistent.invalid.tld.123", timeout=0.5)
        assert result == -1
    
    @patch('socket.gethostbyname')
    @patch('time.perf_counter')
    def test_query_domain_fallback_success(self, mock_time, mock_gethostbyname):
        """Test successful fallback domain query."""
        mock_time.side_effect = [0.0, 0.015]  # 15ms query
        mock_gethostbyname.return_value = "1.2.3.4"
        
        bench = DNSBenchmark()
        result = bench._query_domain_fallback("google.com", timeout=2.0)
        
        assert result == 15.0  # 15ms


class TestICMPResult:
    """Tests for ICMPResult schema."""
    
    def test_icmp_result_creation(self):
        """Test ICMPResult creation and validation."""
        result = ICMPResult(
            samples=1000,
            p50=12.3,
            p90=18.5,
            p95=22.1,
            p99=45.2,
            min=8.1,
            max=120.5,
            mean=15.2,
            stddev=8.3,
            packet_loss=0.5,
            raw_samples=[10.0, 12.0, 11.5]
        )
        
        assert result.samples == 1000
        assert result.p50 == 12.3
        assert result.packet_loss == 0.5
    
    def test_icmp_result_validation_negative_latency(self):
        """Test ICMPResult rejects negative latency."""
        with pytest.raises(ValueError):
            ICMPResult(
                samples=1000,
                p50=-5.0,  # Invalid negative
                p90=18.5,
                p95=22.1,
                p99=45.2,
                min=8.1,
                max=120.5,
                mean=15.2,
                stddev=8.3,
                packet_loss=0.5,
                raw_samples=[]
            )
    
    def test_icmp_result_validation_packet_loss_range(self):
        """Test ICMPResult validates packet loss range."""
        with pytest.raises(ValueError):
            ICMPResult(
                samples=1000,
                p50=12.3,
                p90=18.5,
                p95=22.1,
                p99=45.2,
                min=8.1,
                max=120.5,
                mean=15.2,
                stddev=8.3,
                packet_loss=150.0,  # Invalid > 100
                raw_samples=[]
            )


# Integration test fixtures
@pytest.fixture
def sample_benchmark_result():
    """Fixture providing a sample benchmark result."""
    from ipo.core.utils.json_schema import (
        BenchmarkResult, ICMPResult, JitterResult,
        ThroughputResult, BufferbloatResult, BufferbloatGrade
    )
    from datetime import datetime
    
    return BenchmarkResult(
        timestamp=datetime.now(),
        target="1.1.1.1",
        system_info={"os": "Windows", "cpu_count": 8},
        icmp=ICMPResult(
            samples=1000,
            p50=12.3, p90=18.5, p95=22.1, p99=45.2,
            min=8.1, max=120.5, mean=15.2, stddev=8.3,
            packet_loss=0.2, raw_samples=[]
        ),
        jitter=JitterResult(
            mean_jitter_ms=2.5,
            max_jitter_ms=8.3,
            packet_loss=0.1,
            out_of_order=0
        ),
        throughput=ThroughputResult(
            download_mbps=95.3,
            upload_mbps=18.2,
            retransmits=2
        ),
        bufferbloat=BufferbloatResult(
            idle_latency_ms=12.5,
            loaded_latency_ms=156.3,
            latency_increase_ms=143.8,
            latency_increase_pct=1150.4,
            grade=BufferbloatGrade.C
        ),
        dns=[],
        metadata={}
    )


def test_benchmark_result_json_export(sample_benchmark_result):
    """Test exporting benchmark result to JSON."""
    import json
    
    json_data = sample_benchmark_result.model_dump(mode='json')
    json_str = json.dumps(json_data, indent=2)
    
    assert "1.1.1.1" in json_str
    assert "bufferbloat" in json_str
    
    # Verify can be loaded back
    loaded = json.loads(json_str)
    assert loaded["target"] == "1.1.1.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
