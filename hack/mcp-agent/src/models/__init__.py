from .gemini import gemini_flash, gemini_pro, gemini_pro_preview
from .openai import gpt4o, gpt4o_mini, gpt4o_turbo


def get_model_small():
    return gemini_flash()

def get_model():
    return gpt4o_mini()

def get_model_big():
    return gpt4o()