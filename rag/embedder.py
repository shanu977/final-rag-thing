from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import logging

from .config import config

logger = logging.getLogger(__name__)


class QueryEmbedder:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Empty text cannot be embedded")
        
        embedding = self._model.encode(text.strip(), convert_to_numpy=True, normalize_embeddings=True)
        
        if embedding.shape[0] != config.EMBEDDING_DIM:
            logger.warning(f"Embedding dimension mismatch: expected {config.EMBEDDING_DIM}, got {embedding.shape[0]}")
        
        return embedding.astype(np.float32).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype(np.float32).tolist()


_embedder = None


def get_embedder() -> QueryEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = QueryEmbedder()
    return _embedder


def embed_query(text: str) -> List[float]:
    return get_embedder().embed(text)