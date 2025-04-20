import re

from google.adk.models import LlmResponse
from google.genai import types


def format_markdown_json(content: str) -> str:
    """
    Extract JSON content from markdown code blocks.

    Args:
        content: String that may contain markdown code blocks with JSON

    Returns:
        Extracted JSON content or original content if no JSON code block found
    """
    # Match ```json followed by any content (non-greedy) until ```
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    return content

def format_markdown_llm_response(llm_response: LlmResponse) -> LlmResponse:
    modified_parts = []
    for part in llm_response.content.parts:
        if part.text:
            modified_parts.append(types.Part(text=format_markdown_json(part.text)))
        else:
            modified_parts.append(part)

    new_response = LlmResponse(
        content=types.Content(role="model", parts=modified_parts),
        grounding_metadata=llm_response.grounding_metadata
    )
    return new_response