from .gemini import gemini_flash, gemini_pro
from .openai import gpt4o, gpt4o_mini, gpt4o_turbo


def get_model():
    return gemini_flash()