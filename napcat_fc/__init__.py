"""NapCat / OneBot function tools for AstrBot."""

from napcat_fc.client import NapCatClient, NapCatClientConfig
from napcat_fc.registry import (
    EndpointSpec,
    discover_all_endpoint_specs,
    discover_endpoint_specs,
)

__all__ = [
    "EndpointSpec",
    "NapCatClient",
    "NapCatClientConfig",
    "discover_all_endpoint_specs",
    "discover_endpoint_specs",
]
