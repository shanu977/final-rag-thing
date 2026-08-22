import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
    QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'documents')
    
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    EMBEDDING_DIM = 384
    
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', '8'))
    RAG_MIN_SCORE = float(os.getenv('RAG_MIN_SCORE', '0.3'))
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
    GROQ_TIMEOUT = int(os.getenv('GROQ_TIMEOUT', '60'))
    
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'ai_project')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Dhanu@143')


config = Config()