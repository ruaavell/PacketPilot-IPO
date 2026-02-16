"""DNS resolver benchmarking."""

import socket
import time
import statistics
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from ipo.core.utils.json_schema import DNSResult
from ipo.core.utils.logging import get_logger

logger = get_logger(__name__)


class DNSBenchmark:
    """DNS resolver performance benchmark."""
    
    # Common DNS resolvers to test
    RESOLVERS = {
        "cloudflare": "1.1.1.1",
        "cloudflare_secondary": "1.0.0.1",
        "google": "8.8.8.8",
        "google_secondary": "8.8.4.4",
        "quad9": "9.9.9.9",
        "opendns": "208.67.222.222",
    }
    
    # Popular domains for testing
    TEST_DOMAINS = [
        "google.com", "facebook.com", "youtube.com", "amazon.com", "wikipedia.org",
        "twitter.com", "instagram.com", "reddit.com", "netflix.com", "linkedin.com",
        "github.com", "stackoverflow.com", "microsoft.com", "apple.com", "cloudflare.com",
        "yahoo.com", "zoom.us", "ebay.com", "twitch.tv", "pinterest.com",
        "cnn.com", "bbc.com", "nytimes.com", "espn.com", "spotify.com",
        "discord.com", "dropbox.com", "adobe.com", "nvidia.com", "amd.com",
    ]
    
    def __init__(self, resolvers: List[str] = None, domains: List[str] = None):
        """
        Initialize DNS benchmark.
        
        Args:
            resolvers: List of DNS resolver IPs to test (uses defaults if None)
            domains: List of domains to resolve (uses defaults if None)
        """
        self.resolvers = resolvers or [self.RESOLVERS["cloudflare"], self.RESOLVERS["google"]]
        self.domains = domains or self.TEST_DOMAINS[:20]  # Use first 20 domains
        self.logger = get_logger(f"{__name__}.DNSBenchmark")
        
        # Store original resolver
        self.original_resolver = self._get_current_resolver()
    
    def _get_current_resolver(self) -> str:
        """Get the system's current DNS resolver."""
        # This is a simplified version; actual implementation would parse
        # /etc/resolv.conf on Linux or registry on Windows
        return socket.gethostbyname("dns.google")  # Placeholder
    
    def _query_domain(self, domain: str, resolver: str, timeout: float = 2.0) -> float:
        """
        Query a domain using a specific resolver.
        
        Args:
            domain: Domain to resolve
            resolver: DNS resolver IP
            timeout: Query timeout in seconds
        
        Returns:
            Query time in milliseconds, or -1 on failure
        """
        try:
            # Create a custom resolver
            import dns.resolver
            
            custom_resolver = dns.resolver.Resolver(configure=False)
            custom_resolver.nameservers = [resolver]
            custom_resolver.timeout = timeout
            custom_resolver.lifetime = timeout
            
            start = time.perf_counter()
            custom_resolver.resolve(domain, 'A')
            duration = (time.perf_counter() - start) * 1000  # Convert to ms
            
            return duration
        
        except ImportError:
            # Fallback to socket-based resolution (less accurate)
            self.logger.warning("dnspython not installed, using fallback method")
            return self._query_domain_fallback(domain, timeout)
        
        except Exception as e:
            self.logger.debug(f"Failed to resolve {domain} via {resolver}: {e}")
            return -1
    
    def _query_domain_fallback(self, domain: str, timeout: float = 2.0) -> float:
        """
        Fallback domain query using socket (less accurate, uses system resolver).
        
        Args:
            domain: Domain to resolve
            timeout: Query timeout in seconds
        
        Returns:
            Query time in milliseconds, or -1 on failure
        """
        try:
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            
            start = time.perf_counter()
            socket.gethostbyname(domain)
            duration = (time.perf_counter() - start) * 1000
            
            socket.setdefaulttimeout(old_timeout)
            return duration
        
        except Exception as e:
            self.logger.debug(f"Fallback resolution failed for {domain}: {e}")
            return -1
    
    def benchmark_resolver(self, resolver: str, max_workers: int = 10) -> DNSResult:
        """
        Benchmark a single DNS resolver.
        
        Args:
            resolver: DNS resolver IP address
            max_workers: Number of concurrent queries
        
        Returns:
            DNSResult with performance metrics
        """
        self.logger.info(f"Benchmarking DNS resolver: {resolver}")
        
        query_times: List[float] = []
        failures = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._query_domain, domain, resolver): domain
                for domain in self.domains
            }
            
            for future in as_completed(futures):
                result = future.result()
                if result > 0:
                    query_times.append(result)
                else:
                    failures += 1
        
        if not query_times:
            self.logger.error(f"All queries failed for resolver {resolver}")
            return DNSResult(
                resolver=resolver,
                median_ms=0.0,
                p95_ms=0.0,
                success_rate=0.0,
                samples=len(self.domains)
            )
        
        sorted_times = sorted(query_times)
        median = statistics.median(sorted_times)
        p95 = sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 1 else median
        success_rate = (len(query_times) / len(self.domains)) * 100
        
        result = DNSResult(
            resolver=resolver,
            median_ms=round(median, 2),
            p95_ms=round(p95, 2),
            success_rate=round(success_rate, 1),
            samples=len(self.domains)
        )
        
        self.logger.info(
            f"Resolver {resolver}: median={result.median_ms}ms, "
            f"p95={result.p95_ms}ms, success={result.success_rate}%"
        )
        
        return result
    
    def benchmark_all(self) -> List[DNSResult]:
        """
        Benchmark all configured resolvers.
        
        Returns:
            List of DNSResult, sorted by median latency
        """
        self.logger.info(f"Benchmarking {len(self.resolvers)} DNS resolvers")
        
        results = []
        for resolver in self.resolvers:
            result = self.benchmark_resolver(resolver)
            results.append(result)
        
        # Sort by median latency (best first)
        results.sort(key=lambda r: r.median_ms if r.median_ms > 0 else float('inf'))
        
        return results


def benchmark_dns(
    resolvers: List[str] = None,
    num_domains: int = 20
) -> List[DNSResult]:
    """
    Convenience function to benchmark DNS resolvers.
    
    Args:
        resolvers: List of DNS resolver IPs (uses Cloudflare and Google if None)
        num_domains: Number of test domains to use
    
    Returns:
        List of DNSResult sorted by performance
    """
    bench = DNSBenchmark(
        resolvers=resolvers,
        domains=DNSBenchmark.TEST_DOMAINS[:num_domains]
    )
    return bench.benchmark_all()
