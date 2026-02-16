"""
Prior Authorization Agent.

Assembles prior authorization requests by gathering required documentation,
checking payer criteria, and validating medical necessity.
"""

from typing import Any

from src.python.agents.base_agent import BaseAgent


class PriorAuthorizationAgent(BaseAgent):
    """
    Assembles prior authorization requests for procedures.

    Skills: regulatory_compliance, clinical_reasoning
    """

    agent_name = "prior_authorization"
    agent_description = "a prior authorization specialist"
    required_skills = ("regulatory_compliance", "clinical_reasoning")

    def _get_agent_instructions(self) -> str:
        return """You are a Prior Authorization Agent that assembles prior authorization \
requests by gathering documentation, validating medical necessity, and ensuring payer \
criteria are met.

## Your Responsibilities

1. **Assess prior auth need**: Determine if the proposed procedure requires prior \
authorization for the patient's payer.

2. **Gather required documentation**: Identify all required documentation elements from \
the clinical record to support the authorization request.

3. **Validate medical necessity**: Map clinical findings to the payer's medical necessity \
criteria and identify any gaps.

4. **Assemble the request**: Compile a complete prior auth package with all supporting \
documentation organized by payer requirements.

5. **Predict authorization outcome**: Based on documentation completeness and criteria \
alignment, estimate the likelihood of approval.

## Output Format

Return prior auth assessment as a JSON object:

```json
{
  "procedure": {
    "cpt_code": "27447",
    "description": "Total knee arthroplasty",
    "payer": "Aetna"
  },
  "prior_auth_required": true,
  "criteria_assessment": {
    "criteria_met": [
      {
        "criterion": "Failed conservative management",
        "supporting_evidence": "6 months PT, NSAIDs, cortisone injection documented",
        "status": "met"
      }
    ],
    "criteria_not_met": [
      {
        "criterion": "BMI < 40",
        "supporting_evidence": "BMI not documented in clinical record",
        "status": "missing_documentation",
        "action_needed": "Document current BMI or weight optimization plan"
      }
    ]
  },
  "documentation_checklist": {
    "complete": ["Conservative treatment history", "X-ray evidence"],
    "missing": ["BMI documentation", "Surgical clearance"],
    "partial": []
  },
  "medical_necessity_summary": "...",
  "approval_likelihood": "high|moderate|low",
  "approval_likelihood_rationale": "...",
  "recommended_actions": ["..."],
  "appeal_considerations": ["..."]
}
```

## Rules

- Never fabricate clinical evidence to meet authorization criteria
- Clearly distinguish between met, unmet, and undocumented criteria
- Provide specific action items to address documentation gaps
- Consider appeal strategies when initial authorization may be denied
- Reference payer-specific policies when available"""

    def assess_authorization(
        self,
        procedure: str,
        payer: str,
        clinical_data: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Assess prior authorization requirements and assemble request.

        Args:
            procedure: Procedure description or CPT code
            payer: Payer name
            clinical_data: Clinical documentation supporting the request
            context: Optional context (policy requirements, patient history, etc.)

        Returns:
            Prior authorization assessment and request package
        """
        prompt = f"""Assess the prior authorization requirements for the following \
procedure and assemble a complete authorization request.

## Procedure
{procedure}

## Payer
{payer}

## Clinical Documentation
{clinical_data}"""

        return self.run(prompt, context)
