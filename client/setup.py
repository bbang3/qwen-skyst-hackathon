import os
from agents.agent import Agent

from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    CdpEvmWalletProvider,
    CdpEvmWalletProviderConfig,
    cdp_api_action_provider,
    wallet_action_provider,
)
from coinbase_agentkit_openai_agents_sdk import get_openai_agents_sdk_tools
from barrierx_action_provider import barrierx_action_provider
from tools import web_tool


def initialize_agent(config: CdpEvmWalletProviderConfig):
    """Initialize the agent with CDP Agentkit.

    Args:
        config: Configuration for the CDP EVM Server Wallet Provider

    Returns:
        tuple[Agent, CdpEvmWalletProvider]: The initialized agent and wallet provider

    """
    # Initialize the wallet provider with the config
    wallet_provider = CdpEvmWalletProvider(
        CdpEvmWalletProviderConfig(
            api_key_id=config.api_key_id,  # CDP API Key ID
            api_key_secret=config.api_key_secret,  # CDP API Key Secret
            wallet_secret=config.wallet_secret,  # CDP Wallet Secret
            network_id=config.network_id,  # Network ID - Optional, will default to 'base-sepolia'
            address=config.address,  # Wallet Address - Optional, will trigger idempotency flow if not provided
            idempotency_key=config.idempotency_key,  # Idempotency Key - Optional, seeds generation of a new wallet
        )
    )

    # Create AgentKit instance with wallet and action providers
    agentkit = AgentKit(
        AgentKitConfig(
            wallet_provider=wallet_provider,
            action_providers=[
                cdp_api_action_provider(),
                wallet_action_provider(),
            ],
        )
    )

    # Get tools for the agent
    tools = get_openai_agents_sdk_tools(agentkit)

    # Custom tools
    tools.append(web_tool)

    # Create Agent using the OpenAI Agents SDK
    agent = Agent(
        name="CDP Agent",
        instructions=(
            "You are a helpful agent that can interact onchain using your tools. "
            "IMPORTANT: Any tool you use may return a 402 Payment Required response. "
            "If you receive a 402 response (whether from HTTP requests or other tools), "
            "you must use retry_http_request_with_x402 to retry the request with payment. "
            "The workflow is: "
            "1. Make your initial request using the appropriate tool (e.g., make_http_request for HTTP endpoints, or other tools as needed). "
            "2. If you receive a 402 response with payment requirements, extract the payment details "
            "(network, scheme, max_amount_required, pay_to, asset) from the response. "
            "3. Use retry_http_request_with_x402 with the original request URL/method/body and the payment details to retry with payment. "
            "4. Do not skip the payment step if a 402 is received - always retry with payment using retry_http_request_with_x402."
        ),
        model="gpt-4.1-mini",
        tools=tools,
    )

    return agent, wallet_provider


def setup():
    """Set up the agent with persistent wallet storage.

    Returns:
        Agent: The initialized agent

    """
    # Configure network and file path
    network_id = os.getenv("NETWORK_ID", "base-sepolia")
    wallet_address = os.getenv("BUYER_WALLET_ADDRESS")

    # Create the wallet provider config
    config = CdpEvmWalletProviderConfig(
        api_key_id=os.getenv("CDP_API_KEY_ID"),
        api_key_secret=os.getenv("CDP_API_KEY_SECRET"),
        wallet_secret=os.getenv("CDP_WALLET_SECRET"),
        network_id=network_id,
        address=wallet_address,
    )

    # Initialize the agent and get the wallet provider
    agent, wallet_provider = initialize_agent(config)

    return agent
