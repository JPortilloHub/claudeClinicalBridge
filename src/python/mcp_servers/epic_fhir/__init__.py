"""
Epic FHIR MCP Server Package.

Provides FHIR R4 integration with Epic EHR systems using SMART on FHIR.
"""

from .client import EpicFHIRClient, get_epic_patient

__all__ = ["EpicFHIRClient", "get_epic_patient"]

__version__ = "0.1.0"
