import json
import logging
import requests
from typing import List
from dataclasses import dataclass

from .config import config
from .prompt_builder import Prompt

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    answer: str
    model: str
    usage: dict = None


class GroqClient:
    def __init__(self, api_key: str = None, model: str = None, timeout: int = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or config.GROQ_MODEL
        self.timeout = timeout or config.GROQ_TIMEOUT
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")
    
    def chat(self, prompt: Prompt) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": prompt.messages,
            "temperature": 0.1,
            "max_tokens": 1024
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "KIET-RAG/1.0"
        }
        
        try:
            logger.info(f"Calling Groq API with model: {self.model}")
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            answer = data['choices'][0]['message']['content']
            usage = data.get('usage', {})
            
            logger.info(f"Groq response received (tokens: {usage.get('total_tokens', 'unknown')})")
            
            return LLMResponse(
                answer=answer.strip(),
                model=self.model,
                usage=usage
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"Groq API timeout after {self.timeout}s")
            raise Exception("The AI service timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            raise Exception("The AI service is unavailable right now.")
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Groq response format: {e}")
            raise Exception("The AI service returned an unexpected response.")


_llm_client = None


def get_llm_client() -> GroqClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = GroqClient()
    return _llm_client


def call_groq(prompt: Prompt) -> LLMResponse:
    return get_llm_client().chat(prompt)