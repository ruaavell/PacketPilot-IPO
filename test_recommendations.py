"""Tests for recommendation engine."""

import pytest
from datetime import datetime

from ipo.core.recommendation import RecommendationEngine, generate_recommendations
from ipo.core.utils.json_schema import (
    BenchmarkResult, ICMPResult, JitterResult, ThroughputResult,
    BufferbloatResult, BufferbloatGrade, DNSResult
)


@pytest.fixture
def high_bufferbloat_benchmark():
    """Benchmark with high bufferbloat (should trigger SQM recommendation)."""
    return BenchmarkResult(
        timestamp=datetime.now(),
        target="1.1.1.1",
        system_info={},
        icmp=ICMPResult(
            samples=1000, p50=15.0, p90=25.0, p95=30.0, p99=50.0,
            min=10.0, max=100.0, mean=20.0, stddev=10.0,
            packet_loss=0.5, raw_samples=[]
        ),
        jitter=JitterResult(
            mean_jitter_ms=3.0, max_jitter_ms=10.0,
            packet_loss=0.2, out_of_order=0
        ),
        throughput=ThroughputResult(
            download_mbps=95.0, upload_mbps=18.0, retransmits=2
        ),
        bufferbloat=BufferbloatResult(
            idle_latency_ms=15.0,
            loaded_latency_ms=235.0,
            latency_increase_ms=220.0,  # Very high
            latency_increase_pct=1466.7,
            grade=BufferbloatGrade.F
        ),
        dns=[],
        metadata={}
    )


@pytest.fixture
def low_bufferbloat_benchmark():
    """Benchmark with low bufferbloat (should not trigger SQM recommendation)."""
    return BenchmarkResult(
        timestamp=datetime.now(),
        target="1.1.1.1",
        system_info={},
        icmp=ICMPResult(
            samples=1000, p50=12.0, p90=18.0, p95=22.0, p99=30.0,
            min=8.0, max=50.0, mean=15.0, stddev=5.0,
            packet_loss=0.1, raw_samples=[]
        ),
        jitter=JitterResult(
            mean_jitter_ms=1.5, max_jitter_ms=5.0,
            packet_loss=0.0, out_of_order=0
        ),
        throughput=ThroughputResult(
            download_mbps=100.0, upload_mbps=20.0, retransmits=0
        ),
        bufferbloat=BufferbloatResult(
            idle_latency_ms=12.0,
            loaded_latency_ms=20.0,
            latency_increase_ms=8.0,  # Low - good!
            latency_increase_pct=66.7,
            grade=BufferbloatGrade.A_PLUS
        ),
        dns=[],
        metadata={}
    )


@pytest.fixture
def high_packet_loss_benchmark():
    """Benchmark with high packet loss (should trigger investigation)."""
    return BenchmarkResult(
        timestamp=datetime.now(),
        target="1.1.1.1",
        system_info={},
        icmp=ICMPResult(
            samples=1000, p50=15.0, p90=25.0, p95=30.0, p99=50.0,
            min=10.0, max=100.0, mean=20.0, stddev=10.0,
            packet_loss=8.5,  # High loss
            raw_samples=[]
        ),
        jitter=JitterResult(
            mean_jitter_ms=3.0, max_jitter_ms=10.0,
            packet_loss=5.2, out_of_order=10
        ),
        throughput=ThroughputResult(
            download_mbps=75.0, upload_mbps=15.0, retransmits=50
        ),
        bufferbloat=BufferbloatResult(
            idle_latency_ms=15.0,
            loaded_latency_ms=50.0,
            latency_increase_ms=35.0,
            latency_increase_pct=233.3,
            grade=BufferbloatGrade.B
        ),
        dns=[],
        metadata={}
    )


