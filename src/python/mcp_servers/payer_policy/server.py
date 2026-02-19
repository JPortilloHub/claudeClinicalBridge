"""
Payer Policy MCP Server.

Provides tools for checking prior authorization requirements,
documentation requirements, and medical necessity criteria for
various payers and procedure codes.
"""

import threading
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.python.mcp_servers.payer_policy.policy_store import PolicyStore
from src.python.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize MCP server
mcp = FastMCP("payer-policy")

# Lazy initialization for PolicyStore
_policy_store: PolicyStore | None = None
_store_lock = threading.Lock()


def get_policy_store() -> PolicyStore:
    """
    Get or initialize PolicyStore instance (thread-safe lazy initialization).

    Returns:
        PolicyStore instance
    """
    global _policy_store

    if _policy_store is None:
        with _store_lock:
            if _policy_store is None:
                _policy_store = PolicyStore()
                logger.info("payer_policy_store_initialized")

    return _policy_store


@mcp.tool()
async def check_auth_requirements(payer: str, cpt_code: str) -> dict[str, Any]:
    """
    Check if a procedure requires prior authorization for a specific payer.

    Args:
        payer: Payer name (e.g., "Medicare", "UnitedHealthcare", "Aetna")
        cpt_code: CPT procedure code (e.g., "70553", "27447")

    Returns:
        Dictionary containing:
        - requires_prior_auth (bool): Whether prior auth is required
        - prior_auth_criteria (list[str] | None): Specific criteria if applicable
        - payer (str): Payer name
        - cpt_code (str): CPT code
        - procedure_name (str | None): Procedure description if found

    Examples:
        >>> await check_auth_requirements("UnitedHealthcare", "70553")
        {
            "requires_prior_auth": True,
            "prior_auth_criteria": [
                "Documented neurological symptoms",
                "Failed conservative management",
                "High clinical suspicion for intracranial pathology"
            ],
            "payer": "UnitedHealthcare",
            "cpt_code": "70553",
            "procedure_name": "MRI brain with and without contrast"
        }
    """
    logger.info(
        "check_auth_requirements_started",
        payer=payer,
        cpt_code=cpt_code,
    )

    try:
        store = get_policy_store()
        policy = store.get_policy(payer=payer, cpt_code=cpt_code)

        if not policy:
            logger.warning(
                "policy_not_found",
                payer=payer,
                cpt_code=cpt_code,
            )
            return {
                "requires_prior_auth": None,
                "prior_auth_criteria": None,
                "payer": payer,
                "cpt_code": cpt_code,
                "procedure_name": None,
                "error": f"No policy found for {payer} / {cpt_code}",
            }

        result = {
            "requires_prior_auth": policy.requires_prior_auth,
            "prior_auth_criteria": policy.prior_auth_criteria,
            "payer": policy.payer,
            "cpt_code": policy.cpt_code,
            "procedure_name": policy.procedure_name,
        }

        logger.info(
            "check_auth_requirements_success",
            payer=payer,
            cpt_code=cpt_code,
            requires_prior_auth=policy.requires_prior_auth,
        )

        return result

    except Exception as e:
        logger.error(
            "check_auth_requirements_error",
            payer=payer,
            cpt_code=cpt_code,
            error=str(e),
        )
        return {
            "requires_prior_auth": None,
            "prior_auth_criteria": None,
            "payer": payer,
            "cpt_code": cpt_code,
            "procedure_name": None,
            "error": f"Error checking authorization requirements: {str(e)}",
        }


@mcp.tool()
async def get_documentation_requirements(payer: str, cpt_code: str) -> dict[str, Any]:
    """
    Get required documentation elements for a procedure and payer.

    Args:
        payer: Payer name (e.g., "Medicare", "Aetna", "BCBS")
        cpt_code: CPT procedure code (e.g., "99214", "27447")

    Returns:
        Dictionary containing:
        - documentation_requirements (list[str]): Required documentation elements
        - medical_necessity_criteria (list[str]): Medical necessity criteria
        - payer (str): Payer name
        - cpt_code (str): CPT code
        - procedure_name (str | None): Procedure description if found

    Examples:
        >>> await get_documentation_requirements("Medicare", "99214")
        {
            "documentation_requirements": [
                "Chief complaint documented",
                "History of present illness (4+ elements)",
                "Review of systems (2-9 systems)",
                "Physical examination (2-7 body areas/organ systems)",
                "Medical decision making of moderate complexity",
                "Time documented if using time-based coding (30-39 minutes)"
            ],
            "medical_necessity_criteria": [
                "Established patient",
                "Medically necessary follow-up care",
                "Condition requires moderate complexity evaluation"
            ],
            "payer": "Medicare",
            "cpt_code": "99214",
            "procedure_name": "Office/outpatient visit, established patient, moderate complexity"
        }
    """
    logger.info(
        "get_documentation_requirements_started",
        payer=payer,
        cpt_code=cpt_code,
    )

    try:
        store = get_policy_store()
        policy = store.get_policy(payer=payer, cpt_code=cpt_code)

        if not policy:
            logger.warning(
                "policy_not_found",
                payer=payer,
                cpt_code=cpt_code,
            )
            return {
                "documentation_requirements": [],
                "medical_necessity_criteria": [],
                "payer": payer,
                "cpt_code": cpt_code,
                "procedure_name": None,
                "error": f"No policy found for {payer} / {cpt_code}",
            }

        result = {
            "documentation_requirements": policy.documentation_requirements,
            "medical_necessity_criteria": policy.medical_necessity_criteria,
            "payer": policy.payer,
            "cpt_code": policy.cpt_code,
            "procedure_name": policy.procedure_name,
        }

        logger.info(
            "get_documentation_requirements_success",
            payer=payer,
            cpt_code=cpt_code,
            num_requirements=len(policy.documentation_requirements),
            num_criteria=len(policy.medical_necessity_criteria),
        )

        return result

    except Exception as e:
        logger.error(
            "get_documentation_requirements_error",
            payer=payer,
            cpt_code=cpt_code,
            error=str(e),
        )
        return {
            "documentation_requirements": [],
            "medical_necessity_criteria": [],
            "payer": payer,
            "cpt_code": cpt_code,
            "procedure_name": None,
            "error": f"Error retrieving documentation requirements: {str(e)}",
        }


