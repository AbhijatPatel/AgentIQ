"""
Tests for Pollinations.ai image generator.
"""

from app.tools.pollinations_image import (
    generate_pollinations_image,
    generate_research_images,
)


def test_generate_pollinations_image_returns_valid_structure():
    result = generate_pollinations_image("Autonomous Multi-Agent Framework", seed=42)

    assert "url" in result
    assert "image.pollinations.ai" in result["url"]
    assert "model=flux" in result["url"]
    assert "seed=42" in result["url"]
    assert result["source"] == "pollinations"
    assert result["prompt"] == "Autonomous Multi-Agent Framework"


def test_generate_pollinations_image_handles_empty_prompt():
    result = generate_pollinations_image("")
    assert "url" in result
    assert "image.pollinations.ai" in result["url"]
    assert result["source"] == "pollinations"


def test_generate_research_images_returns_curated_list():
    images = generate_research_images(
        goal="Quantum Machine Learning Algorithms",
        tasks_or_claims=["Qubit error correction", "Variational quantum eigensolver"],
        max_images=3,
    )

    assert len(images) == 3
    for img in images:
        assert "url" in img
        assert img["source"] == "pollinations"