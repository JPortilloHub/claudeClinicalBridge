#!/usr/bin/env python3
"""
Medical Code Indexing Script.

Loads ICD-10-CM and CPT codes from JSON files, generates BioBERT embeddings,
and indexes them into Qdrant vector database for semantic search.

Usage:
    # Index both ICD-10 and CPT codes
    python scripts/index_medical_codes.py

    # Index only ICD-10
    python scripts/index_medical_codes.py --code-type icd10

    # Force recreate collections
    python scripts/index_medical_codes.py --force-recreate

    # Use custom data directory
    python scripts/index_medical_codes.py --data-dir ./custom_data
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.mcp_servers.medical_knowledge.embeddings import load_and_embed_codes
from src.python.mcp_servers.medical_knowledge.search import MedicalCodeSearch
from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


def index_codes(
    code_type: str,
    data_path: Path,
    search_engine: MedicalCodeSearch,
    force_recreate: bool = False,
) -> int:
    """
    Index medical codes into Qdrant.

    Args:
        code_type: "icd10" or "cpt"
        data_path: Path to JSON file with codes
        search_engine: MedicalCodeSearch instance
        force_recreate: Whether to recreate collection

    Returns:
        Number of codes indexed
    """
    collection_name = f"{code_type}_codes"

    logger.info(
        "Starting indexing",
        code_type=code_type,
        data_path=str(data_path),
        force_recreate=force_recreate,
    )

    # Load codes and generate embeddings
    logger.info("Loading codes and generating embeddings", code_type=code_type)
    enriched_codes = load_and_embed_codes(data_path, code_type)

    if not enriched_codes:
        logger.error("No codes loaded", code_type=code_type, path=str(data_path))
        return 0

    logger.info(
        "Codes loaded with embeddings",
        code_type=code_type,
        num_codes=len(enriched_codes),
        embedding_dim=len(enriched_codes[0]["embedding"]),
    )

    # Create collection
    embedding_dim = len(enriched_codes[0]["embedding"])
    search_engine.create_collection(
        collection_name=collection_name,
        vector_size=embedding_dim,
        force_recreate=force_recreate,
    )

    # Index codes
    logger.info("Indexing codes into Qdrant", collection=collection_name)
    num_indexed = search_engine.index_codes(
        collection_name=collection_name,
        codes_with_embeddings=enriched_codes,
    )

    logger.info(
        "Indexing complete",
        code_type=code_type,
        num_indexed=num_indexed,
    )

    # Verify indexing
    stats = search_engine.get_collection_stats(collection_name)
    logger.info("Collection statistics", code_type=code_type, stats=stats)

    return num_indexed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Index medical codes into Qdrant vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index both ICD-10 and CPT codes
  python scripts/index_medical_codes.py

  # Index only ICD-10 codes
  python scripts/index_medical_codes.py --code-type icd10

  # Force recreate collections (WARNING: deletes existing data)
  python scripts/index_medical_codes.py --force-recreate

  # Use custom data directory
  python scripts/index_medical_codes.py --data-dir ./my_data
        """,
    )

    parser.add_argument(
        "--code-type",
        choices=["icd10", "cpt", "both"],
        default="both",
        help="Type of codes to index (default: both)",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=f"Data directory (default: {settings.data_dir})",
    )

    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreate collections (WARNING: deletes existing data)",
    )

    parser.add_argument(
        "--icd10-file",
        type=Path,
        default=None,
        help="Custom ICD-10 JSON file path",
    )

    parser.add_argument(
        "--cpt-file",
        type=Path,
        default=None,
        help="Custom CPT JSON file path",
    )

    args = parser.parse_args()

    # Determine data directory
    data_dir = args.data_dir if args.data_dir else settings.data_dir

    # Determine file paths
    if args.icd10_file:
        icd10_path = args.icd10_file
    else:
        icd10_path = data_dir / "icd10" / "sample_icd10_codes.json"

    if args.cpt_file:
        cpt_path = args.cpt_file
    else:
        cpt_path = data_dir / "cpt" / "sample_cpt_codes.json"

    # Validate files exist
    if args.code_type in ("icd10", "both") and not icd10_path.exists():
        logger.error("ICD-10 file not found", path=str(icd10_path))
        print(f"ERROR: ICD-10 file not found: {icd10_path}", file=sys.stderr)
        sys.exit(1)

    if args.code_type in ("cpt", "both") and not cpt_path.exists():
        logger.error("CPT file not found", path=str(cpt_path))
        print(f"ERROR: CPT file not found: {cpt_path}", file=sys.stderr)
        sys.exit(1)

    # Warning for force recreate
    if args.force_recreate:
        logger.warning("Force recreate enabled - existing data will be deleted")
        print("\n⚠️  WARNING: Force recreate enabled!")
        print("   This will DELETE all existing indexed codes.")
        response = input("   Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Initialize search engine
    logger.info("Initializing search engine")
    search_engine = MedicalCodeSearch()

    # Test Qdrant connectivity before proceeding
    try:
        search_engine.client.get_collections()
        logger.info("Qdrant connectivity verified", url=settings.qdrant_url)
    except Exception as e:
        logger.error("Cannot connect to Qdrant", error=str(e), url=settings.qdrant_url)
        print(f"\n❌ ERROR: Cannot connect to Qdrant at {settings.qdrant_url}")
        print(f"   Error: {e}")
        print(f"   Make sure Qdrant is running: docker-compose up -d qdrant")
        sys.exit(1)

    # Track statistics
    total_indexed = 0
    results = {}

    # Index ICD-10 codes
    if args.code_type in ("icd10", "both"):
        logger.info("=" * 60)
        logger.info("Indexing ICD-10-CM Diagnosis Codes")
        logger.info("=" * 60)
        try:
            num_indexed = index_codes(
                code_type="icd10",
                data_path=icd10_path,
                search_engine=search_engine,
                force_recreate=args.force_recreate,
            )
            total_indexed += num_indexed
            results["icd10"] = {"success": True, "count": num_indexed}
            print(f"\n✅ ICD-10: {num_indexed} codes indexed successfully")
        except Exception as e:
            logger.error("ICD-10 indexing failed", error=str(e), exc_info=True)
            results["icd10"] = {"success": False, "error": str(e)}
            print(f"\n❌ ICD-10 indexing failed: {e}", file=sys.stderr)

    # Index CPT codes
    if args.code_type in ("cpt", "both"):
        logger.info("=" * 60)
        logger.info("Indexing CPT Procedure Codes")
        logger.info("=" * 60)
        try:
            num_indexed = index_codes(
                code_type="cpt",
                data_path=cpt_path,
                search_engine=search_engine,
                force_recreate=args.force_recreate,
            )
            total_indexed += num_indexed
            results["cpt"] = {"success": True, "count": num_indexed}
            print(f"\n✅ CPT: {num_indexed} codes indexed successfully")
        except Exception as e:
            logger.error("CPT indexing failed", error=str(e), exc_info=True)
            results["cpt"] = {"success": False, "error": str(e)}
            print(f"\n❌ CPT indexing failed: {e}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 60)
    print("INDEXING SUMMARY")
    print("=" * 60)

    for code_type, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{code_type.upper():8} {status}", end="")
        if result["success"]:
            print(f" - {result['count']} codes")
        else:
            print(f" - {result['error']}")

    print(f"\nTotal codes indexed: {total_indexed}")

    # Verify with test searches
    if total_indexed > 0:
        print("\n" + "=" * 60)
        print("VERIFICATION TEST SEARCHES")
        print("=" * 60)

        test_queries = [
            ("icd10", "high blood sugar"),
            ("icd10", "chest pain"),
            ("cpt", "office visit"),
            ("cpt", "blood test"),
        ]

        # Reuse embedder if already initialized, otherwise create new one
        from src.python.mcp_servers.medical_knowledge.embeddings import MedicalCodeEmbedder

        logger.info("Initializing embedder for verification searches")
        embedder = MedicalCodeEmbedder()

        for code_type, query in test_queries:
            if code_type not in results or not results[code_type]["success"]:
                continue

            try:
                print(f"\nSearching {code_type.upper()}: '{query}'")
                search_results = search_engine.search_by_text(
                    code_type=code_type,
                    query_text=query,
                    embedder=embedder,
                    limit=3,
                    score_threshold=0.5,
                )

                if search_results:
                    for i, result in enumerate(search_results, 1):
                        print(
                            f"  {i}. {result['code']}: {result['description'][:60]}... "
                            f"(score: {result['similarity_score']:.3f})"
                        )
                else:
                    print("  No results found")

            except Exception as e:
                print(f"  ⚠️  Search failed: {e}")

    logger.info("Indexing script completed", total_indexed=total_indexed)

    # Exit with error code if any indexing failed
    if any(not r["success"] for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nIndexing interrupted by user.")
        logger.info("Indexing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("Indexing script failed", error=str(e), exc_info=True)
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
