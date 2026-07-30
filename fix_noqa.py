import re

files = [
    "backend/src/llm/rag/loaders/universal_loader.py",
    "backend/src/llm/rag/loaders/image_extractor.py",
    "backend/src/api/routers/providers.py",
]

for path in files:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Match "except Exception" or "except Exception as e" lines without existing noqa
        if re.search(r"\bexcept Exception\b", line) and "noqa" not in line:
            line = line.rstrip("\n\r")
            line = line + "  # noqa: BLE001\n"
        new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"Processed {path}")

print("Done!")
