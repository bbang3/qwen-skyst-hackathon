import json
from typing import Any

import requests
from coinbase_agentkit.action_providers.action_decorator import create_action
from coinbase_agentkit.action_providers.action_provider import ActionProvider
from coinbase_agentkit.action_providers.x402.x402_action_provider import (
    DirectX402RequestSchema,
    HttpRequestSchema,
    RetryWithX402Schema,
)
from coinbase_agentkit.network import Network
from coinbase_agentkit.wallet_providers.evm_wallet_provider import EvmWalletProvider
from x402.clients.requests import x402_requests
from x402.types import PaymentRequirements

from .constants import BARRIERX_PROXY_URL

SUPPORTED_NETWORKS = ["base-mainnet", "base-sepolia"]


class BarrierXActionProvider(ActionProvider[EvmWalletProvider]):  # noqa: N801
    """Provides actions for interacting with x402.

    This provider enables making HTTP requests to x402-protected endpoints with optional payment handling.
    It supports both a recommended two-step flow and a direct payment flow.
    """

    def __init__(self):
        super().__init__("x402", [])

    def _send_to_proxy(
        self,
        wallet_provider: EvmWalletProvider,
        request_payload: dict[str, Any],
        payment_info: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Send HTTP request payload to proxy server for safe processing using x402_requests.

        Args:
            wallet_provider: The wallet provider to use for x402 payment handling.
            request_payload: The original HTTP request details (url, method, headers, body).
            payment_info: Optional payment information for x402 requests.

        Returns:
            Response from proxy server.
        """
        # Prepare proxy payload
        proxy_payload = {
            "url": request_payload.get("url", "error"),
            "method": request_payload.get("method", "GET"),
            "headers": request_payload.get("headers"),
            "body": request_payload.get("body"),
        }

        if payment_info:
            proxy_payload["payment_info"] = payment_info

        # Convert proxy payload to JSON string for the body
        body_data = json.dumps(proxy_payload)

        # Create x402 session
        account = wallet_provider.to_signer()
        # If payment_info is provided and not auto_payment, create a payment selector
        if payment_info and not payment_info.get("auto_payment"):
            # Create payment selector function for specific payment option
            def payment_selector(
                payment_options: list[PaymentRequirements],
                network_filter: str | None = None,
                scheme_filter: str | None = None,
                max_value: int | None = None,
            ) -> PaymentRequirements:
                network = network_filter or payment_info["network"]
                scheme = scheme_filter or payment_info["scheme"]
                max_amount = max_value or int(payment_info["max_amount_required"])
                pay_to = payment_info["pay_to"]
                asset = payment_info["asset"]

                for req in payment_options:
                    req_dict = req if isinstance(req, dict) else req.dict()
                    if (
                        req_dict["network"] == network
                        and req_dict["scheme"] == scheme
                        and req_dict["pay_to"] == pay_to
                        and req_dict["asset"] == asset
                        and int(req_dict["max_amount_required"]) <= max_amount
                    ):
                        return PaymentRequirements(**req_dict)

                # Fallback: try matching just network, payTo and asset
                for req in payment_options:
                    req_dict = req if isinstance(req, dict) else req.dict()
                    if (
                        req_dict["network"] == network
                        and req_dict["pay_to"] == pay_to
                        and req_dict["asset"] == asset
                        and int(req_dict["max_amount_required"]) <= max_amount
                    ):
                        return PaymentRequirements(**req_dict)

                raise ValueError(
                    "No matching payment requirements found for the selected criteria"
                )

            session = x402_requests(
                account, payment_requirements_selector=payment_selector
            )
        else:
            # Auto-payment or no payment info - use default x402_requests
            session = x402_requests(account)

        # Make request to proxy server using x402_requests
        response = session.request(
            url=BARRIERX_PROXY_URL,
            method="POST",
            headers={"Content-Type": "application/json"},
            data=body_data,
        )
        print(f"BarrierX Action Provider Response: {response.text}")
        return response

    @create_action(
        name="make_safe_web_request",
        description="""
        Makes a safe HTTP request through a proxy server to protect against prompt injection,
        data exfiltration, and other security risks. The request is sent to a proxy server
        which processes it safely before forwarding to the target endpoint.

        EXAMPLES:
        - Production API: make_safe_web_request("https://api.example.com/weather")
        - Local development: make_safe_web_request("http://localhost:3000/api/data")
        - Testing x402: make_safe_web_request("http://localhost:3000/protected")

        If you receive a 402 Payment Required response, use retry_safe_web_request_with_x402 to handle the payment.""",
        schema=HttpRequestSchema,
    )
    def make_safe_web_request(
        self, wallet_provider: EvmWalletProvider, args: dict[str, Any]
    ) -> str:
        """Make safe HTTP request through proxy server and handle 402 responses.

        Args:
            wallet_provider: The wallet provider (not used for initial request).
            args: Request parameters including URL, method, headers, and body.

        Returns:
            str: JSON string containing response data or payment requirements.

        """
        try:
            # Send request to proxy server
            proxy_response = self._send_to_proxy(wallet_provider, args)

            # Parse proxy server response
            if proxy_response.status_code != 200:
                # Non-200 from the BarrierX proxy (e.g. 403 prompt injection).
                # Preserve HTTP status and body so callers can see the original
                # error details (including the prompt-injection reason).
                try:
                    error_body: Any = proxy_response.json()
                except ValueError:
                    error_body = proxy_response.text

                return json.dumps(
                    {
                        "success": False,
                        "url": args.get("url", "error"),
                        "method": args.get("method", "GET"),
                        "status": proxy_response.status_code,
                        "data": error_body,
                        "headers": dict(proxy_response.headers),
                    },
                    indent=2,
                )

            proxy_data = proxy_response.json()

            # Check if proxy returned a 402 response
            if proxy_data.get("status") == 402 or proxy_data.get("status_code") == 402:
                # Parse payment requirements from 402 response
                accepts = proxy_data.get("accepts", [])
                payment_requirements = [
                    PaymentRequirements(**accept) for accept in accepts
                ]

                return json.dumps(
                    {
                        "status": "error_402_payment_required",
                        "acceptablePaymentOptions": [
                            req.dict() for req in payment_requirements
                        ],
                        "nextSteps": [
                            "Inform the user that the requested server replied with a 402 Payment Required response.",
                            f"The payment options are: {', '.join(f'{req.asset} {req.max_amount_required} {req.network}' for req in payment_requirements)}",
                            "Ask the user if they want to retry the request with payment.",
                            "Use retry_safe_web_request_with_x402 to retry the request with payment.",
                        ],
                    },
                    indent=2,
                )

            # Handle successful response
            return json.dumps(
                {
                    "success": True,
                    "url": args.get("url", "error"),
                    "method": args.get("method", "GET"),
                    "status": proxy_data.get("status_code", proxy_response.status_code),
                    "data": proxy_data.get("data", proxy_data),
                },
                indent=2,
            )

        except Exception as error:
            print("Error making safe request:", str(error))
            return self._handle_http_error(error, args.get("url", "error"))

    @create_action(
        name="retry_safe_web_request_with_x402",
        description="""
        Retries a safe web request with x402 payment after receiving a 402 Payment Required response.
        This should be used after make_safe_web_request returns a 402 response.

        EXAMPLE WORKFLOW:
        1. First call make_safe_web_request("http://localhost:3000/protected")
        2. If you get a 402 response, use this action to retry with payment
        3. Pass the original request parameters and payment details to this action

        DO NOT use this action directly without first trying make_safe_web_request!""",
        schema=RetryWithX402Schema,
    )
    def retry_safe_web_request_with_x402(
        self, wallet_provider: EvmWalletProvider, args: dict[str, Any]
    ) -> str:
        """Retry a safe web request with x402 payment through proxy server."""
        try:
            # Prepare payment information
            payment_info = {
                "network": args["network"],
                "scheme": args["scheme"],
                "max_amount_required": args["max_amount_required"],
                "pay_to": args["pay_to"],
                "asset": args["asset"],
            }

            # Prepare request payload
            request_payload = {
                "url": args.get("url", "error"),
                "method": args.get("method", "GET"),
                "headers": args.get("headers"),
                "body": args.get("body"),
            }

            # Send to proxy server with payment info
            proxy_response = self._send_to_proxy(
                wallet_provider, request_payload, payment_info
            )

            if proxy_response.status_code != 200:
                try:
                    error_body: Any = proxy_response.json()
                except ValueError:
                    error_body = proxy_response.text

                return json.dumps(
                    {
                        "success": False,
                        "url": args.get("url", "error"),
                        "method": args.get("method", "GET"),
                        "status": proxy_response.status_code,
                        "data": error_body,
                        "headers": dict(proxy_response.headers),
                    },
                    indent=2,
                )

            proxy_data = proxy_response.json()

            return json.dumps(
                {
                    "success": True,
                    "data": proxy_data.get("data", proxy_data),
                    "message": "Request completed successfully with payment",
                    "details": {
                        "url": args.get("url", "error"),
                        "method": args.get("method", "GET"),
                        "paymentUsed": {
                            "network": args["network"],
                            "asset": args["asset"],
                            "amount": args["max_amount_required"],
                        },
                        "paymentProof": proxy_data.get("paymentProof"),
                    },
                },
                indent=2,
            )

        except Exception as error:
            print("Error retrying safe request:", str(error))
            return self._handle_http_error(error, args.get("url", "error"))

    @create_action(
        name="make_safe_web_request_with_x402",
        description="""
        ⚠️ WARNING: This action automatically handles payments without asking for confirmation!
        Only use this when explicitly told to skip the confirmation flow.

        Makes a safe HTTP request through a proxy server with automatic x402 payment handling.
        The request is sent to a proxy server which processes it safely before forwarding to the target endpoint.

        For most cases, you should:
        1. First try make_safe_web_request
        2. Then use retry_safe_web_request_with_x402 if payment is required

        This action combines both steps into one, which means:
        - No chance to review payment details before paying
        - No confirmation step
        - Automatic payment processing

        EXAMPLES:
        - Production: make_safe_web_request_with_x402("https://api.example.com/data")
        - Local dev: make_safe_web_request_with_x402("http://localhost:3000/protected")

        Unless specifically instructed otherwise, prefer the two-step approach with make_safe_web_request first.""",
        schema=DirectX402RequestSchema,
    )
    def make_safe_web_request_with_x402(
        self, wallet_provider: EvmWalletProvider, args: dict[str, Any]
    ) -> str:
        """Make safe HTTP request through proxy server with automatic x402 payment handling.

        Args:
            wallet_provider: The wallet provider to use for payment signing.
            args: Request parameters including URL, method, headers, and body.

        Returns:
            str: JSON string containing response data and optional payment proof.

        """
        try:
            # Prepare request payload
            request_payload = {
                "url": args.get("url", "error"),
                "method": args.get("method", "GET"),
                "headers": args.get("headers"),
                "body": args.get("body"),
            }

            # Send to proxy server with auto-payment flag
            # The proxy server will handle payment automatically if needed

            payment_info = {"auto_payment": True}
            proxy_response = self._send_to_proxy(
                wallet_provider, request_payload, payment_info
            )

            if proxy_response.status_code != 200:
                try:
                    error_body: Any = proxy_response.json()
                except ValueError:
                    error_body = proxy_response.text

                return json.dumps(
                    {
                        "success": False,
                        "url": args.get("url", "error"),
                        "method": args.get("method", "GET"),
                        "status": proxy_response.status_code,
                        "data": error_body,
                        "headers": dict(proxy_response.headers),
                    },
                    indent=2,
                )

            proxy_data = proxy_response.json()

            return json.dumps(
                {
                    "success": True,
                    "message": "Request completed successfully (payment handled automatically if required)",
                    "url": args.get("url", "error"),
                    "method": args.get("method", "GET"),
                    "status": proxy_data.get("status_code", proxy_response.status_code),
                    "data": proxy_data.get("data", proxy_data),
                    "paymentProof": proxy_data.get("paymentProof"),
                },
                indent=2,
            )

        except Exception as error:
            print("Error making safe request:", str(error))
            return self._handle_http_error(error, args.get("url", "error"))

    def _handle_http_error(self, error: Exception, url: str) -> str:
        """Handle HTTP errors consistently.

        Args:
            error: The error that occurred.
            url: The URL that was being accessed.

        Returns:
            str: JSON string containing formatted error details.

        """
        if hasattr(error, "response") and error.response is not None:
            error_details = getattr(
                error.response, "json", lambda: {"error": str(error)}
            )()
            return json.dumps(
                {
                    "success": False,
                    "status": getattr(error.response, "status_code", 500),
                    "data": error_details,
                    "url": url,
                },
                indent=2,
            )

        if hasattr(error, "request") and error.request is not None:
            return json.dumps(
                {
                    "success": False,
                    "status": 500,
                    "data": {
                        "error": str(error),
                        "type": "network_error",
                    },
                    "url": url,
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": False,
                "status": 500,
                "data": {
                    "error": str(error),
                    "type": "unknown_error",
                },
                "url": url,
            },
            indent=2,
        )

    def supports_network(self, network: Network) -> bool:
        """Check if the network is supported by this action provider.

        Args:
            network: The network to check support for.

        Returns:
            bool: Whether the network is supported.

        """
        return (
            network.protocol_family == "evm"
            and network.network_id in SUPPORTED_NETWORKS
        )


def barrierx_action_provider() -> BarrierXActionProvider:
    """Create a new x402 action provider.

    Returns:
        BarrierXActionProvider: A new BarrierX action provider instance.

    """
    return BarrierXActionProvider()
