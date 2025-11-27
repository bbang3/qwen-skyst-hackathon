import os

import requests
from agents import function_tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get search proxy server URL from environment
SEARCH_PROXY_URL = os.getenv("SEARCH_PROXY_URL", "http://localhost:4021/search")


@function_tool
def get_today_fortune(birth_animal: str) -> str:
    """Get today's fortune based on birth animal (zodiac sign).

    Args:
        birth_animal (str): Birth animal (e.g., "쥐", "소", "호랑이", ...)
    """
    return f"{birth_animal}띠의 오늘의 운세: 당신은 행운이 가득할 것입니다."


@function_tool
def search_web(query: str, max_results: int = 5) -> str:
    """Perform web search using DuckDuckGo and return formatted results.

    Args:
        query (str): Search keywords or question
        max_results (int): Maximum number of results to return (default: 5)

    Returns:
        str: Formatted string containing search results
    """
    try:
        # Send POST request to proxy server
        response = requests.post(
            SEARCH_PROXY_URL,
            json={"query": query, "max_results": max_results},
            timeout=30,
        )

        # Check if request was successful
        if response.status_code == 400:
            return f"Search request rejected: {response.json().get('detail', 'Malicious prompt detected')}"

        response.raise_for_status()

        # Parse response
        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"'{query}' search results not found."

        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            snippet = result.get("body", "No description")
            url = result.get("href", "")
            formatted_results.append(f"{i}. {title}\n   {snippet}\n   {url}")
            print(snippet)

        return f"'{query}' search results:\n\n" + "\n\n".join(formatted_results)
    except requests.exceptions.RequestException as e:
        return f"An error occurred while searching: {str(e)}"
    except Exception as e:
        return f"An error occurred while searching: {str(e)}"