@mcp.tool()
async def validate_medical_necessity(
    payer: str, cpt_code: str, clinical_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Validate medical necessity criteria against clinical data.

    Checks if the provided clinical data meets the payer's medical necessity
    criteria for the specified procedure code.

    Args:
        payer: Payer name (e.g., "Aetna", "Medicare")
        cpt_code: CPT procedure code (e.g., "27447", "99214")
        clinical_data: Dictionary of clinical information with keys:
            - diagnoses (list[str]): ICD-10 diagnosis codes
            - symptoms (list[str]): Clinical symptoms
            - history (list[str]): Treatment history
            - findings (list[str]): Examination findings
            - Any other relevant clinical data

    Returns:
        Dictionary containing:
        - criteria_met (list[str]): Criteria that are met
        - criteria_not_met (list[str]): Criteria not met or unable to verify
        - all_criteria (list[str]): All medical necessity criteria
        - validation_status (str): "approved" | "needs_review" | "insufficient_data"
        - payer (str): Payer name
        - cpt_code (str): CPT code
        - procedure_name (str | None): Procedure description

    Examples:
        >>> await validate_medical_necessity(
        ...     "Aetna",
        ...     "27447",
        ...     {
        ...         "diagnoses": ["M17.11"],
        ...         "symptoms": ["severe knee pain", "mobility limitation"],
        ...         "history": ["6 months PT", "NSAID trial", "cortisone injection"],
        ...         "findings": ["joint space narrowing on X-ray"]
        ...     }
        ... )
        {
            "criteria_met": [
                "Severe pain limiting daily activities",
                "Failed conservative management (PT, NSAIDs, injections)",
                "Radiographic evidence of joint space narrowing"
            ],
            "criteria_not_met": [
                "Patient medically cleared for surgery",
                "BMI < 40 (or weight optimization plan)"
            ],
            "all_criteria": [...],
            "validation_status": "needs_review",
            "payer": "Aetna",
            "cpt_code": "27447",
            "procedure_name": "Total knee arthroplasty"
        }
    """
    logger.info(
        "validate_medical_necessity_started",
        payer=payer,
        cpt_code=cpt_code,
    )

    try:
        store = get_policy_store()
        policy = store.get_policy(payer=payer, cpt_code=cpt_code)

        if not policy:
            logger.warning(
                "policy_not_found",
                payer=payer,
                cpt_code=cpt_code,
            )
            return {
                "criteria_met": [],
                "criteria_not_met": [],
                "all_criteria": [],
                "validation_status": "insufficient_data",
                "payer": payer,
                "cpt_code": cpt_code,
                "procedure_name": None,
                "error": f"No policy found for {payer} / {cpt_code}",
            }

        # Extract clinical data fields
        diagnoses = clinical_data.get("diagnoses", [])
        symptoms = clinical_data.get("symptoms", [])
        history = clinical_data.get("history", [])
        findings = clinical_data.get("findings", [])

        # Combine all clinical text for keyword matching
        clinical_sources = [
            ("diagnoses", diagnoses),
            ("symptoms", symptoms),
            ("history", history),
            ("findings", findings),
        ]

        # Simple keyword matching for validation (can be enhanced with NLP)
        criteria_met = []
        criteria_not_met = []

        for criterion in policy.medical_necessity_criteria:
            criterion_lower = criterion.lower()
            keywords = criterion_lower.split()[:3]

            # Check if criterion keywords appear in any clinical data source
            matched = False
            for _source_name, source_items in clinical_sources:
                if matched:
                    break
                for item in source_items:
                    if any(keyword in item.lower() for keyword in keywords):
                        matched = True
                        break

            if matched:
                criteria_met.append(criterion)
            else:
                criteria_not_met.append(criterion)

        # Determine validation status
        total_criteria = len(policy.medical_necessity_criteria)
        met_count = len(criteria_met)

        if met_count == total_criteria:
            validation_status = "approved"
        elif met_count >= total_criteria * 0.7:  # 70% threshold
            validation_status = "needs_review"
        else:
            validation_status = "insufficient_data"

        result = {
            "criteria_met": criteria_met,
            "criteria_not_met": criteria_not_met,
            "all_criteria": policy.medical_necessity_criteria,
            "validation_status": validation_status,
            "payer": policy.payer,
            "cpt_code": policy.cpt_code,
            "procedure_name": policy.procedure_name,
        }

        logger.info(
            "validate_medical_necessity_success",
            payer=payer,
            cpt_code=cpt_code,
            validation_status=validation_status,
            criteria_met=met_count,
            total_criteria=total_criteria,
        )

        return result

    except Exception as e:
        logger.error(
            "validate_medical_necessity_error",
            payer=payer,
            cpt_code=cpt_code,
            error=str(e),
        )
        return {
            "criteria_met": [],
            "criteria_not_met": [],
            "all_criteria": [],
            "validation_status": "insufficient_data",
            "payer": payer,
            "cpt_code": cpt_code,
            "procedure_name": None,
            "error": f"Error validating medical necessity: {str(e)}",
        }
