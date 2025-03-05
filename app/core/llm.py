import logging
import json
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    Service for processing text with LLMs.
    """
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.default_model = "claude-3-opus-20240229"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError))
    )
    async def process(
        self, 
        prompt_template: str, 
        variables: Dict[str, Any],
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        extract_json: bool = True
    ) -> Dict[str, Any]:
        """
        Process text with LLM.
        
        Args:
            prompt_template: The prompt template to use
            variables: Variables to substitute in the prompt template
            model: LLM model to use (defaults to claude-3-opus)
            max_tokens: Maximum tokens to generate
            temperature: Temperature parameter for generation (0.0-1.0)
            extract_json: Whether to extract JSON from the response
            
        Returns:
            Processed response as a dictionary
        """
        try:
            # Format the prompt with variables
            prompt = prompt_template.format(**variables)
            
            # Call the LLM
            response = await self.client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = response.content[0].text
            
            # Extract JSON if requested
            if extract_json:
                try:
                    # Find JSON pattern in text
                    json_str = self._extract_json_string(response_text)
                    if json_str:
                        return json.loads(json_str)
                    
                    # If no JSON pattern found, try to parse the entire response
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to extract JSON from response: {e}")
                    logger.debug(f"Response text: {response_text}")
                    return {"text": response_text, "error": "Failed to extract JSON"}
            
            return {"text": response_text}
        
        except Exception as e:
            logger.error(f"Error processing with LLM: {e}")
            return {"error": str(e)}
    
    def _extract_json_string(self, text: str) -> Optional[str]:
        """
        Extract JSON string from text that might have additional content.
        """
        # Look for JSON pattern
        start_idx = text.find('{')
        
        if start_idx == -1:
            return None
        
        # Count braces to find the matching closing brace
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                
            if brace_count == 0:
                return text[start_idx:i+1]
        
        return None