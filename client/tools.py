import os
from typing import Any, Dict

import requests
from agents import function_tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@function_tool
def make_http_request(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    """Make a simple HTTP request.

    This tool performs the same HTTP request functionality as the /check endpoint
    in server/main.py but without any security validation (data leakage or
    prompt injection checks). Use this to compare behavior with the secure proxy.

    Args:
        url (str): The target URL to send the request to
        method (str): HTTP method (GET, POST, PUT, DELETE, etc.). Defaults to "GET"
        headers (dict, optional): HTTP headers to include in the request
        body (any, optional): Request body. If dict, sent as JSON; otherwise as form data

    Returns:
        str: Formatted string containing the response status, headers, and data
    """
    try:
        # Make the HTTP request
        response = requests.request(
            url=url,
            method=method,
            headers=headers,
            data=body,
            timeout=30,
        )

        # Get response content
        if "application/json" in response.headers.get("content-type", ""):
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
        else:
            response_data = response.text

        # Format response for display
        result = f"Status Code: {response.status_code}\n"
        result += f"Headers: {dict(response.headers)}\n"
        result += f"\nResponse Data:\n{response_data}"

        return result

    except requests.exceptions.RequestException as e:
        return f"Error making HTTP request: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
