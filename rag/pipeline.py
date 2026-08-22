import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from .embedder import embed_query
from .retriever import retrieve as qdrant_retrieve, get_retriever
from .context_builder import build_context
from .prompt_builder import build_prompt
from .llm_client import call_groq
from .citation_formatter import format_citations
from .config import config

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_count: int
    context_chunks_used: int
    model: str


class RAGPipeline:
    def __init__(self):
        self.retriever = get_retriever()
        self.embedding_dim = config.EMBEDDING_DIM
    
    def run(self, question: str, top_k: int = None, min_score: float = None) -> RAGResult:
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        question = question.strip()
        logger.info(f"Processing question: {question[:100]}...")
        
        query_vector = embed_query(question)
        
        if len(query_vector) != self.embedding_dim:
            logger.warning(f"Query embedding dimension mismatch: {len(query_vector)} != {self.embedding_dim}")
        
        retrieved_chunks = qdrant_retrieve(query_vector, top_k=top_k, min_score=min_score)
        
        if not retrieved_chunks:
            logger.warning("No relevant chunks retrieved")
            return RAGResult(
                answer="I couldn't find that information in the KIET College knowledge base.",
                sources=[],
                retrieval_count=0,
                context_chunks_used=0,
                model=config.GROQ_MODEL
            )
        
        context, context_chunks = build_context(retrieved_chunks)
        
        prompt = build_prompt(question, context, context_chunks)
        
        llm_response = call_groq(prompt)
        
        sources = format_citations(context_chunks)
        
        result = RAGResult(
            answer=llm_response.answer,
            sources=sources,
            retrieval_count=len(retrieved_chunks),
            context_chunks_used=len(context_chunks),
            model=llm_response.model
        )
        
        logger.info(f"RAG pipeline completed: {len(sources)} sources, answer length: {len(llm_response.answer)}")
        
        return result
    
    def health_check(self) -> Dict[str, Any]:
        qdrant_ok = self.retriever.health_check()
        
        return {
            "qdrant": "ok" if qdrant_ok else "unavailable",
            "embedding_model": config.EMBEDDING_MODEL,
            "collection": config.QDRANT_COLLECTION,
            "groq_model": config.GROQ_MODEL
        }


_pipeline = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


def rag_pipeline(question: str, top_k: int = None, min_score: float = None) -> Dict[str, Any]:
    pipeline = get_pipeline()
    result = pipeline.run(question, top_k=top_k, min_score=min_score)
    return {
        "answer": result.answer,
        "sources": result.sources
    }