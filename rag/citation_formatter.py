import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from .context_builder import ContextChunk

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    doc: str
    page: int
    section: str


class CitationFormatter:
    def __init__(self):
        pass
    
    def format(self, context_chunks: List[ContextChunk]) -> List[Citation]:
        citations = []
        seen = set()
        
        for chunk in context_chunks:
            key = (chunk.doc, chunk.page, chunk.section)
            if key not in seen:
                seen.add(key)
                citations.append(Citation(
                    doc=chunk.doc,
                    page=chunk.page,
                    section=chunk.section
                ))
        
        logger.info(f"Formatted {len(citations)} unique citations")
        return citations
    
    def format_for_frontend(self, context_chunks: List[ContextChunk]) -> List[Dict[str, Any]]:
        citations = self.format(context_chunks)
        return [asdict(c) for c in citations]


def format_citations(context_chunks: List[ContextChunk]) -> List[Dict[str, Any]]:
    formatter = CitationFormatter()
    return formatter.format_for_frontend(context_chunks)