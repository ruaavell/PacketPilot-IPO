"""JSON schema definitions and validation for benchmark data."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class BufferbloatGrade(str, Enum):
    """Bufferbloat quality grades."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ICMPResult(BaseModel):
    """ICMP ping test results."""
    samples: int = Field(..., ge=1, description="Number of ping samples")
    p50: float = Field(..., ge=0, description="50th percentile latency (ms)")
    p90: float = Field(..., ge=0, description="90th percentile latency (ms)")
    p95: float = Field(..., ge=0, description="95th percentile latency (ms)")
    p99: float = Field(..., ge=0, description="99th percentile latency (ms)")
    min: float = Field(..., ge=0, description="Minimum latency (ms)")
    max: float = Field(..., ge=0, description="Maximum latency (ms)")
    mean: float = Field(..., ge=0, description="Mean latency (ms)")
    stddev: float = Field(..., ge=0, description="Standard deviation (ms)")
    packet_loss: float = Field(..., ge=0, le=100, description="Packet loss percentage")
    raw_samples: List[float] = Field(default_factory=list, description="Raw latency samples")


class JitterResult(BaseModel):
    """UDP jitter test results."""
    mean_jitter_ms: float = Field(..., ge=0, description="Mean jitter (ms)")
    max_jitter_ms: float = Field(..., ge=0, description="Max jitter (ms)")
    packet_loss: float = Field(..., ge=0, le=100, description="Packet loss percentage")
    out_of_order: int = Field(..., ge=0, description="Out-of-order packets")


class ThroughputResult(BaseModel):
    """TCP throughput test results."""
    download_mbps: float = Field(..., ge=0, description="Download speed (Mbps)")
    upload_mbps: float = Field(..., ge=0, description="Upload speed (Mbps)")
    retransmits: int = Field(..., ge=0, description="Number of retransmissions")


class BufferbloatResult(BaseModel):
    """Bufferbloat test results."""
    idle_latency_ms: float = Field(..., ge=0, description="Baseline latency (ms)")
    loaded_latency_ms: float = Field(..., ge=0, description="Latency under load (ms)")
    latency_increase_ms: float = Field(..., ge=0, description="Additional latency (ms)")
    latency_increase_pct: float = Field(..., ge=0, description="Percentage increase")
    grade: BufferbloatGrade = Field(..., description="Quality grade")
    
    @field_validator('latency_increase_ms', mode='before')
    @classmethod
    def compute_increase(cls, v: Any, info: Any) -> float:
        """Compute latency increase if not provided."""
        if v is not None:
            return v
        values = info.data
        return values.get('loaded_latency_ms', 0) - values.get('idle_latency_ms', 0)


class DNSResult(BaseModel):
    """DNS resolver benchmark results."""
    resolver: str = Field(..., description="DNS resolver address")
    median_ms: float = Field(..., ge=0, description="Median query time (ms)")
    p95_ms: float = Field(..., ge=0, description="95th percentile (ms)")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate (%)")
    samples: int = Field(..., ge=1, description="Number of queries")


class BenchmarkResult(BaseModel):
    """Complete benchmark results."""
    timestamp: datetime = Field(default_factory=datetime.now, description="Benchmark timestamp")
    target: str = Field(..., description="Target host for testing")
    system_info: Dict[str, Any] = Field(default_factory=dict, description="System information")
    icmp: ICMPResult = Field(..., description="ICMP ping results")
    jitter: JitterResult = Field(..., description="UDP jitter results")
    throughput: ThroughputResult = Field(..., description="TCP throughput results")
    bufferbloat: BufferbloatResult = Field(..., description="Bufferbloat results")
    dns: List[DNSResult] = Field(default_factory=list, description="DNS resolver results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Recommendation(BaseModel):
    """Network optimization recommendation."""
    id: str = Field(..., description="Unique recommendation ID")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")
    confidence: str = Field(..., description="Confidence level (high/medium/low)")
    estimated_impact: str = Field(..., description="Expected improvement")
    category: str = Field(..., description="Category (NIC/Router/DNS/System)")
    commands: List[str] = Field(default_factory=list, description="Commands to execute")
    rollback_commands: List[str] = Field(default_factory=list, description="Rollback commands")
    requires_admin: bool = Field(default=False, description="Requires admin privileges")
    reversible: bool = Field(default=True, description="Can be reversed")
    risk_level: str = Field(default="low", description="Risk level (low/medium/high)")


class ApplyResult(BaseModel):
    """Result of applying a change."""
    success: bool = Field(..., description="Whether operation succeeded")
    recommendation_id: str = Field(..., description="ID of applied recommendation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Application timestamp")
    before_state: Dict[str, Any] = Field(default_factory=dict, description="State before change")
    after_state: Dict[str, Any] = Field(default_factory=dict, description="State after change")
    verification: Dict[str, Any] = Field(default_factory=dict, description="Verification results")
    backup_path: str = Field(..., description="Path to backup file")
    rollback_script: str = Field(..., description="Path to rollback script")
    error_message: str = Field(default="", description="Error message if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def calculate_bufferbloat_grade(latency_increase_ms: float) -> BufferbloatGrade:
    """
    Calculate bufferbloat grade based on latency increase under load.
    
    Based on DSLReports bufferbloat grading:
    - A+: < 10ms
    - A: < 30ms
    - B: < 100ms
    - C: < 200ms
    - D: < 400ms
    - F: >= 400ms
    
    Args:
        latency_increase_ms: Additional latency under load (ms)
    
    Returns:
        BufferbloatGrade enum value
    """
    if latency_increase_ms < 10:
        return BufferbloatGrade.A_PLUS
    elif latency_increase_ms < 30:
        return BufferbloatGrade.A
    elif latency_increase_ms < 100:
        return BufferbloatGrade.B
    elif latency_increase_ms < 200:
        return BufferbloatGrade.C
    elif latency_increase_ms < 400:
        return BufferbloatGrade.D
    else:
        return BufferbloatGrade.F