@pytest.fixture
def fast_dns_benchmark():
    """Benchmark with fast alternative DNS resolver."""
    return BenchmarkResult(
        timestamp=datetime.now(),
        target="1.1.1.1",
        system_info={},
        icmp=ICMPResult(
            samples=1000, p50=12.0, p90=18.0, p95=22.0, p99=30.0,
            min=8.0, max=50.0, mean=15.0, stddev=5.0,
            packet_loss=0.1, raw_samples=[]
        ),
        jitter=JitterResult(
            mean_jitter_ms=2.0, max_jitter_ms=8.0,
            packet_loss=0.0, out_of_order=0
        ),
        throughput=ThroughputResult(
            download_mbps=100.0, upload_mbps=20.0, retransmits=0
        ),
        bufferbloat=BufferbloatResult(
            idle_latency_ms=12.0,
            loaded_latency_ms=25.0,
            latency_increase_ms=13.0,
            latency_increase_pct=108.3,
            grade=BufferbloatGrade.A
        ),
        dns=[
            DNSResult(resolver="1.1.1.1", median_ms=8.5, p95_ms=12.0, success_rate=99.5, samples=20),
            DNSResult(resolver="8.8.8.8", median_ms=15.2, p95_ms=22.0, success_rate=98.0, samples=20),
        ],
        metadata={}
    )


class TestRecommendationEngine:
    """Tests for RecommendationEngine class."""
    
    def test_high_bufferbloat_generates_sqm_recommendation(self, high_bufferbloat_benchmark):
        """Test that high bufferbloat generates SQM recommendation."""
        engine = RecommendationEngine()
        recommendations = engine.generate(high_bufferbloat_benchmark)
        
        # Should have at least SQM recommendation
        assert len(recommendations) > 0
        
        # Find SQM recommendation
        sqm_rec = next((r for r in recommendations if r.id == "sqm_openwrt"), None)
        assert sqm_rec is not None
        assert sqm_rec.confidence == "high"  # 220ms is very high
        assert "SQM" in sqm_rec.title or "Queue" in sqm_rec.title
        assert sqm_rec.category == "Router"
        assert sqm_rec.reversible is True
    
    def test_low_bufferbloat_no_sqm_recommendation(self, low_bufferbloat_benchmark):
        """Test that low bufferbloat does not generate SQM recommendation."""
        engine = RecommendationEngine()
        recommendations = engine.generate(low_bufferbloat_benchmark)
        
        # Should not have SQM recommendation
        sqm_rec = next((r for r in recommendations if r.id == "sqm_openwrt"), None)
        assert sqm_rec is None
    
    def test_medium_bufferbloat_generates_medium_confidence(self):
        """Test that medium bufferbloat generates medium confidence recommendation."""
        benchmark = BenchmarkResult(
            timestamp=datetime.now(),
            target="1.1.1.1",
            system_info={},
            icmp=ICMPResult(
                samples=1000, p50=12.0, p90=20.0, p95=25.0, p99=40.0,
                min=8.0, max=80.0, mean=15.0, stddev=8.0,
                packet_loss=0.2, raw_samples=[]
            ),
            jitter=JitterResult(
                mean_jitter_ms=2.5, max_jitter_ms=8.0,
                packet_loss=0.1, out_of_order=0
            ),
            throughput=ThroughputResult(
                download_mbps=90.0, upload_mbps=18.0, retransmits=1
            ),
            bufferbloat=BufferbloatResult(
                idle_latency_ms=12.0,
                loaded_latency_ms=132.0,
                latency_increase_ms=120.0,  # Medium (100-200ms)
                latency_increase_pct=1000.0,
                grade=BufferbloatGrade.C
            ),
            dns=[],
            metadata={}
        )
        
        engine = RecommendationEngine()
        recommendations = engine.generate(benchmark)
        
        sqm_rec = next((r for r in recommendations if r.id == "sqm_openwrt"), None)
        assert sqm_rec is not None
        assert sqm_rec.confidence == "medium"
    
    def test_high_packet_loss_generates_investigation(self, high_packet_loss_benchmark):
        """Test that high packet loss generates investigation recommendation."""
        engine = RecommendationEngine()
        recommendations = engine.generate(high_packet_loss_benchmark)
        
        # Find packet loss recommendation
        loss_rec = next((r for r in recommendations if "packet loss" in r.title.lower()), None)
        assert loss_rec is not None
        assert loss_rec.confidence == "high"  # 8.5% is very high
    
    def test_fast_dns_generates_dns_recommendation(self, fast_dns_benchmark):
        """Test that fast alternative DNS generates recommendation."""
        engine = RecommendationEngine()
        recommendations = engine.generate(fast_dns_benchmark)
        
        # Find DNS recommendation
        dns_rec = next((r for r in recommendations if "DNS" in r.title), None)
        assert dns_rec is not None
        assert "1.1.1.1" in dns_rec.description  # Should mention Cloudflare
    
    def test_all_recommendations_have_required_fields(self, high_bufferbloat_benchmark):
        """Test that all recommendations have required fields."""
        engine = RecommendationEngine()
        recommendations = engine.generate(high_bufferbloat_benchmark)
        
        for rec in recommendations:
            # All recommendations must have these fields
            assert rec.id is not None and len(rec.id) > 0
            assert rec.title is not None and len(rec.title) > 0
            assert rec.description is not None and len(rec.description) > 0
            assert rec.confidence in ["high", "medium", "low"]
            assert rec.estimated_impact is not None
            assert rec.category is not None
            assert isinstance(rec.commands, list)
            assert isinstance(rec.rollback_commands, list)
            assert isinstance(rec.requires_admin, bool)
            assert isinstance(rec.reversible, bool)
            assert rec.risk_level in ["low", "medium", "high"]
    
    def test_high_jitter_generates_recommendation(self):
        """Test that high jitter generates recommendation."""
        benchmark = BenchmarkResult(
            timestamp=datetime.now(),
            target="1.1.1.1",
            system_info={},
            icmp=ICMPResult(
                samples=1000, p50=12.0, p90=20.0, p95=25.0, p99=40.0,
                min=8.0, max=80.0, mean=15.0, stddev=8.0,
                packet_loss=0.2, raw_samples=[]
            ),
            jitter=JitterResult(
                mean_jitter_ms=25.0,  # High jitter
                max_jitter_ms=50.0,
                packet_loss=0.5,
                out_of_order=15
            ),
            throughput=ThroughputResult(
                download_mbps=90.0, upload_mbps=18.0, retransmits=1
            ),
            bufferbloat=BufferbloatResult(
                idle_latency_ms=12.0,
                loaded_latency_ms=30.0,
                latency_increase_ms=18.0,
                latency_increase_pct=150.0,
                grade=BufferbloatGrade.A
            ),
            dns=[],
            metadata={}
        )
        
        engine = RecommendationEngine()
        recommendations = engine.generate(benchmark)
        
        jitter_rec = next((r for r in recommendations if "jitter" in r.title.lower()), None)
        assert jitter_rec is not None


