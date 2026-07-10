from typing import List, Dict, Any


def build_sections(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups individual granular blocks (like single paragraphs or list items)
    into larger semantic sections based on heading boundaries.
    """
    sections = []

    current_section = None
    current_heading = ""
    current_parent_heading = ""

    for block in blocks:
        b_type = block.get("type", "text")
        content = block.get("content", "").strip()
        meta = block.get("metadata", {})

        if b_type == "heading":
            if current_section:
                sections.append(current_section)
                current_section = None

            current_parent_heading = current_heading
            current_heading = content

        elif b_type in ("table", "figure", "image_description"):
            if current_section:
                sections.append(current_section)
                current_section = None
            new_meta = meta.copy()
            if not new_meta.get("heading"):
                new_meta["heading"] = current_heading
            if not new_meta.get("parent_heading"):
                new_meta["parent_heading"] = current_parent_heading

            sections.append({"type": b_type, "content": content, "metadata": new_meta})

        else:
            block_heading = meta.get("heading")
            if block_heading and block_heading != current_heading:
                if current_section:
                    sections.append(current_section)
                    current_section = None
                current_heading = block_heading
                current_parent_heading = meta.get(
                    "parent_heading", current_parent_heading
                )

            if not current_section:
                current_section = {
                    "type": "text",
                    "content": content,
                    "metadata": {
                        "heading": current_heading,
                        "parent_heading": current_parent_heading,
                        "page": meta.get("page", 1),
                    },
                }
            else:
                if b_type == "list_item":
                    current_section["content"] += "\n" + content
                else:
                    current_section["content"] += "\n\n" + content

    if current_section:
        sections.append(current_section)

    return sections
