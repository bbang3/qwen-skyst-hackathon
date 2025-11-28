import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from x402.fastapi.middleware import require_payment

from data_leakage_checker import check_data_leakage
from prompt_injection_checker import check_prompt_injection

# Load environment variables
load_dotenv()

# Get configuration from environment
ADDRESS = os.getenv("SELLER_WALLET_ADDRESS")

if not ADDRESS:
    raise ValueError("Missing required environment variables")

app = FastAPI()

# Apply payment middleware to specific routes
app.middleware("http")(
    require_payment(
        path="/check",
        price="$0.001",
        pay_to_address=ADDRESS,
        network="base-sepolia",
    )
)


class ProxyRequest(BaseModel):
    """Request model for proxy endpoint."""

    url: str
    method: str = "GET"
    headers: Dict[str, str] | None = None
    body: Any | None = None
    payment_info: Dict[str, Any] | None = None


@app.post("/check")
async def check(request: ProxyRequest) -> Dict[str, Any]:
    """Proxy endpoint that safely processes HTTP requests.

    This endpoint:
    1. Validates input for data leakage and prompt injection
    2. Makes the actual HTTP request if validation passes
    3. Validates output for prompt injection
    4. Returns the response or error details
    """
    try:
        target_url = request.url
        method = request.method
        headers = request.headers
        body = request.body

        if not target_url:
            raise HTTPException(status_code=400, detail="Missing required field: 'url'")

        # Convert all input data to string for security checks
        input_data_str = (
            f"Method: {method}\n"
            f"URL: {target_url}\n"
            f"Headers: {headers}\n"
            f"Body: {body}"
        )
        print(f"Input data: {input_data_str}")

        # 1. Check input for data leakage
        # Only detect: CRYPTO, CREDIT_CARD, US_SSN, PHONE_NUMBER, US_BANK_NUMBER
        entities_to_detect = [
            "CRYPTO",
            "CREDIT_CARD",
            "US_SSN",
            "PHONE_NUMBER",
            "US_BANK_NUMBER",
        ]
        is_safe, reason = check_data_leakage(
            input_data_str, entities=entities_to_detect
        )
        if not is_safe:
            raise HTTPException(
                status_code=403,
                detail={"error": "Data leakage detected", "reason": reason},
            )

        # 2. Make the actual HTTP request
        try:
            response = requests.request(
                url=target_url,
                method=method,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                data=body if not isinstance(body, dict) else None,
                timeout=30,
            )

            # Get response content
            if "application/json" in response.headers.get("content-type", ""):
                response_data = response.json()
            else:
                response_data = response.text

            # 3. Check output for prompt injection
            output_str = str(response_data)
            is_safe, reason = check_prompt_injection(output_str)
            if not is_safe:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Prompt injection detected in response",
                        "reason": reason,
                    },
                )

            # Return successful response
            return {
                "status_code": response.status_code,
                "data": response_data,
                "headers": dict(response.headers),
            }

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "Failed to make request", "details": str(e)},
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "details": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4021)
