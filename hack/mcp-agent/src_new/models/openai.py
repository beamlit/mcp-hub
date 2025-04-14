from google.adk.models.lite_llm import LiteLlm


def gpt4o():
    return LiteLlm(
        "openai/gpt-4o-mini",
        temperature=0
    )

def gpt4o_turbo():
    return LiteLlm(
        "openai/gpt-4o-turbo",
        temperature=0
    )

def gpt4o_mini():
    return LiteLlm(
        "openai/gpt-4o-mini",
        temperature=0
    )
