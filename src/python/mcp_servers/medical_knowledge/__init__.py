"""
Medical Knowledge Base MCP Server Package.

Provides semantic search over ICD-10-CM diagnosis codes and CPT procedure codes
using BioBERT embeddings and Qdrant vector database.

Main Components:
- MedicalCodeEmbedder: Generate BioBERT embeddings for medical codes
- MedicalCodeSearch: Semantic search engine with Qdrant
- FastMCP Server: MCP server exposing search tools

Usage:
    from src.python.mcp_servers.medical_knowledge import (
        MedicalCodeEmbedder,
        MedicalCodeSearch,
        search_medical_codes,
    )

    # Quick search
    results = search_medical_codes("high blood sugar", code_type="icd10")

    # Advanced usage
    embedder = MedicalCodeEmbedder()
    search_engine = MedicalCodeSearch()
    results = search_engine.search_by_text("icd10", "diabetes", embedder)
"""

from .embeddings import MedicalCodeEmbedder, load_and_embed_codes
from .search import MedicalCodeSearch, search_medical_codes

__all__ = [
    "MedicalCodeEmbedder",
    "MedicalCodeSearch",
    "load_and_embed_codes",
    "search_medical_codes",
]

__version__ = "0.1.0"
