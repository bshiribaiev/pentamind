"""
DigitalOcean Serverless Inference API wrapper.
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
import httpx
from .types import Message, ModelCallResult

logger = logging.getLogger(__name__)

DO_INFERENCE_URL = "https://inference.do-ai.run/v1/chat/completions"
DEFAULT_TIMEOUT = 60.0


class ModelAPIError(Exception):
    """Custom exception for model API errors."""
    pass


def get_model_access_key() -> str:
    """Get MODEL_ACCESS_KEY from environment."""
    key = os.environ.get("MODEL_ACCESS_KEY")
    if not key:
        raise ModelAPIError("MODEL_ACCESS_KEY environment variable not set")
    return key


def call_do_chat_completion(
    model: str,
    messages: List[Message],
    max_tokens: int = 200,
    temperature: float = 0.2,
    timeout: float = DEFAULT_TIMEOUT,
) -> ModelCallResult:
    """
    Call DigitalOcean Serverless Inference API.
    
    Args:
        model: Model identifier (e.g., "anthropic-claude-sonnet-4")
        messages: List of chat messages
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
        
    Returns:
        ModelCallResult with content, latency, and usage stats
        
    Raises:
        ModelAPIError: On API errors, timeouts, or invalid responses
    """
    start_time = time.time()
    
    try:
        access_key = get_model_access_key()
    except ModelAPIError:
        raise
    
    # Prepare request payload
    payload = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    headers = {
        "Authorization": f"Bearer {access_key}",
        "Content-Type": "application/json",
    }
    
    try:
        with httpx.Client(timeout=timeout) as client:
            logger.info(f"Calling model: {model} (timeout={timeout}s)")
            response = client.post(
                DO_INFERENCE_URL,
                json=payload,
                headers=headers,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Check for non-200 responses
            if response.status_code != 200:
                error_detail = response.text[:200]  # Truncate for logging
                logger.error(
                    f"Model API returned {response.status_code}: {error_detail}"
                )
                raise ModelAPIError(
                    f"API returned status {response.status_code}: {error_detail}"
                )
            
            # Parse response
            try:
                data = response.json()
            except Exception as e:
                raise ModelAPIError(f"Failed to parse JSON response: {e}")
            
            # Extract content
            if "choices" not in data or len(data["choices"]) == 0:
                raise ModelAPIError("No choices in API response")
            
            content = data["choices"][0].get("message", {}).get("content", "")
            if not content:
                raise ModelAPIError("Empty content in API response")
            
            # Extract usage stats if available
            usage = data.get("usage", {})
            
            logger.info(
                f"Model {model} responded in {latency_ms}ms "
                f"({len(content)} chars)"
            )
            
            return ModelCallResult(
                content=content,
                latency_ms=latency_ms,
                usage=usage,
                model=model,
            )
            
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Timeout calling model {model} after {latency_ms}ms")
        raise ModelAPIError(f"Request timeout after {timeout}s")
    
    except httpx.RequestError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Request error calling model {model}: {e}")
        raise ModelAPIError(f"Request failed: {str(e)}")
    
    except ModelAPIError:
        # Re-raise our custom exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error calling model {model}: {e}")
        raise ModelAPIError(f"Unexpected error: {str(e)}")


def call_with_text_messages(
    model: str,
    user_message: str,
    system_message: Optional[str] = None,
    max_tokens: int = 200,
    temperature: float = 0.2,
    timeout: float = DEFAULT_TIMEOUT,
) -> ModelCallResult:
    """
    Convenience wrapper for simple text-based model calls.
    
    Args:
        model: Model identifier
        user_message: User message content
        system_message: Optional system message
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
        
    Returns:
        ModelCallResult
    """
    messages = []
    
    if system_message:
        messages.append(Message(role="system", content=system_message))
    
    messages.append(Message(role="user", content=user_message))
    
    return call_do_chat_completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )

