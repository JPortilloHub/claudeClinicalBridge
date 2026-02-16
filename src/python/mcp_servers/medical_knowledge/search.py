"""
Semantic search engine for medical codes using Qdrant vector database.

Provides similarity-based search over ICD-10-CM and CPT codes using BioBERT embeddings.
Supports hierarchical code relationships and configurable search parameters.
"""

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class MedicalCodeSearch:
    """
    Semantic search engine for medical codes using Qdrant vector database.

    Supports search over ICD-10-CM diagnosis codes and CPT procedure codes
    using BioBERT embeddings for semantic similarity matching.
    """

    def __init__(
        self,
        qdrant_client: QdrantClient | None = None,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize the search engine.

        Args:
            qdrant_client: Qdrant client instance. If None, creates new client from settings.
            similarity_threshold: Minimum similarity score (0-1) for search results.
        """
        self.similarity_threshold = similarity_threshold

        # Initialize Qdrant client
        if qdrant_client:
            self.client = qdrant_client
        else:
            if settings.qdrant_api_key:
                # Remote Qdrant Cloud
                self.client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                )
            else:
                # Local Qdrant
                self.client = QdrantClient(url=settings.qdrant_url)

        logger.info(
            "Medical code search engine initialized",
            qdrant_url=settings.qdrant_url,
            similarity_threshold=similarity_threshold,
        )

    def _collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists in Qdrant.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.client.get_collection(collection_name)
            return True
        except (UnexpectedResponse, Exception) as e:
            logger.debug(
                "Collection does not exist",
                collection=collection_name,
                error=str(e),
            )
            return False

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 768,
        force_recreate: bool = False,
    ) -> None:
        """
        Create a new Qdrant collection for medical codes.

        Args:
            collection_name: Name of the collection (e.g., "icd10_codes", "cpt_codes")
            vector_size: Dimension of embedding vectors (BioBERT default: 768)
            force_recreate: If True, delete existing collection and recreate
        """
        if force_recreate and self._collection_exists(collection_name):
            logger.info("Deleting existing collection", collection=collection_name)
            self.client.delete_collection(collection_name)

        if self._collection_exists(collection_name):
            logger.info("Collection already exists", collection=collection_name)
            return

        logger.info(
            "Creating collection",
            collection=collection_name,
            vector_size=vector_size,
        )

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

        logger.info("Collection created successfully", collection=collection_name)

    def index_codes(
        self,
        collection_name: str,
        codes_with_embeddings: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Index medical codes with embeddings into Qdrant.

        Args:
            collection_name: Target collection name
            codes_with_embeddings: List of code dicts with "embedding" field
            batch_size: Number of codes to upload per batch

        Returns:
            Number of codes successfully indexed
        """
        if not self._collection_exists(collection_name):
            raise ValueError(
                f"Collection '{collection_name}' does not exist. "
                "Call create_collection() first."
            )

        logger.info(
            "Indexing codes",
            collection=collection_name,
            num_codes=len(codes_with_embeddings),
        )

        # Prepare points for Qdrant
        points = []
        for idx, code_data in enumerate(codes_with_embeddings):
            embedding = code_data.get("embedding")
            if not embedding:
                logger.warning("Code missing embedding, skipping", code=code_data.get("code"))
                continue

            # Create stable ID from code identifier to prevent collisions
            code_id = code_data.get("code", "")
            code_type = code_data.get("code_type", "unknown")

            # Generate stable hash-based ID
            stable_id = hashlib.sha256(f"{code_type}:{code_id}".encode()).hexdigest()
            # Convert to integer ID (Qdrant requires int or UUID)
            # Use first 16 hex chars and convert to int, then modulo to fit in int64 range
            numeric_id = int(stable_id[:16], 16) % (2**63 - 1)

            # Create payload without embedding (stored separately in vector)
            payload = {k: v for k, v in code_data.items() if k != "embedding"}

            point = models.PointStruct(
                id=numeric_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Upload in batches
        total_indexed = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch,
                )
                total_indexed += len(batch)
                logger.debug(
                    "Batch indexed",
                    collection=collection_name,
                    batch_num=i // batch_size + 1,
                    batch_size=len(batch),
                )
            except Exception as e:
                logger.error(
                    "Failed to index batch",
                    collection=collection_name,
                    batch_num=i // batch_size + 1,
                    error=str(e),
                )
                raise

        logger.info(
            "Indexing complete",
            collection=collection_name,
            total_indexed=total_indexed,
        )

        return total_indexed

    def search(
        self,
        collection_name: str,
        query_vector: list[float] | np.ndarray,
        limit: int = 10,
        score_threshold: float | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar medical codes using embedding vector.

        Args:
            collection_name: Collection to search ("icd10_codes" or "cpt_codes")
            query_vector: Query embedding vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (overrides instance threshold if provided)
            filter_conditions: Optional Qdrant filter conditions

        Returns:
            List of matching codes with scores and metadata
        """
        if not self._collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist")

        threshold = score_threshold if score_threshold is not None else self.similarity_threshold

        # Convert numpy array to list if needed
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        logger.debug(
            "Searching codes",
            collection=collection_name,
            limit=limit,
            threshold=threshold,
        )

        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=threshold,
                query_filter=filter_conditions,
            )

            # Format results
            formatted_results = []
            for result in results:
                code_data = result.payload.copy()
                code_data["similarity_score"] = result.score
                formatted_results.append(code_data)

            logger.info(
                "Search complete",
                collection=collection_name,
                num_results=len(formatted_results),
            )

            return formatted_results

        except Exception as e:
            logger.error(
                "Search failed",
                collection=collection_name,
                error=str(e),
            )
            raise

    def search_by_text(
        self,
        code_type: str,
        query_text: str,
        embedder,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for medical codes using natural language query.

        Args:
            code_type: Type of code ("icd10" or "cpt")
            query_text: Natural language query (e.g., "high blood sugar")
            embedder: MedicalCodeEmbedder instance to generate query embedding
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching codes with scores
        """
        # Validate code type
        if code_type not in ("icd10", "cpt"):
            raise ValueError(f"code_type must be 'icd10' or 'cpt', got: {code_type}")

        collection_name = f"{code_type}_codes"

        # Generate embedding for query text
        query_embedding = embedder.generate_embedding(query_text)

        # Search
        results = self.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
        )

        return results

    def get_code_by_id(
        self,
        collection_name: str,
        code: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve exact code by code identifier.

        Args:
            collection_name: Collection to search
            code: Exact code identifier (e.g., "E11.9", "99214")

        Returns:
            Code data if found, None otherwise
        """
        if not self._collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist")

        logger.debug("Looking up code", collection=collection_name, code=code)

        try:
            # Search with exact match filter
            results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="code",
                            match=models.MatchValue(value=code),
                        )
                    ]
                ),
                limit=1,
            )

            # Defensive unpacking of results tuple
            points, next_offset = results if results and len(results) == 2 else ([], None)

            if points and len(points) > 0:
                point = points[0]
                return point.payload
            else:
                logger.warning("Code not found", collection=collection_name, code=code)
                return None

        except Exception as e:
            logger.error(
                "Code lookup failed",
                collection=collection_name,
                code=code,
                error=str(e),
            )
            raise

    def get_code_hierarchy(
        self,
        collection_name: str,
        code: str,
    ) -> dict[str, Any]:
        """
        Get hierarchical information for a code (parent and children).

        For ICD-10, codes have parent-child relationships:
        - E11 (parent) -> E11.9, E11.65, E11.22 (children)

        Args:
            collection_name: Collection to search
            code: Code identifier

        Returns:
            Dictionary with code, parent, and children information
        """
        # Get the code itself
        code_data = self.get_code_by_id(collection_name, code)
        if not code_data:
            return {"code": code, "found": False}

        result = {
            "code": code,
            "found": True,
            "data": code_data,
            "parent": None,
            "children": [],
        }

        # Get parent if exists
        parent_code = code_data.get("parent_code")
        if parent_code:
            parent_data = self.get_code_by_id(collection_name, parent_code)
            result["parent"] = parent_data

        # Get children (codes with this code as parent)
        try:
            children_results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="parent_code",
                            match=models.MatchValue(value=code),
                        )
                    ]
                ),
                limit=100,  # Reasonable limit for children
            )

            # Defensive unpacking of results tuple
            children_points, _ = children_results if children_results and len(children_results) == 2 else ([], None)

            if children_points and len(children_points) > 0:
                result["children"] = [point.payload for point in children_points]

        except Exception as e:
            logger.warning(
                "Failed to get children codes",
                collection=collection_name,
                code=code,
                error=str(e),
            )

        return result

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """
        Get statistics about a collection.

        Args:
            collection_name: Collection name

        Returns:
            Dictionary with collection statistics
        """
        if not self._collection_exists(collection_name):
            return {"exists": False}

        try:
            collection_info = self.client.get_collection(collection_name)

            return {
                "exists": True,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        except Exception as e:
            logger.error(
                "Failed to get collection stats",
                collection=collection_name,
                error=str(e),
            )
            raise


# Convenience function for quick search
def search_medical_codes(
    query: str,
    code_type: str = "icd10",
    limit: int = 10,
    similarity_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """
    Quick search function for medical codes.

    Args:
        query: Natural language query
        code_type: "icd10" or "cpt"
        limit: Maximum results
        similarity_threshold: Minimum similarity score

    Returns:
        List of matching codes
    """
    from .embeddings import MedicalCodeEmbedder

    # Initialize components
    embedder = MedicalCodeEmbedder()
    search_engine = MedicalCodeSearch(similarity_threshold=similarity_threshold)

    # Search
    results = search_engine.search_by_text(
        code_type=code_type,
        query_text=query,
        embedder=embedder,
        limit=limit,
    )

    return results


# Example usage
if __name__ == "__main__":
    import sys

    # Test search
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Searching for: {query}")

        results = search_medical_codes(query, code_type="icd10", limit=5)

        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['code']}: {result['description']}")
            print(f"   Similarity: {result['similarity_score']:.3f}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print()
    else:
        print("Usage: python -m src.python.mcp_servers.medical_knowledge.search <query>")
        print("Example: python -m src.python.mcp_servers.medical_knowledge.search 'high blood sugar'")
