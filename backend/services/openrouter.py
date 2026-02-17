import httpx
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from cachetools import TTLCache

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

_models_cache = TTLCache(maxsize=1, ttl=300)

FREE_MODEL_PATTERNS = [
    "free",
    ":free",
    "/free",
]

EXCLUDED_PATTERNS = [
    "image",
    "vision",
    "whisper",
    "tts",
    "embedding",
    "moderation",
    "dall-e",
    "stable-diffusion",
]


async def fetch_models_from_openrouter() -> List[Dict[str, Any]]:
    """Fetch all models from OpenRouter API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Content-Type": "application/json"}
        if OPENROUTER_API_KEY:
            headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"

        response = await client.get(f"{OPENROUTER_BASE_URL}/models", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])


def is_free_model(model_id: str, model_data: Dict) -> bool:
    """Check if a model is free"""
    model_id_lower = model_id.lower()
    for pattern in FREE_MODEL_PATTERNS:
        if pattern in model_id_lower:
            return True

    pricing = model_data.get("pricing", {})
    prompt_price = float(pricing.get("prompt", "1") or "1")
    completion_price = float(pricing.get("completion", "1") or "1")

    return prompt_price == 0 and completion_price == 0


def supports_tools(model_data: Dict) -> bool:
    """Check if model supports tools/function calling"""
    architecture = model_data.get("architecture", {})
    modality = architecture.get("modality", "")
    input_modalities = architecture.get("input_modalities", [])
    output_modalities = architecture.get("output_modalities", [])

    if "text" not in input_modalities:
        return False

    if "text" not in output_modalities:
        return False

    model_id = model_data.get("id", "").lower()
    for excluded in EXCLUDED_PATTERNS:
        if excluded in model_id:
            return False

    description = model_data.get("description", "") or ""
    name = model_data.get("name", "") or ""

    tool_indicators = ["tool", "function", "tool_use", "function_call"]
    combined_text = f"{model_id} {name} {description}".lower()

    for indicator in tool_indicators:
        if indicator in combined_text:
            return True

    supported_params = model_data.get("supported_parameters", [])
    if "tools" in supported_params or "tool_choice" in supported_params:
        return True

    return True


async def get_tool_capable_models() -> List[Dict[str, Any]]:
    """Get all models that support tools, with caching"""
    cache_key = "tool_models"
    if cache_key in _models_cache:
        return _models_cache[cache_key]

    all_models = await fetch_models_from_openrouter()

    tool_models = []
    for model in all_models:
        if supports_tools(model):
            model_id = model.get("id", "")
            tool_models.append(
                {
                    "id": model_id,
                    "name": model.get("name", model_id),
                    "provider": model_id.split("/")[0]
                    if "/" in model_id
                    else "unknown",
                    "is_free": is_free_model(model_id, model),
                    "pricing": model.get("pricing", {}),
                    "context_length": model.get("context_length", 4096),
                    "description": model.get("description", ""),
                }
            )

    tool_models.sort(key=lambda x: (not x["is_free"], x["name"].lower()))

    _models_cache[cache_key] = tool_models
    return tool_models


def get_default_free_model() -> Optional[str]:
    """Get a default free model ID"""
    return "meta-llama/llama-3.3-8b-instruct:free"
