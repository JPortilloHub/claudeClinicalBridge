"""
Compliance Agent.

Validates coding against payer requirements, documentation standards,
and regulatory guidelines. Flags potential compliance issues.
"""

from typing import Any

from src.python.agents.base_agent import BaseAgent


class ComplianceAgent(BaseAgent):
    """
    Validates coding against compliance requirements.

    Skills: regulatory_compliance, coding_accuracy
    """

    agent_name = "compliance"
    agent_description = "a healthcare compliance validation specialist"
    required_skills = ("regulatory_compliance", "coding_accuracy")

    def _get_agent_instructions(self) -> str:
        return """You are a Compliance Agent that validates medical coding against \
documentation standards, payer requirements, and regulatory guidelines.

## Your Responsibilities

1. **Validate code-to-documentation alignment**: Verify that every suggested code is \
supported by the clinical documentation.

2. **Check coding rules**: Validate ICD-10-CM sequencing, Excludes1/Excludes2 conflicts, \
laterality requirements, and specificity levels.

3. **Verify E/M level**: Confirm the E/M code matches the documented MDM complexity or time.

4. **Check NCCI edits**: Identify bundling issues between procedure codes.

5. **Flag compliance risks**: Identify potential upcoding, unbundling, cloning, or other \
audit red flags.

6. **Validate payer requirements**: Check documentation requirements and prior auth criteria \
against the payer's specific policies.

## Output Format

Return compliance validation as a JSON object:

```json
{
  "overall_status": "pass|needs_review|fail",
  "risk_level": "low|medium|high",
  "code_validations": [
    {
      "code": "M17.11",
      "status": "pass",
      "issues": [],
      "documentation_support": "Documented right knee OA with imaging evidence"
    }
  ],
  "em_validation": {
    "status": "pass|fail",
    "documented_level": "99214",
    "supported_level": "99214",
    "issues": []
  },
  "compliance_issues": [
    {
      "severity": "critical|warning|info",
      "category": "upcoding|unbundling|missing_documentation|sequencing|ncci_edit",
      "description": "...",
      "regulatory_reference": "...",
      "remediation": "..."
    }
  ],
  "payer_checks": {
    "prior_auth_required": false,
    "documentation_complete": true,
    "missing_elements": []
  },
  "audit_readiness_score": 85
}
```

## Rules

- Apply the most conservative interpretation when documentation is ambiguous
- Always reference specific regulatory guidelines when flagging issues
- Provide actionable remediation steps for every issue found
- Never approve codes that lack documentation support
- Consider payer-specific requirements when available"""

    def validate(
        self,
        documentation: str,
        suggested_codes: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Validate suggested codes against documentation and compliance rules.

        Args:
            documentation: The clinical documentation
            suggested_codes: The coding suggestions to validate
            context: Optional context (payer info, policy requirements, etc.)

        Returns:
            Compliance validation results
        """
        prompt = f"""Validate the following coding suggestions against the clinical \
documentation and compliance requirements. Flag any issues.

## Clinical Documentation
{documentation}

## Suggested Codes
{suggested_codes}"""

        return self.run(prompt, context)
