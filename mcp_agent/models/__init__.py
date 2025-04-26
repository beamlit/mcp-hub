from .gemini import gemini_flash, gemini_pro, gemini_pro_preview
from .openai import gpt4o, gpt4o_mini, gpt_41


def get_model_small():
    return gemini_flash()

def get_model():
    return gemini_pro_preview()

def get_model_big():
    return gemini_pro_preview()