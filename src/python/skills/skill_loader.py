"""
Skill Loader for Agent Skills.

Loads Markdown-based skill files and provides them as system prompt
content for Claude Agent SDK sub-agents.
"""

from pathlib import Path

from src.python.utils.logging import get_logger

logger = get_logger(__name__)

# Skills directory (same directory as this module)
SKILLS_DIR = Path(__file__).parent

# Available skill definitions
AVAILABLE_SKILLS = {
    "medical_terminology": "medical_terminology_skill.md",
    "coding_accuracy": "coding_accuracy_skill.md",
    "clinical_reasoning": "clinical_reasoning_skill.md",
    "regulatory_compliance": "regulatory_compliance_skill.md",
}


def load_skill(skill_name: str) -> str:
    """
    Load a skill's Markdown content by name.

    Args:
        skill_name: Skill identifier (e.g., "medical_terminology", "coding_accuracy")

    Returns:
        Skill content as a string

    Raises:
        ValueError: If skill_name is not recognized
        FileNotFoundError: If skill file is missing
    """
    if skill_name not in AVAILABLE_SKILLS:
        raise ValueError(
            f"Unknown skill: '{skill_name}'. Available skills: {list(AVAILABLE_SKILLS.keys())}"
        )

    skill_file = SKILLS_DIR / AVAILABLE_SKILLS[skill_name]

    if not skill_file.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_file}")

    content = skill_file.read_text(encoding="utf-8")

    logger.info(
        "skill_loaded",
        skill_name=skill_name,
        file=str(skill_file.name),
        length=len(content),
    )

    return content


def load_skills(*skill_names: str) -> str:
    """
    Load and concatenate multiple skills into a single prompt string.

    Args:
        *skill_names: One or more skill identifiers

    Returns:
        Combined skill content separated by section dividers

    Raises:
        ValueError: If any skill_name is not recognized
    """
    sections = []

    for name in skill_names:
        content = load_skill(name)
        sections.append(content)

    combined = "\n\n---\n\n".join(sections)

    logger.info(
        "skills_combined",
        skills=list(skill_names),
        total_length=len(combined),
    )

    return combined


def list_available_skills() -> dict[str, str]:
    """
    List all available skills with their file paths.

    Returns:
        Dictionary mapping skill names to file paths
    """
    return {name: str(SKILLS_DIR / filename) for name, filename in AVAILABLE_SKILLS.items()}


def get_skill_summary(skill_name: str) -> dict[str, str]:
    """
    Get a brief summary of a skill (first heading and role description).

    Args:
        skill_name: Skill identifier

    Returns:
        Dictionary with 'name', 'title', and 'role' keys
    """
    content = load_skill(skill_name)
    lines = content.strip().split("\n")

    title = ""
    role = ""

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        if "You are " in line and not role:
            role = line.strip()
            break

    return {
        "name": skill_name,
        "title": title,
        "role": role,
    }
