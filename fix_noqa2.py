"""Bulk-apply noqa comments to remaining ruff errors that need manual suppression."""
import re

# Map of file -> list of (line_number_1indexed, noqa_codes)
fixes = {
    "backend/src/providers/llm/groq.py": [(61, "BLE001")],
    "backend/src/providers/llm/ollama.py": [(74, "BLE001")],
    "backend/src/providers/llm/openai.py": [(65, "BLE001")],
    "backend/src/providers/llm/openrouter.py": [(23, "BLE001")],
    "backend/src/llm/capability_discovery.py": [(104, "BLE001")],
    "backend/src/llm/rag/retrieval/search.py": [(169, "BLE001")],
    "backend/src/services/chat_service.py": [(201, "BLE001"), (254, "BLE001"), (284, "BLE001"), (456, "BLE001"), (478, "BLE001 S110")],
    "backend/src/services/email_service.py": [(48, "BLE001")],
    "backend/src/services/ingestion_service.py": [(140, "BLE001")],
}

for filepath, line_fixes in fixes.items():
    with open(filepath, "rb") as f:
        raw = f.read()

    # Detect line ending
    if b"\r\n" in raw:
        sep = b"\r\n"
    else:
        sep = b"\n"

    lines = raw.split(sep)

    for lineno, codes in line_fixes:
        idx = lineno - 1  # 0-indexed
        line = lines[idx]
        # Decode, strip trailing whitespace
        decoded = line.rstrip()
        if b"noqa" in decoded:
            print(f"  SKIP {filepath}:{lineno} (already has noqa)")
            continue
        decoded = decoded + f"  # noqa: {codes}".encode()
        lines[idx] = decoded
        print(f"  FIXED {filepath}:{lineno} -> added # noqa: {codes}")

    with open(filepath, "wb") as f:
        f.write(sep.join(lines))

print("\nDone!")
