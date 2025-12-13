"""
Perplexity API integration for search and research tasks.
"""
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PerplexityError(Exception):
    """Custom exception for Perplexity API errors."""
    pass


def get_perplexity_key() -> Optional[str]:
    """Get PERPLEXITY_API_KEY from environment."""
    return os.environ.get("PERPLEXITY_API_KEY")


def search_with_perplexity(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Perform a search using Perplexity Search API.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary with search results and sources
        
    Raises:
        PerplexityError: On API errors or if API key is missing
    """
    api_key = get_perplexity_key()
    
    if not api_key:
        logger.warning("PERPLEXITY_API_KEY not set, skipping Perplexity search")
        raise PerplexityError("PERPLEXITY_API_KEY not configured")
    
    try:
        from perplexity import Perplexity
        
        logger.info(f"Performing Perplexity search: {query[:100]}...")
        
        # Initialize client with API key
        client = Perplexity(api_key=api_key)
        
        # Perform search
        search = client.search.create(
            query=query,
            max_results=max_results,
            max_tokens_per_page=1024
        )
        
        # Extract results
        results = []
        for result in search.results:
            results.append({
                "title": result.title,
                "url": result.url,
                "snippet": getattr(result, 'snippet', ''),
            })
        
        logger.info(f"Found {len(results)} results from Perplexity")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "source": "perplexity",
            "count": len(results),
        }
    
    except ImportError:
        logger.error("Perplexity package not installed")
        raise PerplexityError(
            "Perplexity package not installed. Run: pip install perplexityai"
        )
    
    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        raise PerplexityError(f"Search failed: {str(e)}")


def format_search_results_for_llm(search_data: Dict[str, Any]) -> str:
    """
    Format search results into a string for LLM context.
    
    Args:
        search_data: Search results from search_with_perplexity
        
    Returns:
        Formatted string with search results
    """
    if not search_data.get("success"):
        return "No search results available."
    
    results = search_data.get("results", [])
    if not results:
        return "No search results found."
    
    # Build context string
    context_parts = [
        f"Search Results for: {search_data['query']}",
        f"Found {len(results)} relevant sources:",
        ""
    ]
    
    for i, result in enumerate(results, 1):
        context_parts.append(f"{i}. {result['title']}")
        context_parts.append(f"   URL: {result['url']}")
        if result.get('snippet'):
            context_parts.append(f"   {result['snippet']}")
        context_parts.append("")
    
    return "\n".join(context_parts)


def search_and_synthesize(
    query: str,
    model_executor: callable,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Search with Perplexity and synthesize results using an LLM.
    
    Args:
        query: User's research question
        model_executor: Function to call LLM (should accept prompt string)
        max_results: Maximum search results to include
        
    Returns:
        Dictionary with synthesized answer and sources
    """
    try:
        # Perform search
        search_data = search_with_perplexity(query, max_results)
        
        # Format for LLM
        search_context = format_search_results_for_llm(search_data)
        
        # Build synthesis prompt
        synthesis_prompt = f"""Based on the following search results, provide a comprehensive answer to the user's question.

User Question: {query}

{search_context}

Instructions:
- Synthesize the information from the search results
- Provide a clear, well-structured answer
- Cite sources using [1], [2], etc. when making specific claims
- If the search results don't fully answer the question, acknowledge that

Your answer:"""
        
        # Get LLM response
        llm_response = model_executor(synthesis_prompt)
        
        # Build source list
        sources = [
            f"[{i}] {r['title']} - {r['url']}"
            for i, r in enumerate(search_data['results'], 1)
        ]
        
        return {
            "success": True,
            "answer": llm_response,
            "sources": sources,
            "raw_search": search_data,
        }
        
    except PerplexityError as e:
        logger.warning(f"Perplexity search unavailable: {e}")
        # Fall back to LLM without search
        return {
            "success": False,
            "answer": None,
            "sources": [],
            "error": str(e),
        }

