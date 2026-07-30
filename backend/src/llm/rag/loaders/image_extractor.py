from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import pypdf
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def extract_and_describe_images(
    file_path: str,
    openai_api_key: str,
    model_name: str,
    document_name: str,
    workspace_id: str,
) -> list[dict[str, Any]]:
    """
    Extract images from a PDF and generate GPT-4o vision descriptions.
    Returns blocks with:
      - type: "image_description"
      - content: semantic description of the image
      - metadata: page, caption, description, has_image
    """
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        return []

    try:
        client = AsyncOpenAI(api_key=openai_api_key)
        reader = pypdf.PdfReader(str(path))
        image_blocks = []

        for page_num, page in enumerate(reader.pages, start=1):
            resources = page.get("/Resources")
            if not resources:
                continue
            xobjects = resources.get("/XObject")
            if not xobjects:
                continue

            for obj_ref in xobjects.values():
                obj = obj_ref.get_object()
                if obj.get("/Subtype") != "/Image":
                    continue

                try:
                    image_data = _extract_image_bytes(obj)
                    if not image_data:
                        continue
                except Exception:  # noqa: BLE001 S112  # skip unreadable image objects
                    continue

                description = await _describe_image(
                    client, model_name, image_data, document_name, page_num
                )
                if description:
                    image_blocks.append(
                        {
                            "type": "image_description",
                            "content": description,
                            "metadata": {
                                "page": page_num,
                                "heading": "",
                                "parent_heading": "",
                                "source": "vision_llm",
                                "has_image": False,
                                "description": description,
                            },
                        }
                    )

        logger.info(
            "Extracted %d image descriptions from %s", len(image_blocks), path.name
        )
        return image_blocks

    except Exception as e:  # noqa: BLE001
        logger.warning("Image extraction failed for %s: %s", path.name, e)
        return []


def _extract_image_bytes(obj) -> bytes | None:
    """Extract raw image bytes from a PDF XObject."""
    data = obj.get_data()
    if not data:
        return None
    if len(data) > 10 * 1024 * 1024:
        return data[: 10 * 1024 * 1024]
    return data


async def _describe_image(
    client, model_name: str, image_bytes: bytes, document_name: str, page_num: int
) -> str:
    """Send image to Vision LLM and get a semantic description."""
    try:
        b64 = base64.b64encode(image_bytes).decode()
        if image_bytes[:4] == b"\x89PNG":
            mime = "image/png"
        elif image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"
        else:
            mime = "image/jpeg"

        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"This image is from page {page_num} of the document '{document_name}'. "
                                "Provide a small and accurate semantic description of this image, chart, diagram, "
                                "or figure. Focus on key data points and text visible."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or ""
    except Exception as e:  # noqa: BLE001
        logger.warning("Vision description failed: %s", e)
        return ""
