"""
Medical Knowledge Base MCP Server.

Provides semantic search over ICD-10-CM diagnosis codes and CPT procedure codes
using BioBERT embeddings. Enables LLM agents to find relevant medical codes
based on natural language clinical descriptions.

Tools:
- search_icd10: Search ICD-10 diagnosis codes
- search_cpt: Search CPT procedure codes
- get_code_details: Get detailed information about a specific code
- get_code_hierarchy: Get parent/child code relationships

Resources:
- code://{code_type}/{code}: Individual code lookup
"""

import threading
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.python.utils.logging import get_logger

from .embeddings import MedicalCodeEmbedder
from .search import MedicalCodeSearch

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("medical-knowledge")

# Initialize embedder and search engine (lazy loading with thread safety)
_embedder: MedicalCodeEmbedder | None = None
_search_engine: MedicalCodeSearch | None = None
_embedder_lock = threading.Lock()
_search_lock = threading.Lock()


def get_embedder() -> MedicalCodeEmbedder:
    """Get or create embedder instance (lazy initialization, thread-safe)."""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            # Double-check locking pattern
            if _embedder is None:
                logger.info("Initializing MedicalCodeEmbedder")
                _embedder = MedicalCodeEmbedder()
    return _embedder


def get_search_engine() -> MedicalCodeSearch:
    """Get or create search engine instance (lazy initialization, thread-safe)."""
    global _search_engine
    if _search_engine is None:
        with _search_lock:
            # Double-check locking pattern
            if _search_engine is None:
                logger.info("Initializing MedicalCodeSearch")
                _search_engine = MedicalCodeSearch()
    return _search_engine


