import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from .retriever import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    source_index: int
    doc: str
    page: int
    section: str
    content: str
    score: float


class ContextBuilder:
    def __init__(self, max_chunks: int = None):
        self.max_chunks = max_chunks or 8
    
    def build(self, chunks: List[RetrievedChunk]) -> tuple[str, List[ContextChunk]]:
        if not chunks:
            return "", []
        
        selected = chunks[:self.max_chunks]
        
        context_parts = []
        context_chunks = []
        
        for i, chunk in enumerate(selected):
            source_num = i + 1
            
            page_info = f"Page: {chunk.page_start}"
            if chunk.page_end != chunk.page_start:
                page_info = f"Pages: {chunk.page_start}-{chunk.page_end}"
            
            section_info = chunk.section.replace('**', '').strip() if chunk.section else "Unknown"
            
            source_header = (
                f"[Source {source_num}]\n"
                f"Document: {chunk.filename}\n"
                f"{page_info}\n"
                f"Section: {section_info}\n"
            )
            
            context_parts.append(f"{source_header}\n{chunk.content}")
            
            context_chunks.append(ContextChunk(
                source_index=source_num,
                doc=chunk.filename,
                page=chunk.page_start,
                section=section_info,
                content=chunk.content,
                score=chunk.score
            ))
        
        full_context = "\n\n---\n\n".join(context_parts)
        logger.info(f"Built context with {len(context_chunks)} chunks")
        
        return full_context, context_chunks


def build_context(chunks: List[RetrievedChunk], max_chunks: int = None) -> tuple[str, List[ContextChunk]]:
    builder = ContextBuilder(max_chunks=max_chunks)
    return builder.build(chunks)