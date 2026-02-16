"""Network optimization recommendation engine."""

from typing import List, Dict, Any
import logging

from ipo.core.utils.json_schema import BenchmarkResult, Recommendation
from ipo.core.utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """Rule-based recommendation engine for network optimization."""
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.logger = get_logger(f"{__name__}.RecommendationEngine")
        self.recommendations: List[Recommendation] = []
    
    def generate(self, benchmark: BenchmarkResult) -> List[Recommendation]:
        """
        Generate recommendations based on benchmark results.
        
        Args:
            benchmark: BenchmarkResult from measurement
        
        Returns:
            List of Recommendation objects
        """
        self.logger.info("Generating recommendations...")
        self.recommendations = []
        
        # Analyze bufferbloat
        self._analyze_bufferbloat(benchmark)
        
        # Analyze packet loss
        self._analyze_packet_loss(benchmark)
        
        # Analyze DNS performance
        self._analyze_dns(benchmark)
        
        # Analyze jitter
        self._analyze_jitter(benchmark)
        
        # NIC tuning recommendations (platform-specific)
        self._analyze_nic_settings(benchmark)
        
        self.logger.info(f"Generated {len(self.recommendations)} recommendations")
        return self.recommendations
    
    def _analyze_bufferbloat(self, benchmark: BenchmarkResult) -> None:
        """Analyze bufferbloat and recommend SQM if needed."""
        bufferbloat = benchmark.bufferbloat
        
        # Recommend SQM if bufferbloat is significant (grade C or worse)
        if bufferbloat.latency_increase_ms > 100:
            # High confidence recommendation for severe bufferbloat
            confidence = "high" if bufferbloat.latency_increase_ms > 200 else "medium"
            
            rec = Recommendation(
                id="sqm_openwrt",
                title="Enable Smart Queue Management (SQM) on Router",
                description=(
                    f"Your connection shows {bufferbloat.latency_increase_ms:.0f}ms "
                    f"latency increase under load (grade {bufferbloat.grade}). "
                    "This indicates bufferbloat, which causes lag spikes during high bandwidth usage. "
                    "SQM with CAKE + fq_codel can reduce this significantly."
                ),
                confidence=confidence,
                estimated_impact=(
                    f"Reduce latency under load by 50-80% "
                    f"(from ~{bufferbloat.loaded_latency_ms:.0f}ms to ~{bufferbloat.idle_latency_ms * 1.2:.0f}ms)"
                ),
                category="Router",
                commands=[
                    "# Generate OpenWRT SQM config:",
                    "ipo router openwrt --download YOUR_DOWNLOAD_MBPS --upload YOUR_UPLOAD_MBPS"
                ],
                rollback_commands=[
                    "# On router: uci delete sqm.@queue[0]",
                    "# On router: uci commit && /etc/init.d/sqm restart"
                ],
                requires_admin=False,  # Applied manually on router
                reversible=True,
                risk_level="low"
            )
            
            self.recommendations.append(rec)
            self.logger.info(f"Added recommendation: {rec.id} (confidence: {confidence})")
    
    def _analyze_packet_loss(self, benchmark: BenchmarkResult) -> None:
        """Analyze packet loss and recommend fixes."""
        icmp_loss = benchmark.icmp.packet_loss
        udp_loss = benchmark.jitter.packet_loss
        
        # High ICMP packet loss
        if icmp_loss > 1.0:
            rec = Recommendation(
                id="investigate_packet_loss",
                title="Investigate Packet Loss",
                description=(
                    f"Detected {icmp_loss:.1f}% ICMP packet loss. "
                    "This suggests network congestion, hardware issues, or ISP problems."
                ),
                confidence="high" if icmp_loss > 5.0 else "medium",
                estimated_impact="Potential for significant stability improvement",
                category="System",
                commands=[
                    "# Check network cable connections",
                    "# Test with different DNS servers",
                    "# Contact ISP if persistent"
                ],
                rollback_commands=[],
                requires_admin=False,
                reversible=True,
                risk_level="low"
            )
            
            self.recommendations.append(rec)
    
    def _analyze_dns(self, benchmark: BenchmarkResult) -> None:
        """Analyze DNS performance and recommend faster resolvers."""
        if not benchmark.dns or len(benchmark.dns) < 2:
            return
        
        # Find fastest resolver
        fastest = min(benchmark.dns, key=lambda d: d.median_ms)
        
        # Check if there's a significant improvement available
        # Compare to typical ISP DNS (~30-50ms)
        if fastest.median_ms < 20 and fastest.success_rate > 95:
            rec = Recommendation(
                id="dns_cloudflare_google",
                title=f"Use Faster DNS Resolver ({fastest.resolver})",
                description=(
                    f"DNS resolver {fastest.resolver} shows {fastest.median_ms:.1f}ms median latency. "
                    "Switching from your ISP's DNS can improve browsing responsiveness."
                ),
                confidence="medium",
                estimated_impact=f"Reduce DNS lookup time to ~{fastest.median_ms:.0f}ms",
                category="DNS",
                commands=[
                    f"# Windows: Set DNS to {fastest.resolver}",
                    "# Settings → Network → Adapter → Properties → IPv4 → DNS"
                ],
                rollback_commands=[
                    "# Set DNS back to 'Obtain DNS server address automatically'"
                ],
                requires_admin=True,
                reversible=True,
                risk_level="low"
            )
            
            self.recommendations.append(rec)
    
    def _analyze_jitter(self, benchmark: BenchmarkResult) -> None:
        """Analyze jitter and recommend fixes."""
        jitter = benchmark.jitter
        
        if jitter.mean_jitter_ms > 10:
            rec = Recommendation(
                id="reduce_jitter",
                title="High Jitter Detected",
                description=(
                    f"UDP jitter is {jitter.mean_jitter_ms:.1f}ms, which may cause issues "
                    "in real-time applications (gaming, VoIP, video calls)."
                ),
                confidence="medium",
                estimated_impact="Improved real-time application performance",
                category="System",
                commands=[
                    "# Enable QoS on router",
                    "# Close background applications using bandwidth",
                    "# Consider SQM for jitter reduction"
                ],
                rollback_commands=[],
                requires_admin=False,
                reversible=True,
                risk_level="low"
            )
            
            self.recommendations.append(rec)
    
    def _analyze_nic_settings(self, benchmark: BenchmarkResult) -> None:
        """Analyze NIC settings and recommend tuning (Windows-specific)."""
        import platform
        
        if platform.system() != "Windows":
            return
        
        # Generic NIC tuning recommendation
        # In production, we would query actual NIC settings
        rec = Recommendation(
            id="nic_rss_enable",
            title="Enable Receive Side Scaling (RSS) on Network Adapter",
            description=(
                "RSS distributes network processing across multiple CPU cores, "
                "improving throughput on multi-core systems. "
                "This is especially beneficial for high-speed connections (>100 Mbps)."
            ),
            confidence="medium",
            estimated_impact="Potential 10-30% throughput improvement on fast connections",
            category="NIC",
            commands=[
                "# Check current RSS status:",
                "Get-NetAdapterRss",
                "# Enable RSS:",
                "Enable-NetAdapterRss -Name '*'",
            ],
            rollback_commands=[
                "Disable-NetAdapterRss -Name '*'"
            ],
            requires_admin=True,
            reversible=True,
            risk_level="low"
        )
        
        self.recommendations.append(rec)
        self.logger.info("Added NIC tuning recommendation (RSS)")
    
    def print_summary(self, recommendations: List[Recommendation]) -> None:
        """
        Print human-readable recommendation summary.
        
        Args:
            recommendations: List of recommendations
        """
        if not recommendations:
            print("\n✓ No optimization recommendations - your network is performing well!")
            return
        
        print(f"\n📊 Found {len(recommendations)} optimization opportunities:\n")
        
        for i, rec in enumerate(recommendations, 1):
            # Confidence indicator
            conf_indicator = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(rec.confidence, "⚪")
            
            print(f"{i}. {conf_indicator} {rec.title}")
            print(f"   Category: {rec.category} | Confidence: {rec.confidence.upper()}")
            print(f"   Impact: {rec.estimated_impact}")
            print(f"   Risk: {rec.risk_level} | Reversible: {'Yes' if rec.reversible else 'No'}")
            if rec.requires_admin:
                print("   ⚠️  Requires administrator privileges")
            print()


def generate_recommendations(benchmark: BenchmarkResult) -> List[Recommendation]:
    """
    Convenience function to generate recommendations.
    
    Args:
        benchmark: BenchmarkResult from measurement
    
    Returns:
        List of Recommendation objects
    """
    engine = RecommendationEngine()
    return engine.generate(benchmark)
