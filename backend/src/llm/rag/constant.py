class RAGConstant:
    TEMPERATURE = 0.5
    MODEL = "gpt-4.1-mini"
    COHERE_RERANK_MODEL = "rerank-english-v3.0"
    DEFAULT_MAX_ITERATION = 5
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
    CHUNK_SIZE = 250
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    MIN_CHUNK_SIZE = 50
    FALLBACK_OPENROUTER_MODELS = [
        {
            "id": "tencent/hy3:free",
            "name": "tencent/hy3:free",
        }
    ]
    FALLBACK_OPENAI_MODELS = [
        {"id": "gpt-4.1-mini", "name": "gpt-4.1-mini"},
        {"id": "gpt-4.1-nano", "name": "gpt-4.1-nano"},
    ]
    FALLBACK_GROQ_MODELS = [
        {"id": "openai/gpt-oss-20b", "name": "openai/gpt-oss-20b"},
        {"id": "llama-3.1-8b-instant", "name": "llama-3.1-8b-instant"},
    ]
    FALLBACK_GEMINI_MODELS = [{"id": "gemini-2.5-flash", "name": "gemini-2.5-flash"}]
    OPENAI_DEFAULT_MODEL = "gpt-4.1-mini"
    GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
