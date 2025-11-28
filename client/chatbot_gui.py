"""Enterprise Chat - Demo application for safe HTTP request firewall.

This GUI application demonstrates how enterprise agents can safely interact
with external APIs through our firewall proxy that protects against:
- Data leakage (PII, credentials, sensitive information)
- Prompt injection attacks
- Unauthorized data exfiltration
"""

import asyncio
import sys
from pathlib import Path

import streamlit as st
from agents.items import ItemHelpers
from agents.run import Runner
from dotenv import load_dotenv
from setup import setup

# Add parent directory to path to import chatbot module
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from client.debug_utils import print_debug_info

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Enterprise Chat",
    page_icon="🛡️",
    layout="wide",
)

# Initialize session state
if "agent" not in st.session_state:
    with st.spinner("Initializing agent..."):
        try:
            st.session_state.agent = setup()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.session_state.initialized = False
            st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = None

if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False


def display_chat_message(role: str, content: str):
    """Display a chat message in the chat interface.

    Args:
        role: The role of the message sender ('user' or 'assistant').
        content: The message content.
    """
    with st.chat_message(role):
        st.markdown(content)


# Display chat history
for message in st.session_state.messages:
    display_chat_message(message["role"], message["content"])

# Row above: small "Attach file" trigger on the right
uploaded_file = None
_, attach_col = st.columns([10, 2])
with attach_col:
    with st.popover("Attach file"):
        uploaded_file = st.file_uploader(
            "Attach file",
            type=["json", "txt", "md", "csv"],
            label_visibility="collapsed",
        )

# Sticky chat input always rendered at the very bottom
prompt = st.chat_input("Type your message here...")

if prompt:
    # Read attached file content (if any) as text
    attached_text = None
    attached_filename = None
    if uploaded_file is not None:
        try:
            # Read the file as UTF-8 text
            file_bytes = uploaded_file.read()
            attached_text = file_bytes.decode("utf-8")
            attached_filename = uploaded_file.name
        except Exception:
            # If decoding fails, ignore the file for safety
            attached_text = None
            attached_filename = None

    # Build the prompt that will actually be sent to the agent
    if attached_text:
        prompt_for_agent = (
            f"{prompt}\n\n" f"[Attached file: {attached_filename}]\n" f"{attached_text}"
        )
    else:
        prompt_for_agent = prompt

    # Add user message to chat (without raw file content)
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_chat_message("user", prompt)

    # Prepare input with conversation history
    if st.session_state.conversation_history is None:
        input_data = prompt_for_agent
    else:
        new_user_message = ItemHelpers.input_to_new_input_list(prompt_for_agent)[0]
        input_data = st.session_state.conversation_history + [new_user_message]

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Running..."):
            try:
                # Run agent asynchronously
                output = asyncio.run(Runner.run(st.session_state.agent, input_data))

                response = output.final_output

                # Display response
                st.markdown(response)

                # Print debugging information to terminal if debug mode is enabled
                if st.session_state.debug_mode:
                    print_debug_info(output)

                # Add assistant message to chat
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

                # Update conversation history
                st.session_state.conversation_history = output.to_input_list()

            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )

# Sidebar with controls
with st.sidebar:
    st.title("🛡️ Enterprise Chat")

    # Debug mode toggle
    st.session_state.debug_mode = st.checkbox(
        "🔍 Debug Mode",
        value=st.session_state.debug_mode,
        help="Show tool calls and responses for debugging",
    )

    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = None
        st.rerun()

    st.markdown("### About")
    st.markdown(
        "**Enterprise Chat** is a demo application showcasing our secure HTTP request firewall. "
        "All agent interactions with external APIs are automatically protected by our firewall proxy, "
        "which prevents data leakage and prompt injection attacks."
    )
    st.markdown("---")
    st.markdown("### Security Features")
    st.markdown(
        """
        - 🔒 **Data Leakage Protection**: Detects and blocks PII, credentials, and sensitive data
        - 🛡️ **Prompt Injection Defense**: Prevents malicious prompt injection attempts
        - ✅ **Safe HTTP Requests**: All external requests go through secure proxy
        - 💳 **x402 Payment Support**: Handles payment-required endpoints securely
        """
    )
