with open("backend/src/providers/llm/groq.py", "rb") as f:
    data = f.read()
lines = data.split(b"\n")
print(repr(lines[60]))  # line 61 (0-indexed: 60)
print(repr(lines[59]))
