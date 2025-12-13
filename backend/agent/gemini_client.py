"""
Google Gemini API integration for long-context tasks.
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(Exception):
    """Custom exception for Gemini API errors."""
    pass


def get_gemini_key() -> Optional[str]:
    """Get GEMINI_API_KEY from environment."""
    return os.environ.get("GEMINI_API_KEY")


def call_gemini(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.5-pro",
    max_tokens: int = 8000,
    temperature: float = 0.3,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Call Google Gemini API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model identifier (gemini-1.5-pro-latest, gemini-1.5-flash-latest)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with content, latency_ms, usage, and model
        
    Raises:
        GeminiError: On API errors or configuration issues
    """
    start_time = time.time()
    
    api_key = get_gemini_key()
    if not api_key:
        raise GeminiError("GEMINI_API_KEY not set")
    
    # Convert messages to Gemini format
    contents = []
    system_instruction = None
    
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}]
            })
        elif msg["role"] == "assistant":
            contents.append({
                "role": "model",
                "parts": [{"text": msg["content"]}]
            })
    
    # Build request
    url = f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
    }
    
    # Add system instruction if provided
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    
    try:
        logger.info(f"Calling Gemini model: {model}")
        
        response = requests.post(
            url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code != 200:
            error_detail = response.text[:200]
            logger.error(f"Gemini API error {response.status_code}: {error_detail}")
            raise GeminiError(f"API returned {response.status_code}: {error_detail}")
        
        data = response.json()
        
        # Extract response
        if "candidates" not in data or len(data["candidates"]) == 0:
            raise GeminiError("No candidates in response")
        
        candidate = data["candidates"][0]
        
        if "content" not in candidate:
            raise GeminiError("No content in candidate")
        
        parts = candidate["content"].get("parts", [])
        if not parts:
            raise GeminiError("No parts in content")
        
        content = parts[0].get("text", "")
        
        # Extract usage stats
        usage_metadata = data.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
            "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
            "total_tokens": usage_metadata.get("totalTokenCount", 0),
        }
        
        logger.info(f"Gemini responded in {latency_ms}ms ({len(content)} chars)")
        
        return {
            "content": content,
            "latency_ms": latency_ms,
            "usage": usage,
            "model": model,
        }
        
    except requests.RequestException as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Gemini request failed: {e}")
        raise GeminiError(f"Request failed: {str(e)}")
    
    except GeminiError:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected Gemini error: {e}")
        raise GeminiError(f"Unexpected error: {str(e)}")


def is_gemini_available() -> bool:
    """Check if Gemini API key is configured."""
    return get_gemini_key() is not None


def get_appropriate_gemini_model(input_length: int) -> str:
    """
    Select appropriate Gemini model based on input length.
    
    Args:
        input_length: Length of input in characters
        
    Returns:
        Model name
    """
    # Gemini 1.5 Pro: Best for long context (up to 2M tokens)
    # Gemini 1.5 Flash: Faster, cheaper (up to 1M tokens)
    
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = input_length // 4
    
    if estimated_tokens > 100000:  # > 100K tokens
        return "gemini-2.5-pro"
    elif estimated_tokens > 10000:  # > 10K tokens
        return "gemini-2.5-pro"
    else:
        return "gemini-2.5-flash"  # Fast for shorter contexts

