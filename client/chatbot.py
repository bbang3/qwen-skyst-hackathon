import asyncio
import json
import os
import sys
import time

from agents.agent import Agent
from agents.items import ItemHelpers
from agents.run import Runner
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
from dotenv import load_dotenv


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
                barrierx_action_provider(),
            ],
        )
    )

    # Get tools for the agent
    tools = get_openai_agents_sdk_tools(agentkit)

    # Custom tools
    # tools.append(get_today_fortune)
    # tools.append(search_web)

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


# Chat Mode
async def run_chat_mode(agent):
    """Run the agent interactively based on user input."""
    print("Starting chat mode... Type 'exit' to end.")
    conversation_history = None

    while True:
        try:
            user_input = input("\nPrompt: ")
            if user_input.lower() == "exit":
                break

            # Prepare input: append new user message to conversation history
            if conversation_history is None:
                input_data = user_input
            else:
                new_user_message = ItemHelpers.input_to_new_input_list(user_input)[0]
                input_data = conversation_history + [new_user_message]

            # Run agent with conversation history in input
            output = await Runner.run(agent, input_data)
            print(output.final_output)
            print("-------------------")

            # Update conversation history for next turn
            conversation_history = output.to_input_list()

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


# Mode Selection
def choose_mode():
    """Choose whether to run in autonomous or chat mode based on user input."""
    while True:
        print("\nAvailable modes:")
        print("1. chat    - Interactive chat mode")
        print("2. auto    - Autonomous action mode")

        choice = input("\nChoose a mode (enter number or name): ").lower().strip()
        if choice in ["1", "chat"]:
            return "chat"
        elif choice in ["2", "auto"]:
            return "auto"
        print("Invalid choice. Please try again.")


async def main():
    """Start the chatbot agent."""
    # Load environment variables
    load_dotenv()

    # Set up the agent
    agent = setup()

    await run_chat_mode(agent=agent)


if __name__ == "__main__":
    print("Starting Agent...")
    asyncio.run(main())
