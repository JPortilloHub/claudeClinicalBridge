"""
Unit tests for Skill Loader.
"""

import pytest

from src.python.skills.skill_loader import (
    AVAILABLE_SKILLS,
    get_skill_summary,
    list_available_skills,
    load_skill,
    load_skills,
)


# ============================================================================
# load_skill Tests
# ============================================================================


@pytest.mark.parametrize("skill_name", list(AVAILABLE_SKILLS.keys()))
def test_load_skill_all_available(skill_name):
    """Test that all registered skills load successfully."""
    content = load_skill(skill_name)

    assert isinstance(content, str)
    assert len(content) > 100  # Ensure non-trivial content
    assert content.startswith("# ")  # All skills start with a heading


def test_load_skill_medical_terminology():
    """Test medical terminology skill content."""
    content = load_skill("medical_terminology")

    assert "Medical Terminology" in content
    assert "SNOMED CT" in content or "ICD-10" in content
    assert "Standardized" in content


def test_load_skill_coding_accuracy():
    """Test coding accuracy skill content."""
    content = load_skill("coding_accuracy")

    assert "Coding Accuracy" in content
    assert "ICD-10-CM" in content
    assert "CPT" in content
    assert "specificity" in content.lower()


def test_load_skill_clinical_reasoning():
    """Test clinical reasoning skill content."""
    content = load_skill("clinical_reasoning")

    assert "Clinical Reasoning" in content
    assert "differential" in content.lower()
    assert "VINDICATE" in content
    assert "SOAP" in content


def test_load_skill_regulatory_compliance():
    """Test regulatory compliance skill content."""
    content = load_skill("regulatory_compliance")

    assert "Regulatory Compliance" in content
    assert "HIPAA" in content
    assert "PHI" in content
    assert "18 Identifiers" in content or "18 identifiers" in content


def test_load_skill_unknown():
    """Test loading an unknown skill raises ValueError."""
    with pytest.raises(ValueError, match="Unknown skill"):
        load_skill("nonexistent_skill")


# ============================================================================
# load_skills Tests
# ============================================================================


def test_load_skills_single():
    """Test loading a single skill via load_skills."""
    content = load_skills("medical_terminology")

    assert "Medical Terminology" in content
    # Single skill should not have the inter-skill separator
    assert "\n\n---\n\n" not in content


def test_load_skills_multiple():
    """Test loading multiple skills combines them."""
    content = load_skills("medical_terminology", "coding_accuracy")

    assert "Medical Terminology" in content
    assert "Coding Accuracy" in content
    assert "---" in content  # Separator between skills


def test_load_skills_all():
    """Test loading all available skills."""
    content = load_skills(*AVAILABLE_SKILLS.keys())

    assert "Medical Terminology" in content
    assert "Coding Accuracy" in content
    assert "Clinical Reasoning" in content
    assert "Regulatory Compliance" in content


def test_load_skills_unknown():
    """Test loading with an unknown skill raises ValueError."""
    with pytest.raises(ValueError, match="Unknown skill"):
        load_skills("medical_terminology", "fake_skill")


# ============================================================================
# list_available_skills Tests
# ============================================================================


def test_list_available_skills():
    """Test listing all available skills."""
    skills = list_available_skills()

    assert isinstance(skills, dict)
    assert len(skills) == 4
    assert "medical_terminology" in skills
    assert "coding_accuracy" in skills
    assert "clinical_reasoning" in skills
    assert "regulatory_compliance" in skills

    # All paths should end with .md
    for path in skills.values():
        assert path.endswith(".md")


# ============================================================================
# get_skill_summary Tests
# ============================================================================


def test_get_skill_summary():
    """Test getting a skill summary."""
    summary = get_skill_summary("medical_terminology")

    assert summary["name"] == "medical_terminology"
    assert "Medical Terminology" in summary["title"]
    assert len(summary["role"]) > 0


@pytest.mark.parametrize("skill_name", list(AVAILABLE_SKILLS.keys()))
def test_get_skill_summary_all(skill_name):
    """Test that summaries work for all skills."""
    summary = get_skill_summary(skill_name)

    assert summary["name"] == skill_name
    assert len(summary["title"]) > 0


# ============================================================================
# AVAILABLE_SKILLS Tests
# ============================================================================


def test_available_skills_count():
    """Test that exactly 4 skills are registered."""
    assert len(AVAILABLE_SKILLS) == 4


def test_available_skills_files_exist():
    """Test that all registered skill files actually exist."""
    from pathlib import Path

    from src.python.skills.skill_loader import SKILLS_DIR

    for skill_name, filename in AVAILABLE_SKILLS.items():
        skill_path = SKILLS_DIR / filename
        assert skill_path.exists(), f"Missing skill file: {skill_path} for '{skill_name}'"
