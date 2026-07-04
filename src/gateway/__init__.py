"""Upstream HTTP clients — ONLY place that calls KB-IHMS or EC-OPS."""

from src.gateway.ecops_client import EcOpsClient
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

__all__ = ["EcOpsClient", "IhmsClient", "ObservabilityHeaders"]
