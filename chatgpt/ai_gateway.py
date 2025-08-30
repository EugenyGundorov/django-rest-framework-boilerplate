
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os
import mimetypes
import tempfile
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pybreaker

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)

@dataclass
class ModelParams:
    model: str
    max_output: int = 2048
    base_url: str = ""
    api_key: str = ""

@dataclass
class PromptParams:
    system: str = ""
    user: str = ""

@dataclass
class ClientData:
    text: str = ""
    images: Optional[List[str]] = None

def _as_image_url(s: str) -> str:
    return s

class OpenAIClient:
    def __init__(self, params: ModelParams):
        if not AsyncOpenAI:
            raise RuntimeError("openai package not available")
        key = params.api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not provided")
        kwargs = {}
        if params.base_url:
            kwargs["base_url"] = params.base_url
        self.client = AsyncOpenAI(api_key=key, **kwargs)
        self.params = params

    @breaker
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def generate(self, prompts: PromptParams, data: ClientData) -> Dict[str, Any]:
        content: List[Dict[str, Any]] = []
        if data.text:
            content.append({"type": "input_text", "text": data.text})
        if data.images:
            for img in data.images:
                content.append({"type":"input_image","image_url":{"url":_as_image_url(img)}})
        messages = [{"role":"user","content":content}]
        if prompts.system:
            messages.insert(0, {"role":"system","content":prompts.system})

        resp = await self.client.chat.completions.create(
            model=self.params.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.params.max_output,
        )
        out = resp.choices[0].message.content if resp.choices else ""
        return {"text": out, "raw": resp.model_dump()}

    @breaker
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def run_agent(self, agent_prompt: str, user_text: str, files: Optional[List[str]]=None, knowledge: Optional[List[Dict[str,Any]]]=None) -> Dict[str, Any]:
        # Simple agent: prepends KB to system prompt and attaches files as URLs
        sys_prompt = agent_prompt or ""
        kb_text = ""
        if knowledge:
            # naive top-k concatenate
            parts = []
            for i, item in enumerate(knowledge[:10]):
                title = item.get("title","KB")
                content = item.get("content","")
                parts.append(f"[{i+1}] {title}\n{content}")
            kb_text = "\n\n".join(parts)
        if kb_text:
            sys_prompt = (sys_prompt + "\n\nRelevant Knowledge Base:\n" + kb_text).strip()

        data = ClientData(text=user_text, images=files or [])
        return await self.generate(PromptParams(system=sys_prompt), data)
