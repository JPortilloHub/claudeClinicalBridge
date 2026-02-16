"""
Payer Policy Store with SQLite backend.

Manages payer policies including prior authorization requirements,
documentation requirements, and medical necessity criteria.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from pydantic import BaseModel, Field

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class PayerPolicy(BaseModel):
    """Payer policy model."""

    payer: str = Field(..., description="Payer name (e.g., Medicare, UnitedHealthcare)")
    cpt_code: str = Field(..., description="CPT procedure code")
    procedure_name: str = Field(..., description="Procedure name/description")
    requires_prior_auth: bool = Field(..., description="Whether prior auth is required")
    documentation_requirements: list[str] = Field(
        ..., description="Required documentation elements"
    )
    medical_necessity_criteria: list[str] = Field(
        ..., description="Medical necessity criteria"
    )
    prior_auth_criteria: list[str] | None = Field(
        None, description="Specific prior auth criteria (if applicable)"
    )
    reimbursement_rate: float | None = Field(
        None, description="Reimbursement rate in USD"
    )
    effective_date: str = Field(..., description="Policy effective date (YYYY-MM-DD)")
    notes: str | None = Field(None, description="Additional notes")


class PolicyStore:
    """
    Payer policy store with SQLite backend.

    Manages loading, querying, and updating payer policies for
    prior authorization and documentation requirements.
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialize policy store.

        Args:
            db_path: Path to SQLite database file (defaults to settings)
        """
        self.db_path = db_path or settings.database_url.replace("sqlite:///", "")
        self._ensure_db_exists()

        logger.info("policy_store_initialized", db_path=self.db_path)

    @contextmanager
    def _get_connection(self, row_factory: bool = False) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for SQLite connections.

        Args:
            row_factory: If True, set row_factory to sqlite3.Row

        Yields:
            SQLite connection
        """
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _row_to_policy(row: sqlite3.Row) -> PayerPolicy:
        """
        Convert a SQLite Row to a PayerPolicy model.

        Args:
            row: SQLite Row object

        Returns:
            Validated PayerPolicy instance
        """
        policy_dict = dict(row)
        policy_dict["documentation_requirements"] = json.loads(
            policy_dict["documentation_requirements"]
        )
        policy_dict["medical_necessity_criteria"] = json.loads(
            policy_dict["medical_necessity_criteria"]
        )
        if policy_dict["prior_auth_criteria"]:
            policy_dict["prior_auth_criteria"] = json.loads(
                policy_dict["prior_auth_criteria"]
            )

        # Remove DB-specific fields
        for field in ["id", "created_at", "updated_at"]:
            policy_dict.pop(field, None)

        return PayerPolicy(**policy_dict)

    def _ensure_db_exists(self) -> None:
        """Ensure database and tables exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create policies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payer TEXT NOT NULL,
                    cpt_code TEXT NOT NULL,
                    procedure_name TEXT NOT NULL,
                    requires_prior_auth BOOLEAN NOT NULL,
                    documentation_requirements TEXT NOT NULL,
                    medical_necessity_criteria TEXT NOT NULL,
                    prior_auth_criteria TEXT,
                    reimbursement_rate REAL,
                    effective_date TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(payer, cpt_code)
                )
            """)

            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_payer_cpt
                ON policies(payer, cpt_code)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cpt
                ON policies(cpt_code)
            """)

            conn.commit()

        logger.info("policy_store_database_initialized")

    def load_policies_from_json(self, json_path: str) -> int:
        """
        Load policies from JSON file into database.

        Args:
            json_path: Path to JSON file with policies

        Returns:
            Number of policies loaded

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON is invalid
        """
        json_file = Path(json_path)
        if not json_file.exists():
            raise FileNotFoundError(f"Policy JSON not found: {json_path}")

        with open(json_file, "r") as f:
            data = json.load(f)

        policies = data.get("policies", [])
        if not policies:
            raise ValueError("No policies found in JSON file")

        loaded_count = 0
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            for policy_data in policies:
                try:
                    # Validate with Pydantic
                    policy = PayerPolicy(**policy_data)

                    # Insert or replace policy
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO policies (
                            payer, cpt_code, procedure_name, requires_prior_auth,
                            documentation_requirements, medical_necessity_criteria,
                            prior_auth_criteria, reimbursement_rate, effective_date,
                            notes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            policy.payer,
                            policy.cpt_code,
                            policy.procedure_name,
                            policy.requires_prior_auth,
                            json.dumps(policy.documentation_requirements),
                            json.dumps(policy.medical_necessity_criteria),
                            json.dumps(policy.prior_auth_criteria)
                            if policy.prior_auth_criteria
                            else None,
                            policy.reimbursement_rate,
                            policy.effective_date,
                            policy.notes,
                            now,
                            now,
                        ),
                    )
                    loaded_count += 1

                except Exception as e:
                    logger.error(
                        "policy_load_error",
                        payer=policy_data.get("payer"),
                        cpt_code=policy_data.get("cpt_code"),
                        error=str(e),
                    )

            conn.commit()

        logger.info("policies_loaded", count=loaded_count, source=json_path)
        return loaded_count

    def get_policy(self, payer: str, cpt_code: str) -> PayerPolicy | None:
        """
        Get policy for specific payer and CPT code.

        Args:
            payer: Payer name
            cpt_code: CPT code

        Returns:
            Policy if found, None otherwise
        """
        with self._get_connection(row_factory=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM policies
                WHERE payer = ? AND cpt_code = ?
                """,
                (payer, cpt_code),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_policy(row)

    def search_policies(
        self,
        payer: str | None = None,
        cpt_code: str | None = None,
        requires_prior_auth: bool | None = None,
        limit: int = 50,
    ) -> list[PayerPolicy]:
        """
        Search for policies with filters.

        Args:
            payer: Filter by payer name (optional)
            cpt_code: Filter by CPT code (optional)
            requires_prior_auth: Filter by prior auth requirement (optional)
            limit: Maximum number of results

        Returns:
            List of matching policies
        """
        # Build query dynamically
        query = "SELECT * FROM policies WHERE 1=1"
        params: list[Any] = []

        if payer:
            query += " AND payer = ?"
            params.append(payer)

        if cpt_code:
            query += " AND cpt_code = ?"
            params.append(cpt_code)

        if requires_prior_auth is not None:
            query += " AND requires_prior_auth = ?"
            params.append(requires_prior_auth)

        query += " LIMIT ?"
        params.append(limit)

        with self._get_connection(row_factory=True) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_policy(row) for row in rows]

    def get_all_payers(self) -> list[str]:
        """
        Get list of all payers in database.

        Returns:
            List of unique payer names
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT payer FROM policies ORDER BY payer")
            return [row[0] for row in cursor.fetchall()]

    def count_policies(self) -> int:
        """
        Count total number of policies in database.

        Returns:
            Total policy count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM policies")
            return cursor.fetchone()[0]
