"""
Medical code embeddings using BioBERT.

Generates semantic embeddings for ICD-10 and CPT code descriptions using the
BioBERT (Bidirectional Encoder Representations from Transformers for Biomedical Text Mining) model.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class MedicalCodeEmbedder:
    """
    Generate embeddings for medical codes using BioBERT.

    The BioBERT model is pre-trained on biomedical literature (PubMed abstracts and PMC articles)
    and produces high-quality embeddings for medical terminology.
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize the embedder with a sentence transformer model.

        Args:
            model_name: Name of the sentence transformer model. Defaults to BioBERT from settings.
        """
        self.model_name = model_name or settings.embeddings_model
        logger.info("Loading embedding model", model=self.model_name)

        try:
            # Set cache directory for models (absolute path from settings)
            cache_dir = Path(settings.embeddings_cache_dir).resolve()
            cache_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Downloading/loading model (first run may take several minutes)",
                model=self.model_name,
                cache_dir=str(cache_dir),
            )

            self.model = SentenceTransformer(self.model_name, cache_folder=str(cache_dir))
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                "Embedding model loaded successfully",
                model=self.model_name,
                embedding_dim=self.embedding_dim,
            )
        except ConnectionError as e:
            logger.error(
                "Network error downloading model",
                model=self.model_name,
                error=str(e),
                help="Check internet connection or download model manually",
            )
            raise
        except Exception as e:
            logger.error("Failed to load embedding model", model=self.model_name, error=str(e))
            raise

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text string.

        Args:
            text: Input text to embed

        Returns:
            Numpy array of embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        try:
            embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error("Failed to generate embedding", text=text[:100], error=str(e))
            raise

    def generate_embeddings_batch(
        self, texts: list[str], batch_size: int | None = None
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batch.

        For very large batches (>10,000 texts), processing is automatically chunked
        to prevent memory issues.

        Args:
            texts: List of input texts to embed
            batch_size: Batch size for encoding. Defaults to settings value.

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return np.array([], dtype=np.float32)

        batch_size = batch_size or settings.embeddings_batch_size

        # Limit total batch size to prevent OOM errors
        MAX_TOTAL_BATCH = 10000
        if len(texts) > MAX_TOTAL_BATCH:
            logger.warning(
                "Large batch detected, processing in chunks to prevent memory issues",
                num_texts=len(texts),
                chunk_size=MAX_TOTAL_BATCH,
            )

            # Process in chunks
            all_embeddings = []
            for i in range(0, len(texts), MAX_TOTAL_BATCH):
                chunk = texts[i : i + MAX_TOTAL_BATCH]
                logger.info(
                    "Processing chunk",
                    chunk_num=i // MAX_TOTAL_BATCH + 1,
                    chunk_size=len(chunk),
                )
                chunk_embeddings = self.model.encode(
                    chunk,
                    convert_to_numpy=True,
                    batch_size=batch_size,
                    show_progress_bar=True,
                )
                all_embeddings.append(chunk_embeddings)

            embeddings = np.vstack(all_embeddings)
            return embeddings.astype(np.float32)

        # Normal batch processing
        logger.info("Generating batch embeddings", num_texts=len(texts), batch_size=batch_size)

        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,  # Show progress for large batches
            )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error("Failed to generate batch embeddings", num_texts=len(texts), error=str(e))
            raise

    def embed_medical_code(self, code_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate embedding for a medical code and enrich the code data.

        Creates a composite text from code, description, and keywords for optimal semantic search.

        Args:
            code_data: Dictionary containing code information (code, description, keywords, etc.)

        Returns:
            Enhanced code data with embedding and composite text
        """
        # Create composite text for better semantic matching
        description = code_data.get("description", "")
        keywords = code_data.get("keywords", [])

        # Composite text: description is primary, keywords provide additional context
        composite_text = description
        if keywords:
            keyword_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
            composite_text = f"{description}. Keywords: {keyword_str}"

        # Generate embedding
        embedding = self.generate_embedding(composite_text)

        # Enrich code data
        enriched_data = code_data.copy()
        enriched_data["embedding"] = embedding.tolist()
        enriched_data["composite_text"] = composite_text
        enriched_data["embedding_model"] = self.model_name

        return enriched_data

    def embed_medical_codes_batch(
        self, codes_data: list[dict[str, Any]], batch_size: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate embeddings for multiple medical codes in batch.

        Args:
            codes_data: List of code dictionaries
            batch_size: Batch size for encoding

        Returns:
            List of enriched code dictionaries with embeddings
        """
        if not codes_data:
            return []

        logger.info("Embedding medical codes in batch", num_codes=len(codes_data))

        # Create composite texts
        composite_texts = []
        for code_data in codes_data:
            description = code_data.get("description", "")
            keywords = code_data.get("keywords", [])

            composite_text = description
            if keywords:
                keyword_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
                composite_text = f"{description}. Keywords: {keyword_str}"

            composite_texts.append(composite_text)

        # Generate embeddings in batch
        embeddings = self.generate_embeddings_batch(composite_texts, batch_size)

        # Enrich code data
        enriched_codes = []
        for i, code_data in enumerate(codes_data):
            enriched_data = code_data.copy()
            enriched_data["embedding"] = embeddings[i].tolist()
            enriched_data["composite_text"] = composite_texts[i]
            enriched_data["embedding_model"] = self.model_name
            enriched_codes.append(enriched_data)

        logger.info("Successfully embedded medical codes", num_codes=len(enriched_codes))
        return enriched_codes


def load_and_embed_codes(json_path: str | Path, code_type: str = "icd10") -> list[dict[str, Any]]:
    """
    Load medical codes from JSON file and generate embeddings.

    Args:
        json_path: Path to JSON file containing medical codes
        code_type: Type of code (icd10, cpt)

    Returns:
        List of enriched code dictionaries with embeddings
    """
    json_path = Path(json_path)

    if not json_path.exists():
        logger.error("Code file not found", path=str(json_path))
        raise FileNotFoundError(f"Code file not found: {json_path}")

    logger.info("Loading medical codes", path=str(json_path), code_type=code_type)

    with open(json_path) as f:
        codes_data = json.load(f)

    logger.info("Loaded medical codes from file", num_codes=len(codes_data), code_type=code_type)

    # Initialize embedder
    embedder = MedicalCodeEmbedder()

    # Generate embeddings
    enriched_codes = embedder.embed_medical_codes_batch(codes_data)

    # Add code type to each code
    for code in enriched_codes:
        code["code_type"] = code_type

    return enriched_codes


# Convenience functions for CLI usage
if __name__ == "__main__":
    import sys

    # Example usage: python -m src.python.mcp_servers.medical_knowledge.embeddings icd10
    if len(sys.argv) > 1:
        code_type = sys.argv[1]

        if code_type == "icd10":
            json_path = settings.data_dir / "icd10" / "sample_icd10_codes.json"
        elif code_type == "cpt":
            json_path = settings.data_dir / "cpt" / "sample_cpt_codes.json"
        else:
            print(f"Unknown code type: {code_type}")
            print(
                "Usage: python -m src.python.mcp_servers.medical_knowledge.embeddings [icd10|cpt]"
            )
            sys.exit(1)

        enriched_codes = load_and_embed_codes(json_path, code_type)

        print(f"Successfully embedded {len(enriched_codes)} {code_type.upper()} codes")
        print(f"Embedding dimension: {len(enriched_codes[0]['embedding'])}")
        print("\nExample code:")
        print(f"  Code: {enriched_codes[0]['code']}")
        print(f"  Description: {enriched_codes[0]['description']}")
        print(f"  Embedding shape: {len(enriched_codes[0]['embedding'])}")
    else:
        print("Usage: python -m src.python.mcp_servers.medical_knowledge.embeddings [icd10|cpt]")