class TestRecommendationGeneration:
    """Tests for recommendation generation function."""
    
    def test_generate_recommendations_function(self, high_bufferbloat_benchmark):
        """Test convenience function for generating recommendations."""
        recommendations = generate_recommendations(high_bufferbloat_benchmark)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should have at least SQM recommendation for high bufferbloat
        assert any(r.id == "sqm_openwrt" for r in recommendations)


class TestRecommendationPriority:
    """Tests for recommendation prioritization."""
    
    def test_multiple_issues_generates_multiple_recommendations(self):
        """Test that multiple issues generate multiple recommendations."""
        # Benchmark with both bufferbloat AND packet loss
        benchmark = BenchmarkResult(
            timestamp=datetime.now(),
            target="1.1.1.1",
            system_info={},
            icmp=ICMPResult(
                samples=1000, p50=15.0, p90=25.0, p95=30.0, p99=50.0,
                min=10.0, max=100.0, mean=20.0, stddev=10.0,
                packet_loss=6.0,  # High packet loss
                raw_samples=[]
            ),
            jitter=JitterResult(
                mean_jitter_ms=15.0,  # High jitter
                max_jitter_ms=30.0,
                packet_loss=4.0,
                out_of_order=20
            ),
            throughput=ThroughputResult(
                download_mbps=80.0, upload_mbps=15.0, retransmits=25
            ),
            bufferbloat=BufferbloatResult(
                idle_latency_ms=15.0,
                loaded_latency_ms=250.0,
                latency_increase_ms=235.0,  # Very high bufferbloat
                latency_increase_pct=1566.7,
                grade=BufferbloatGrade.F
            ),
            dns=[],
            metadata={}
        )
        
        engine = RecommendationEngine()
        recommendations = engine.generate(benchmark)
        
        # Should have multiple recommendations
        assert len(recommendations) >= 3
        
        # Should have SQM, packet loss investigation, and jitter recommendations
        rec_ids = [r.id for r in recommendations]
        assert "sqm_openwrt" in rec_ids
        assert "investigate_packet_loss" in rec_ids
        assert "reduce_jitter" in rec_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
