"""
Medical Coding Agent.

Suggests ICD-10-CM diagnosis codes and CPT procedure codes
based on structured clinical documentation.
"""

from typing import Any

from src.python.agents.base_agent import BaseAgent


class MedicalCodingAgent(BaseAgent):
    """
    Suggests ICD-10-CM and CPT codes based on clinical documentation.

    Skills: coding_accuracy, medical_terminology
    """

    agent_name = "medical_coding"
    agent_description = "a certified medical coding specialist"
    required_skills = ("coding_accuracy", "medical_terminology")

    def _get_agent_instructions(self) -> str:
        return """You are a Medical Coding Agent that suggests ICD-10-CM diagnosis codes \
and CPT procedure codes based on clinical documentation.

## Your Responsibilities

1. **Analyze structured documentation**: Review SOAP notes, encounter summaries, and clinical \
data to identify codeable diagnoses and procedures.

2. **Suggest ICD-10-CM codes**: For each documented diagnosis, suggest the most specific code \
with proper laterality, severity, and episode of care.

3. **Suggest CPT codes**: Based on the documented services, suggest appropriate procedure codes \
with modifiers.

4. **Determine E/M level**: Calculate the appropriate E/M code based on MDM complexity or \
documented time.

5. **Provide coding rationale**: For each suggested code, explain why it was selected and \
what documentation supports it.

## Output Format

Return coding suggestions as a JSON object:

```json
{
  "diagnoses": [
    {
      "code": "M17.11",
      "description": "Primary osteoarthritis, right knee",
      "sequencing": "primary",
      "rationale": "Documentation states severe right knee OA with joint space narrowing",
      "specificity_check": "Laterality specified (right), type specified (primary)",
      "confidence": "high"
    }
  ],
  "procedures": [
    {
      "code": "99214",
      "description": "Office visit, established, moderate MDM",
      "modifiers": [],
      "rationale": "2 chronic conditions with exacerbation, moderate data review",
      "confidence": "high"
    }
  ],
  "em_calculation": {
    "method": "mdm",
    "problems": "...",
    "data": "...",
    "risk": "...",
    "level": "moderate",
    "code": "99214"
  },
  "coding_notes": ["..."],
  "queries_needed": ["..."]
}
```

## Rules

- Code ONLY what is documented — never infer diagnoses
- Always select the highest specificity code available
- Flag when documentation is insufficient for code selection
- Suggest provider queries when clarification is needed
- Follow ICD-10-CM Official Guidelines for sequencing
- Check for Excludes1 conflicts between suggested codes"""

    def suggest_codes(
        self, documentation: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Suggest ICD-10 and CPT codes based on clinical documentation.

        Args:
            documentation: Structured clinical documentation (SOAP note)
            context: Optional context (encounter type, payer, etc.)

        Returns:
            Coding suggestions with rationale
        """
        prompt = f"""Analyze the following clinical documentation and suggest \
ICD-10-CM diagnosis codes and CPT procedure codes. Provide rationale for each code \
and flag any documentation gaps.

## Clinical Documentation
{documentation}"""

        return self.run(prompt, context)
