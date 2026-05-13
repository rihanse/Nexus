import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "enterprise.db")
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL", "")
TEST_EMAIL_ADDRESS = os.getenv("TEST_EMAIL_ADDRESS", "")