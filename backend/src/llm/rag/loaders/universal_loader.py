from __future__ import annotations

import csv
import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

_PLAIN_TEXT_FORMATS = {".txt", ".md", ".markdown"}


def load_document(file_path: str) -> list[dict[str, Any]]:
    """
    Route the file to the appropriate native parser and return a unified list of blocks.
    Each block: {type, content, metadata}
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    logger.info("Loading document: %s (ext=%s)", path.name, ext)

    if ext == ".pdf":
        return _load_pdf(file_path)

    if ext == ".docx":
        return _load_docx(file_path)

    if ext == ".pptx":
        return _load_pptx(file_path)

    if ext in (".xlsx", ".xls"):
        return _load_xlsx(file_path)

    if ext in _PLAIN_TEXT_FORMATS:
        return _load_plain_text(file_path)

    if ext == ".csv":
        return _load_csv(file_path)

    if ext == ".json":
        return _load_json(file_path)

    if ext == ".xml":
        return _load_xml(file_path)

    # Fallback: read as plain text
    logger.warning("Unknown file type %s, treating as plain text", ext)
    return _load_plain_text(file_path)


def _describe_image_hf(image_bytes: bytes) -> str:
    """Send image to Hugging Face free Inference API to get a caption."""
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    if not hf_token:
        return ""

    API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes, timeout=15)
        response.raise_for_status()
        result = response.json()
        if (
            isinstance(result, list)
            and len(result) > 0
            and "generated_text" in result[0]
        ):
            return result[0]["generated_text"].strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Hugging Face image captioning failed: %s", e)

    return ""


def _load_pdf(file_path: str) -> list[dict[str, Any]]:
    """Parse PDF with pypdf and fallback camelot tables."""
    blocks = []

    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                paras = text.split("\n\n")
                for para in paras:
                    para = para.strip()
                    if para:
                        blocks.append(
                            {
                                "type": "text",
                                "content": para,
                                "metadata": {
                                    "page": i + 1,
                                    "heading": "",
                                    "parent_heading": "",
                                    "source": "pypdf",
                                },
                            }
                        )

            # Extract and describe images
            for img in page.images:
                try:
                    caption = _describe_image_hf(img.data)
                    if caption:
                        blocks.append(
                            {
                                "type": "image_description",
                                "content": f"[Image on page {i+1}]: {caption}",
                                "metadata": {
                                    "page": i + 1,
                                    "heading": "",
                                    "parent_heading": "",
                                    "source": "pypdf-hf-vision",
                                },
                            }
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to process image on page %d: %s", i + 1, e)
    except Exception as e:  # noqa: BLE001
        logger.error("pypdf extraction failed: %s", e)

    camelot_tables = _extract_tables_camelot(file_path)
    blocks.extend(camelot_tables)

    return blocks


def _extract_tables_camelot(file_path: str) -> list[dict[str, Any]]:
    try:
        import camelot

        tables = camelot.read_pdf(file_path, pages="all", flavor="lattice")
        result = []
        for i, table in enumerate(tables):
            md = table.df.to_markdown(index=False)
            result.append(
                {
                    "type": "table",
                    "content": md or "",
                    "metadata": {
                        "page": table.page,
                        "table_id": f"table_{i + 1}",
                        "heading": "",
                        "parent_heading": "",
                        "source": "camelot",
                    },
                }
            )
        return result
    except Exception as e:  # noqa: BLE001
        logger.warning("Camelot table extraction failed: %s", e)
        return []


def _load_docx(file_path: str) -> list[dict[str, Any]]:
    try:
        import docx
    except ImportError:
        logger.error("python-docx not installed.")
        return []

    blocks = []
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                blocks.append(
                    {
                        "type": "text",
                        "content": para.text.strip(),
                        "metadata": {
                            "page": 1,
                            "heading": "",
                            "parent_heading": "",
                            "source": "docx",
                        },
                    }
                )

        for i, table in enumerate(doc.tables):
            md_lines = []
            for j, row in enumerate(table.rows):
                row_data = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                md_lines.append("| " + " | ".join(row_data) + " |")
                if j == 0:
                    md_lines.append("| " + " | ".join(["---"] * len(row.cells)) + " |")

            if md_lines:
                blocks.append(
                    {
                        "type": "table",
                        "content": "\n".join(md_lines),
                        "metadata": {
                            "page": 1,
                            "table_id": f"table_{i+1}",
                            "heading": "",
                            "parent_heading": "",
                            "source": "docx",
                        },
                    }
                )

    except Exception as e:  # noqa: BLE001
        logger.error("DOCX load error: %s", e)
    return blocks


def _load_pptx(file_path: str) -> list[dict[str, Any]]:
    try:
        from pptx import Presentation
    except ImportError:
        logger.error("python-pptx not installed.")
        return []

    blocks = []
    try:
        prs = Presentation(file_path)
        for i, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            if slide_text:
                blocks.append(
                    {
                        "type": "text",
                        "content": "\n\n".join(slide_text),
                        "metadata": {
                            "page": i + 1,
                            "heading": "",
                            "parent_heading": "",
                            "source": "pptx",
                        },
                    }
                )
    except Exception as e:  # noqa: BLE001
        logger.error("PPTX load error: %s", e)
    return blocks


def _load_xlsx(file_path: str) -> list[dict[str, Any]]:
    try:
        import openpyxl
    except ImportError:
        logger.error("openpyxl not installed.")
        return []

    blocks = []
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for sheetname in wb.sheetnames:
            sheet = wb[sheetname]
            md_lines = []
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if not any(row):
                    continue

                row_data = [
                    str(cell).replace("\n", " ").strip() if cell is not None else ""
                    for cell in row
                ]
                md_lines.append("| " + " | ".join(row_data) + " |")
                if i == 0:
                    md_lines.append("| " + " | ".join(["---"] * len(row_data)) + " |")

            if md_lines:
                blocks.append(
                    {
                        "type": "table",
                        "content": "\n".join(md_lines),
                        "metadata": {
                            "page": 1,
                            "heading": sheetname,
                            "parent_heading": "",
                            "source": "xlsx",
                        },
                    }
                )
    except Exception as e:  # noqa: BLE001
        logger.error("XLSX load error: %s", e)
    return blocks


def _load_plain_text(file_path: str) -> list[dict[str, Any]]:
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        blocks = []
        current_heading = ""
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if para.startswith("#"):
                heading_text = para.lstrip("#").strip()
                current_heading = heading_text
                blocks.append(
                    {
                        "type": "heading",
                        "content": heading_text,
                        "metadata": {
                            "page": 1,
                            "heading": heading_text,
                            "parent_heading": "",
                            "source": "text",
                        },
                    }
                )
            else:
                blocks.append(
                    {
                        "type": "text",
                        "content": para,
                        "metadata": {
                            "page": 1,
                            "heading": current_heading,
                            "parent_heading": "",
                            "source": "text",
                        },
                    }
                )
        return blocks
    except Exception as e:  # noqa: BLE001
        logger.error("Plain text load error: %s", e)
        return []


def _load_csv(file_path: str) -> list[dict[str, Any]]:
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return []
        headers = rows[0]
        data_rows = rows[1:]
        md_lines = ["| " + " | ".join(headers) + " |"]
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in data_rows:
            md_lines.append("| " + " | ".join(str(c) for c in row) + " |")
        return [
            {
                "type": "table",
                "content": "\n".join(md_lines),
                "metadata": {
                    "page": 1,
                    "heading": "",
                    "parent_heading": "",
                    "source": "csv",
                },
            }
        ]
    except Exception as e:  # noqa: BLE001
        logger.error("CSV load error: %s", e)
        return []


def _load_json(file_path: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return [
            {
                "type": "text",
                "content": content,
                "metadata": {
                    "page": 1,
                    "heading": "",
                    "parent_heading": "",
                    "source": "json",
                },
            }
        ]
    except Exception as e:  # noqa: BLE001
        logger.error("JSON load error: %s", e)
        return []


def _load_xml(file_path: str) -> list[dict[str, Any]]:
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        texts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(f"{elem.tag}: {elem.text.strip()}")
        return [
            {
                "type": "text",
                "content": "\n".join(texts),
                "metadata": {
                    "page": 1,
                    "heading": "",
                    "parent_heading": "",
                    "source": "xml",
                },
            }
        ]
    except Exception as e:  # noqa: BLE001
        logger.error("XML load error: %s", e)
        return []
