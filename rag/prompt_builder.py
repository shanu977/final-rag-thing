import logging
from typing import List
from dataclasses import dataclass

from .context_builder import ContextChunk

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the KIET College AI Assistant.

Answer the user's question using ONLY the information provided in the retrieved knowledge-base context.

Rules:

1. Do not invent facts.
2. Do not use outside knowledge.
3. If the answer is not contained in the provided context, clearly say that the information is not available in the KIET knowledge base.
4. Preserve names, numbers, dates, percentages, timings, and policies accurately.
5. Give a concise and useful answer.
6. Use the provided source information when forming the answer.
7. Never fabricate citations."""


@dataclass
class Prompt:
    system: str
    user: str
    messages: List[dict]


class PromptBuilder:
    def __init__(self, system_prompt: str = None):
        self.system_prompt = system_prompt or SYSTEM_PROMPT
    
    def build(self, question: str, context: str, context_chunks: List[ContextChunk]) -> Prompt:
        if context:
            user_prompt = f"""Based on the following retrieved knowledge base context, answer the user's question.

Context:
{context}

Question: {question}

Answer the question using only the information from the context above. If the answer is not in the context, state that the information is not available in the KIET knowledge base."""
        else:
            user_prompt = f"""The knowledge base did not return any relevant information for this question.

Question: {question}

Answer: I couldn't find that information in the KIET College knowledge base."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.debug(f"Built prompt with {len(context_chunks)} context chunks")
        
        return Prompt(
            system=self.system_prompt,
            user=user_prompt,
            messages=messages
        )


def build_prompt(question: str, context: str, context_chunks: List[ContextChunk]) -> Prompt:
    builder = PromptBuilder()
    return builder.build(question, context, context_chunks)