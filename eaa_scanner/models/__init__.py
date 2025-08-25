"""
Enterprise-grade data models for EAA Scanner
Type-safe Pydantic models for validation and serialization
"""

from .scanner_results import (
    ScannerResult,
    ViolationInstance,
    AggregatedResults,
    ComplianceMetrics,
    ScannerMetadata,
    ScanContext
)

__all__ = [
    "ScannerResult", 
    "ViolationInstance", 
    "AggregatedResults", 
    "ComplianceMetrics",
    "ScannerMetadata",
    "ScanContext"
]