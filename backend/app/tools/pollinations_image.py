"""
Pollinations.ai image generator.

Generates high-resolution, context-tailored AI visuals using Pollinations.ai (FLUX model).
No API keys required; 100% free and non-blocking.
"""

from __future__ import annotations

import random
from urllib.parse import quote

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_pollinations_image(
    prompt: str,
    width: int = 1024,
    height: int = 768,
    model: str = "flux",
    seed: int | None = None,
) -> dict:
    """
    Generate a direct Pollinations.ai image record from a descriptive prompt.

    Returns:
        dict containing 'url', 'prompt', 'description', 'source' ('pollinations'),
        and dimension metadata.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        clean_prompt = "Futuristic autonomous research technology visualization"

    encoded_prompt = quote(clean_prompt)
    image_seed = seed if seed is not None else random.randint(1000, 999999)
    base_url = settings.POLLINATIONS_IMAGE_URL.rstrip("/")

    image_url = (
        f"{base_url}/{encoded_prompt}"
        f"?width={width}&height={height}&model={model}&nologo=true&seed={image_seed}"
    )

    logger.info("Generated Pollinations.ai visual URL for prompt: %s (seed=%d)", clean_prompt[:60], image_seed)

    return {
        "url": image_url,
        "prompt": clean_prompt,
        "description": clean_prompt,
        "title": f"AI Visual: {clean_prompt[:40]}...",
        "source": "pollinations",
        "width": width,
        "height": height,
        "seed": image_seed,
    }


def generate_research_images(
    goal: str,
    tasks_or_claims: list[str] | None = None,
    max_images: int = 3,
) -> list[dict]:
    """
    Produce a curated set of 1-3 contextual AI illustration images for a research topic.
    """
    prompts = [
        f"High quality infographic visualization of {goal}, scientific diagram, 8k resolution, cinematic lighting",
        f"Conceptual technical architecture and future landscape of {goal}, modern UI graphic, clean render",
        f"Key breakthrough analysis of {goal}, professional data visualization, editorial style",
    ]

    if tasks_or_claims:
        for claim in tasks_or_claims[:2]:
            if claim and len(claim.strip()) > 10:
                prompts.append(f"Visual depiction of {claim.strip()}, detailed educational render, sharp focus")

    selected_prompts = prompts[:max_images]
    images = []
    for i, p in enumerate(selected_prompts, start=1):
        try:
            images.append(generate_pollinations_image(p, seed=random.randint(10000, 999999)))
        except Exception as exc:
            logger.warning("Could not generate pollinations image %d: %s", i, exc)

    return images
