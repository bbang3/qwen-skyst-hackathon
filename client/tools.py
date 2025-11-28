import os
from typing import Any, Dict

import requests
from agents import function_tool
from dotenv import load_dotenv

import multiprocessing as mp

# Load environment variables
load_dotenv()

from barrierx.client import barrierx


# @barrierx
def make_http_request(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    """Make a simple HTTP request."""

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
        body (any, optional): Request body. If dict, sent as JSON; otherwise as form data

    Returns:
        str: Formatted string containing the response status, headers, and data.
    """

    return make_http_request(url, method, headers, body)
