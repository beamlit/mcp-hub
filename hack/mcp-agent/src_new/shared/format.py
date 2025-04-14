from google.adk.models import LlmResponse
from google.genai import types


def format_markdown_json(content: str) -> str:
    if content.startswith("```json"):
        return content.replace("```json", "").replace("```", "").replace("\n", "")
    else:
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