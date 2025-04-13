from google.adk.models.lite_llm import LiteLlm


def gemini_flash():
    return LiteLlm(
        "gemini/gemini-2.0-flash",
        temperature=0
    )

def gemini_pro_preview():
    return LiteLlm(
        "gemini/gemini-2.5-pro-preview-03-25",
        temperature=0
    )

def gemini_pro():
    return LiteLlm(
        "gemini/gemini-2.5-pro-exp-03-25",
        temperature=0
    )