@mcp.tool()
async def search_icd10(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """
    Search ICD-10-CM diagnosis codes by clinical description.

    Uses semantic search with BioBERT embeddings to find relevant diagnosis codes
    based on natural language queries. Returns codes ranked by similarity score.

    Args:
        query: Natural language clinical description
               (e.g., "high blood sugar", "chest pain", "type 2 diabetes")
        limit: Maximum number of results to return (default: 10, max: 50)
        similarity_threshold: Minimum similarity score 0-1 (default: 0.7)
                             Higher values return more precise matches

    Returns:
        List of matching ICD-10 codes with details:
        - code: ICD-10-CM code (e.g., "E11.9")
        - description: Full code description
        - category: Medical category
        - keywords: Relevant keywords
        - similarity_score: Similarity to query (0-1)
        - billable: Whether code is billable
        - parent_code: Parent code if hierarchical

    Example:
        >>> search_icd10("diabetes with high blood sugar", limit=5)
        [
            {
                "code": "E11.65",
                "description": "Type 2 diabetes mellitus with hyperglycemia",
                "similarity_score": 0.92,
                ...
            }
        ]
    """
    # Validate parameters
    if not query or not query.strip():
        logger.warning("Empty query provided to search_icd10")
        return []

    # Validate query length
    MAX_QUERY_LENGTH = 1000
    if len(query) > MAX_QUERY_LENGTH:
        logger.warning(
            "Query too long, truncating",
            original_length=len(query),
            max_length=MAX_QUERY_LENGTH,
        )
        query = query[:MAX_QUERY_LENGTH]

    if limit < 1:
        limit = 1
    elif limit > 50:
        logger.warning("Limit capped at 50", requested_limit=limit)
        limit = 50

    if similarity_threshold < 0:
        similarity_threshold = 0
    elif similarity_threshold > 1:
        similarity_threshold = 1

    logger.info(
        "ICD-10 search request",
        query=query[:100],
        limit=limit,
        threshold=similarity_threshold,
    )

    try:
        embedder = get_embedder()
        search_engine = get_search_engine()

        results = search_engine.search_by_text(
            code_type="icd10",
            query_text=query,
            embedder=embedder,
            limit=limit,
            score_threshold=similarity_threshold,
        )

        logger.info("ICD-10 search completed", num_results=len(results))
        return results

    except Exception as e:
        logger.error("ICD-10 search failed", query=query, error=str(e))
        raise


@mcp.tool()
async def search_cpt(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """
    Search CPT procedure codes by procedure description.

    Uses semantic search with BioBERT embeddings to find relevant procedure codes
    based on natural language queries. Returns codes ranked by similarity score.

    Args:
        query: Natural language procedure description
               (e.g., "office visit", "blood test", "MRI brain")
        limit: Maximum number of results to return (default: 10, max: 50)
        similarity_threshold: Minimum similarity score 0-1 (default: 0.7)

    Returns:
        List of matching CPT codes with details:
        - code: CPT code (e.g., "99214")
        - description: Full procedure description
        - category: Procedure category
        - keywords: Relevant keywords
        - similarity_score: Similarity to query (0-1)
        - typical_duration: Typical procedure duration if applicable
        - work_rvu: Work RVU value if available

    Example:
        >>> search_cpt("routine office visit", limit=5)
        [
            {
                "code": "99214",
                "description": "Office or other outpatient visit...",
                "similarity_score": 0.89,
                ...
            }
        ]
    """
    # Validate parameters
    if not query or not query.strip():
        logger.warning("Empty query provided to search_cpt")
        return []

    # Validate query length
    MAX_QUERY_LENGTH = 1000
    if len(query) > MAX_QUERY_LENGTH:
        logger.warning(
            "Query too long, truncating",
            original_length=len(query),
            max_length=MAX_QUERY_LENGTH,
        )
        query = query[:MAX_QUERY_LENGTH]

    if limit < 1:
        limit = 1
    elif limit > 50:
        logger.warning("Limit capped at 50", requested_limit=limit)
        limit = 50

    if similarity_threshold < 0:
        similarity_threshold = 0
    elif similarity_threshold > 1:
        similarity_threshold = 1

    logger.info(
        "CPT search request",
        query=query[:100],
        limit=limit,
        threshold=similarity_threshold,
    )

    try:
        embedder = get_embedder()
        search_engine = get_search_engine()

        results = search_engine.search_by_text(
            code_type="cpt",
            query_text=query,
            embedder=embedder,
            limit=limit,
            score_threshold=similarity_threshold,
        )

        logger.info("CPT search completed", num_results=len(results))
        return results

    except Exception as e:
        logger.error("CPT search failed", query=query, error=str(e))
        raise


@mcp.tool()
async def get_code_details(
    code_type: str,
    code: str,
) -> dict[str, Any] | None:
    """
    Get full details for a specific ICD-10 or CPT code.

    Performs exact code lookup to retrieve complete information about a medical code.

    Args:
        code_type: Type of code - "icd10" or "cpt"
        code: Exact code identifier (e.g., "E11.9", "99214")

    Returns:
        Code details dictionary if found, None if not found:
        - code: The code identifier
        - description: Full description
        - category: Medical/procedure category
        - keywords: Associated keywords
        - Additional fields specific to code type

    Example:
        >>> get_code_details("icd10", "E11.9")
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "category": "Endocrine, nutritional and metabolic diseases",
            "billable": true,
            ...
        }
    """
    # Validate parameters
    if code_type not in ("icd10", "cpt"):
        logger.warning("Invalid code_type", code_type=code_type)
        raise ValueError(f"code_type must be 'icd10' or 'cpt', got: {code_type}")

    if not code or not code.strip():
        logger.warning("Empty code provided")
        return None

    # Normalize code: preserve case for ICD-10, uppercase for CPT
    code = code.strip()
    if code_type == "cpt":
        code = code.upper()  # CPT codes are numeric, safe to uppercase
    # ICD-10 codes: preserve original case (e.g., "E11.9")

    collection_name = f"{code_type}_codes"

    logger.info("Code details request", code_type=code_type, code=code)

    try:
        search_engine = get_search_engine()
        result = search_engine.get_code_by_id(collection_name, code)

        if result:
            logger.info("Code found", code_type=code_type, code=code)
        else:
            logger.info("Code not found", code_type=code_type, code=code)

        return result

    except Exception as e:
        logger.error(
            "Code lookup failed",
            code_type=code_type,
            code=code,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_code_hierarchy(
    code_type: str,
    code: str,
) -> dict[str, Any]:
    """
    Get hierarchical code relationships (parent and children).

    For ICD-10 codes with hierarchical structure, returns the parent code
    and all child codes. Useful for understanding code specificity and
    related diagnoses.

    Args:
        code_type: Type of code - "icd10" or "cpt"
        code: Code identifier (e.g., "E11" for diabetes parent)

    Returns:
        Dictionary containing:
        - code: The queried code
        - found: Whether code exists
        - data: Full code details
        - parent: Parent code details if exists
        - children: List of child code details

    Example:
        >>> get_code_hierarchy("icd10", "E11")
        {
            "code": "E11",
            "found": true,
            "data": {...},
            "parent": {...},
            "children": [
                {"code": "E11.9", ...},
                {"code": "E11.65", ...},
                ...
            ]
        }
    """
    # Validate parameters
    if code_type not in ("icd10", "cpt"):
        logger.warning("Invalid code_type", code_type=code_type)
        raise ValueError(f"code_type must be 'icd10' or 'cpt', got: {code_type}")

    if not code or not code.strip():
        logger.warning("Empty code provided")
        return {"code": code, "found": False, "error": "Empty code"}

    # Normalize code: preserve case for ICD-10, uppercase for CPT
    code = code.strip()
    if code_type == "cpt":
        code = code.upper()  # CPT codes are numeric, safe to uppercase
    # ICD-10 codes: preserve original case (e.g., "E11.9")

    collection_name = f"{code_type}_codes"

    logger.info("Code hierarchy request", code_type=code_type, code=code)

    try:
        search_engine = get_search_engine()
        hierarchy = search_engine.get_code_hierarchy(collection_name, code)

        logger.info(
            "Code hierarchy retrieved",
            code_type=code_type,
            code=code,
            found=hierarchy.get("found", False),
            num_children=len(hierarchy.get("children", [])),
        )

        return hierarchy

    except Exception as e:
        logger.error(
            "Code hierarchy lookup failed",
            code_type=code_type,
            code=code,
            error=str(e),
        )
        raise


@mcp.tool()
async def get_collection_stats(
    code_type: str,
) -> dict[str, Any]:
    """
    Get statistics about the medical code collection.

    Returns information about the size and status of the ICD-10 or CPT
    code collection in the vector database.

    Args:
        code_type: Type of code collection - "icd10" or "cpt"

    Returns:
        Statistics dictionary:
        - exists: Whether collection exists
        - vectors_count: Number of indexed vectors
        - points_count: Number of code entries
        - status: Collection status

    Example:
        >>> get_collection_stats("icd10")
        {
            "exists": true,
            "vectors_count": 35,
            "points_count": 35,
            "status": "green"
        }
    """
    # Validate parameters
    if code_type not in ("icd10", "cpt"):
        raise ValueError(f"code_type must be 'icd10' or 'cpt', got: {code_type}")

    collection_name = f"{code_type}_codes"

    logger.info("Collection stats request", code_type=code_type)

    try:
        search_engine = get_search_engine()
        stats = search_engine.get_collection_stats(collection_name)

        logger.info("Collection stats retrieved", code_type=code_type, stats=stats)
        return stats

    except Exception as e:
        logger.error(
            "Collection stats failed",
            code_type=code_type,
            error=str(e),
        )
        raise


@mcp.resource("code://{code_type}/{code}")
async def code_resource(code_type: str, code: str) -> str:
    """
    MCP resource for code lookup.

    Provides a resource URI pattern for accessing medical codes:
    - code://icd10/E11.9
    - code://cpt/99214

    Args:
        code_type: "icd10" or "cpt"
        code: Code identifier

    Returns:
        Formatted code details as string
    """
    logger.info("Code resource request", code_type=code_type, code=code)

    result = await get_code_details(code_type, code)

    if result is None:
        return f"Code not found: {code_type.upper()} {code}"

    # Format as readable text
    lines = [
        f"Code: {result.get('code')}",
        f"Type: {code_type.upper()}",
        f"Description: {result.get('description')}",
        f"Category: {result.get('category', 'N/A')}",
    ]

    if keywords := result.get("keywords"):
        lines.append(f"Keywords: {', '.join(keywords)}")

    if "billable" in result:
        lines.append(f"Billable: {'Yes' if result['billable'] else 'No'}")

    if parent := result.get("parent_code"):
        lines.append(f"Parent Code: {parent}")

    return "\n".join(lines)


# Server lifecycle hooks
@mcp.server_init()
async def init():
    """Initialize server and warm up components."""
    logger.info("Medical Knowledge MCP Server initializing")

    # Warm up embedder and search engine
    try:
        embedder = get_embedder()
        logger.info(
            "Embedder ready",
            model=embedder.model_name,
            embedding_dim=embedder.embedding_dim,
        )

        search_engine = get_search_engine()
        logger.info("Search engine ready")

        # Log collection status
        for code_type in ["icd10", "cpt"]:
            stats = await get_collection_stats(code_type)
            logger.info(f"{code_type.upper()} collection status", **stats)

    except Exception as e:
        logger.error("Server initialization failed", error=str(e))
        raise

    logger.info("Medical Knowledge MCP Server initialized successfully")


# Run server
if __name__ == "__main__":
    import asyncio

    logger.info("Starting Medical Knowledge MCP Server")

    try:
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
