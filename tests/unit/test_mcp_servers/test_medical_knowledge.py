"""
Unit tests for Medical Knowledge Base MCP Server.

Tests embedding generation, semantic search, and MCP server tools.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

np = pytest.importorskip("numpy", reason="numpy not installed")
pytest.importorskip("qdrant_client", reason="qdrant-client not installed")

from qdrant_client.http import models

from src.python.mcp_servers.medical_knowledge.embeddings import (
    MedicalCodeEmbedder,
    load_and_embed_codes,
)
from src.python.mcp_servers.medical_knowledge.search import MedicalCodeSearch
from src.python.mcp_servers.medical_knowledge.server import (
    get_code_details,
    get_code_hierarchy,
    search_cpt,
    search_icd10,
)


@pytest.fixture
def sample_icd10_code():
    """Sample ICD-10 code for testing."""
    return {
        "code": "E11.9",
        "description": "Type 2 diabetes mellitus without complications",
        "category": "Endocrine, nutritional and metabolic diseases",
        "parent_code": "E11",
        "billable": True,
        "keywords": [
            "diabetes",
            "type 2",
            "mellitus",
            "hyperglycemia",
            "blood sugar",
        ],
    }


@pytest.fixture
def sample_cpt_code():
    """Sample CPT code for testing."""
    return {
        "code": "99214",
        "description": "Office or other outpatient visit for E/M of established patient",
        "category": "Evaluation and Management",
        "keywords": ["office visit", "established patient", "E&M"],
    }


@pytest.fixture
def mock_embedder():
    """Mock MedicalCodeEmbedder for testing."""
    embedder = Mock(spec=MedicalCodeEmbedder)
    embedder.model_name = "test-model"
    embedder.embedding_dim = 768
    embedder.generate_embedding = Mock(return_value=np.random.rand(768).astype(np.float32))
    return embedder


@pytest.fixture
def mock_search_engine():
    """Mock MedicalCodeSearch for testing."""
    search_engine = Mock(spec=MedicalCodeSearch)
    return search_engine


class TestMedicalCodeEmbedder:
    """Test cases for MedicalCodeEmbedder."""

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_embedder_initialization(self, mock_transformer):
        """Test embedder initializes correctly."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()

        assert embedder.model is not None
        assert embedder.embedding_dim == 768
        mock_transformer.assert_called_once()

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_generate_embedding(self, mock_transformer):
        """Test embedding generation for single text."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.random.rand(768)
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()
        embedding = embedder.generate_embedding("diabetes")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert embedding.dtype == np.float32

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_generate_embedding_empty_text(self, mock_transformer):
        """Test embedding generation handles empty text."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()
        embedding = embedder.generate_embedding("")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert np.all(embedding == 0)  # Should return zero vector

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_embed_medical_code(self, mock_transformer, sample_icd10_code):
        """Test embedding a medical code with metadata."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.random.rand(768)
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()
        enriched = embedder.embed_medical_code(sample_icd10_code)

        assert "embedding" in enriched
        assert "composite_text" in enriched
        assert "embedding_model" in enriched
        assert len(enriched["embedding"]) == 768
        assert "Type 2 diabetes" in enriched["composite_text"]
        assert "Keywords:" in enriched["composite_text"]

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_embed_codes_batch(self, mock_transformer, sample_icd10_code, sample_cpt_code):
        """Test batch embedding generation."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.random.rand(2, 768)
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()
        codes = [sample_icd10_code, sample_cpt_code]
        enriched_codes = embedder.embed_medical_codes_batch(codes)

        assert len(enriched_codes) == 2
        assert all("embedding" in code for code in enriched_codes)
        assert all(len(code["embedding"]) == 768 for code in enriched_codes)

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    def test_batch_size_limiting(self, mock_transformer):
        """Test large batch is chunked to prevent OOM."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        # Return array matching input size
        mock_model.encode.side_effect = lambda texts, **kwargs: np.random.rand(len(texts), 768)
        mock_transformer.return_value = mock_model

        embedder = MedicalCodeEmbedder()

        # Create 15000 texts (should trigger chunking at 10000)
        texts = [f"text {i}" for i in range(15000)]
        embeddings = embedder.generate_embeddings_batch(texts)

        assert embeddings.shape == (15000, 768)
        # Should have called encode twice (10000 + 5000)
        assert mock_model.encode.call_count == 2


class TestMedicalCodeSearch:
    """Test cases for MedicalCodeSearch."""

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_search_engine_initialization(self, mock_qdrant):
        """Test search engine initializes correctly."""
        search_engine = MedicalCodeSearch()
        assert search_engine.client is not None
        assert search_engine.similarity_threshold == 0.7

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_collection_exists(self, mock_qdrant):
        """Test collection existence check."""
        mock_client = Mock()
        mock_client.get_collection.return_value = Mock()
        mock_qdrant.return_value = mock_client

        search_engine = MedicalCodeSearch()
        exists = search_engine._collection_exists("icd10_codes")

        assert exists is True
        mock_client.get_collection.assert_called_once_with("icd10_codes")

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_create_collection(self, mock_qdrant):
        """Test collection creation."""
        mock_client = Mock()
        mock_client.get_collection.side_effect = Exception("Not found")
        mock_qdrant.return_value = mock_client

        search_engine = MedicalCodeSearch()
        search_engine.create_collection("test_collection", vector_size=768)

        mock_client.create_collection.assert_called_once()

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_search(self, mock_qdrant, sample_icd10_code):
        """Test semantic search."""
        mock_client = Mock()

        # Mock search results
        mock_result = Mock()
        mock_result.payload = sample_icd10_code
        mock_result.score = 0.95
        mock_client.search.return_value = [mock_result]
        mock_client.get_collection.return_value = Mock()
        mock_qdrant.return_value = mock_client

        search_engine = MedicalCodeSearch()
        query_vector = np.random.rand(768)
        results = search_engine.search("icd10_codes", query_vector, limit=10)

        assert len(results) == 1
        assert results[0]["code"] == "E11.9"
        assert results[0]["similarity_score"] == 0.95
        mock_client.search.assert_called_once()

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_get_code_by_id(self, mock_qdrant, sample_icd10_code):
        """Test exact code lookup."""
        mock_client = Mock()

        # Mock scroll results
        mock_point = Mock()
        mock_point.payload = sample_icd10_code
        mock_client.scroll.return_value = ([mock_point], None)
        mock_client.get_collection.return_value = Mock()
        mock_qdrant.return_value = mock_client

        search_engine = MedicalCodeSearch()
        result = search_engine.get_code_by_id("icd10_codes", "E11.9")

        assert result is not None
        assert result["code"] == "E11.9"
        assert result["description"] == "Type 2 diabetes mellitus without complications"

    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_get_code_hierarchy(self, mock_qdrant, sample_icd10_code):
        """Test code hierarchy retrieval."""
        mock_client = Mock()

        # Mock code lookup
        mock_point = Mock()
        mock_point.payload = sample_icd10_code
        mock_client.scroll.return_value = ([mock_point], None)
        mock_client.get_collection.return_value = Mock()
        mock_qdrant.return_value = mock_client

        search_engine = MedicalCodeSearch()
        hierarchy = search_engine.get_code_hierarchy("icd10_codes", "E11.9")

        assert hierarchy["found"] is True
        assert hierarchy["code"] == "E11.9"
        assert "data" in hierarchy
        assert "parent" in hierarchy
        assert "children" in hierarchy


class TestMCPServerTools:
    """Test cases for MCP server tools."""

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    @patch("src.python.mcp_servers.medical_knowledge.server.get_embedder")
    async def test_search_icd10_tool(
        self, mock_get_embedder, mock_get_search_engine, mock_embedder, sample_icd10_code
    ):
        """Test search_icd10 MCP tool."""
        mock_get_embedder.return_value = mock_embedder

        mock_search = Mock()
        mock_search.search_by_text.return_value = [
            {**sample_icd10_code, "similarity_score": 0.92}
        ]
        mock_get_search_engine.return_value = mock_search

        results = await search_icd10("diabetes", limit=5)

        assert len(results) == 1
        assert results[0]["code"] == "E11.9"
        assert results[0]["similarity_score"] == 0.92

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    @patch("src.python.mcp_servers.medical_knowledge.server.get_embedder")
    async def test_search_cpt_tool(
        self, mock_get_embedder, mock_get_search_engine, mock_embedder, sample_cpt_code
    ):
        """Test search_cpt MCP tool."""
        mock_get_embedder.return_value = mock_embedder

        mock_search = Mock()
        mock_search.search_by_text.return_value = [
            {**sample_cpt_code, "similarity_score": 0.89}
        ]
        mock_get_search_engine.return_value = mock_search

        results = await search_cpt("office visit", limit=5)

        assert len(results) == 1
        assert results[0]["code"] == "99214"
        assert results[0]["similarity_score"] == 0.89

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    async def test_get_code_details_tool(
        self, mock_get_search_engine, sample_icd10_code
    ):
        """Test get_code_details MCP tool."""
        mock_search = Mock()
        mock_search.get_code_by_id.return_value = sample_icd10_code
        mock_get_search_engine.return_value = mock_search

        result = await get_code_details("icd10", "E11.9")

        assert result is not None
        assert result["code"] == "E11.9"
        assert "description" in result

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    async def test_get_code_hierarchy_tool(
        self, mock_get_search_engine, sample_icd10_code
    ):
        """Test get_code_hierarchy MCP tool."""
        mock_search = Mock()
        mock_search.get_code_hierarchy.return_value = {
            "code": "E11.9",
            "found": True,
            "data": sample_icd10_code,
            "parent": None,
            "children": [],
        }
        mock_get_search_engine.return_value = mock_search

        result = await get_code_hierarchy("icd10", "E11.9")

        assert result["found"] is True
        assert result["code"] == "E11.9"

    @pytest.mark.asyncio
    async def test_search_icd10_empty_query(self):
        """Test search_icd10 with empty query."""
        results = await search_icd10("", limit=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_icd10_limit_validation(self):
        """Test search_icd10 limit parameter validation."""
        with patch("src.python.mcp_servers.medical_knowledge.server.get_embedder"):
            with patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine"):
                # Limit too low
                results = await search_icd10("test", limit=-5)
                # Should not raise error, should clamp to 1

                # Limit too high (should be capped at 50)
                results = await search_icd10("test", limit=100)
                # Should not raise error, should clamp to 50

    @pytest.mark.asyncio
    async def test_get_code_details_invalid_type(self):
        """Test get_code_details with invalid code type."""
        with pytest.raises(ValueError, match="code_type must be"):
            await get_code_details("invalid", "E11.9")


class TestSemanticSearchAccuracy:
    """Integration-style tests for semantic search accuracy."""

    @patch("src.python.mcp_servers.medical_knowledge.embeddings.SentenceTransformer")
    @patch("src.python.mcp_servers.medical_knowledge.search.QdrantClient")
    def test_diabetes_query_matches_diabetes_code(
        self, mock_qdrant, mock_transformer, sample_icd10_code
    ):
        """Test that 'high blood sugar' query returns diabetes code."""
        # Setup mocks
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.random.rand(768)
        mock_transformer.return_value = mock_model

        mock_client = Mock()
        mock_result = Mock()
        mock_result.payload = sample_icd10_code
        mock_result.score = 0.92
        mock_client.search.return_value = [mock_result]
        mock_client.get_collection.return_value = Mock()
        mock_qdrant.return_value = mock_client

        # Test search
        embedder = MedicalCodeEmbedder()
        search_engine = MedicalCodeSearch()

        results = search_engine.search_by_text(
            "icd10", "high blood sugar", embedder, limit=5
        )

        assert len(results) > 0
        assert results[0]["code"] == "E11.9"
        assert results[0]["similarity_score"] > 0.7


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    async def test_search_with_network_error(self, mock_get_search_engine):
        """Test search handles network errors gracefully."""
        mock_search = Mock()
        mock_search.search_by_text.side_effect = Exception("Network error")
        mock_get_search_engine.return_value = mock_search

        with patch("src.python.mcp_servers.medical_knowledge.server.get_embedder"):
            with pytest.raises(Exception, match="Network error"):
                await search_icd10("test query")

    @pytest.mark.asyncio
    @patch("src.python.mcp_servers.medical_knowledge.server.get_search_engine")
    async def test_get_code_not_found(self, mock_get_search_engine):
        """Test get_code_details when code doesn't exist."""
        mock_search = Mock()
        mock_search.get_code_by_id.return_value = None
        mock_get_search_engine.return_value = mock_search

        result = await get_code_details("icd10", "INVALID")

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
