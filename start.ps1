# Start the Enterprise AI Knowledge Platform
# Make sure to run `uv sync` first to install dependencies!

# Start Postgres Database first (if not running)
echo "Starting FastAPI Server..."
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend/src
