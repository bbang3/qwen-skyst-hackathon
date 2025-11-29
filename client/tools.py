from typing import Dict

import requests
from agents import function_tool
from barrierx.client import barrierx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@function_tool
@barrierx
def web_tool(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    """Make a simple HTTP request. This tool is used to make HTTP requests to the target URL.

    Args:
        url (str): The target URL to send the request to
        method (str): HTTP method (GET, POST, PUT, DELETE, etc.). Defaults to "GET"
        headers (dict, optional): HTTP headers to include in the request
        body (any, optional): Request body.

    Returns:
        str: Formatted string containing the response status, headers, and data.
    """

    response = requests.request(
        url=url,
        method=method,
        headers=headers,
        data=body,
        timeout=30,
    )
    response_str = f"Status Code: {response.status_code}\n"
    response_str += f"Headers: {dict(response.headers)}\n"
    response_str += f"\nResponse Data:\n{response.text}"
    return response_str


@function_tool
@barrierx
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo API.

    Args:
        query (str): The search query

    Returns:
        str: Formatted search results with titles, descriptions, and URLs
    """
    try:
        # DuckDuckGo JSON API
        url = f"https://api.duckduckgo.com/?q={query}&format=json"

        response = requests.get(url=url, timeout=10)

        import pdb

        pdb.set_trace()
        data = response.json()
        results = []

        # Check for instant answer
        if data.get("AbstractText"):
            results.append(
                f"Title: {data.get('Heading', 'Answer')}\n"
                f"URL: {data.get('AbstractURL', 'N/A')}\n"
                f"Description: {data.get('AbstractText')}\n"
            )

        # Check RelatedTopics for search results
        for topic in data.get("RelatedTopics", [])[:10]:
            if isinstance(topic, dict):
                # Handle nested topics
                if "Topics" in topic:
                    for subtopic in topic["Topics"][:5]:
                        if "Text" in subtopic and "FirstURL" in subtopic:
                            results.append(
                                f"Title: {subtopic.get('Text', '').split(' - ')[0]}\n"
                                f"URL: {subtopic.get('FirstURL', '')}\n"
                                f"Description: {subtopic.get('Text', 'No description available')}\n"
                            )
                elif "Text" in topic and "FirstURL" in topic:
                    results.append(
                        f"Title: {topic.get('Text', '').split(' - ')[0]}\n"
                        f"URL: {topic.get('FirstURL', '')}\n"
                        f"Description: {topic.get('Text', 'No description available')}\n"
                    )

        if not results:
            return "No search results found."

        return f"Search Results for '{query}':\n\n" + "\n---\n".join(results)

    except Exception as e:
        print(f"Error performing search: {str(e)}")
        return f"Error performing search: {str(e)}"
