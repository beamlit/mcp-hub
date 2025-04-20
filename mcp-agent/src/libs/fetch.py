import requests


def fetch_url(url: str) -> str:
    """
    Fetch the content of a URL
    Args:
        url: The URL to fetch the content from.
    Returns:
        The content of the URL.
    """
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return "Could not fetch content from URL"