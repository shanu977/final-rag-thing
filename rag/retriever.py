import requests
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_start: int
    page_end: int
    section: str
    subsection: str
    content: str
    content_hash: str
    score: float
    metadata: Dict[str, Any]


class QdrantRetriever:
    def __init__(self, url: str = None, collection: str = None):
        self.url = url or config.QDRANT_URL
        self.collection = collection or config.QDRANT_COLLECTION
        self.base_url = f"{self.url}/collections/{self.collection}"
        self._session = requests.Session()
    
    def retrieve(self, query_vector: List[float], top_k: int = None, min_score: float = None) -> List[RetrievedChunk]:
        top_k = top_k or config.RAG_TOP_K
        min_score = min_score if min_score is not None else config.RAG_MIN_SCORE
        
        payload = {
            "vector": query_vector,
            "limit": top_k,
            "with_payload": True,
            "with_vector": False,
            "score_threshold": min_score
        }
        
        try:
            response = self._session.post(
                f"{self.base_url}/points/search",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            chunks = []
            for point in data.get('result', []):
                payload_data = point.get('payload', {})
                chunk = RetrievedChunk(
                    chunk_id=payload_data.get('chunk_id', point.get('id', '')),
                    document_id=payload_data.get('document_id', ''),
                    filename=payload_data.get('filename', ''),
                    page_start=payload_data.get('page_start', 0),
                    page_end=payload_data.get('page_end', 0),
                    section=payload_data.get('section', ''),
                    subsection=payload_data.get('subsection', ''),
                    content=payload_data.get('text', ''),
                    content_hash=payload_data.get('content_hash', ''),
                    score=point.get('score', 0.0),
                    metadata=payload_data
                )
                chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} chunks from Qdrant (top_k={top_k}, min_score={min_score})")
            return chunks
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Qdrant retrieval failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during retrieval: {e}")
            raise
    
    def health_check(self) -> bool:
        try:
            response = self._session.get(f"{self.url}/collections/{self.collection}", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


_retriever = None


def get_retriever() -> QdrantRetriever:
    global _retriever
    if _retriever is None:
        _retriever = QdrantRetriever()
    return _retriever


def retrieve(query_vector: List[float], top_k: int = None, min_score: float = None) -> List[RetrievedChunk]:
    return get_retriever().retrieve(query_vector, top_k, min_score)