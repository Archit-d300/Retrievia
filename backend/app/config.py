import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
TEXT_DIR = DATA_DIR / "texts"
INDEX_DIR = DATA_DIR / "faiss"
REGISTRY_PATH = DATA_DIR / "registry.json"
for _p in (UPLOAD_DIR, TEXT_DIR, INDEX_DIR):
    _p.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
HF_PROVIDER = os.getenv("HF_PROVIDER", "auto")
LLM_MODEL = os.getenv("HF_LLM_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
GRADER_MODEL = os.getenv("HF_GRADER_MODEL", LLM_MODEL)
# Use a sentence-transformers checkpoint that is known to work with the project dependency set.
# Some LiquidAI local embedding models trigger a transformers/Torch incompatibility (`seq_idx`).
DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBED_MODEL = os.getenv("HF_EMBED_MODEL", DEFAULT_EMBED_MODEL)
EMBED_MODE = os.getenv("EMBED_MODE", "local")  # local | api
QUERY_PREFIX = os.getenv("EMBED_QUERY_PREFIX", "query: ")
DOC_PREFIX = os.getenv("EMBED_DOC_PREFIX", "document: ")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
RETRIEVE_K = int(os.getenv("RETRIEVE_K", "6"))
CONTEXT_K = int(os.getenv("CONTEXT_K", "4"))          # chunks actually sent to the LLM
GRADE_HIGH = float(os.getenv("GRADE_HIGH", "0.55"))
GRADE_LOW = float(os.getenv("GRADE_LOW", "0.25"))
PAPER_SIM_THRESHOLD = float(os.getenv("PAPER_SIM_THRESHOLD", "0.75"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "40"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()]
