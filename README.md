# BarrierX - Secure HTTP Request Firewall for AI Agents

BarrierX is a security proxy server that protects AI agents from data leakage and prompt injection attacks when making HTTP requests. It acts as a firewall between your agent and external APIs, validating both incoming requests and outgoing responses.

## Project Overview

### What BarrierX Does

BarrierX provides a secure proxy layer that:
- **Prevents Data Leakage**: Detects and blocks sensitive information (PII, credentials, API keys) from being sent in HTTP requests
- **Blocks Prompt Injection**: Uses LLM-based classification to detect and prevent prompt injection attempts in both requests and responses
- **Enables x402 Payments**: Integrates with x402 protocol for payment-protected endpoints

### Demo Components

The project includes three main components:

1. **`barrierx_server/`** - The security proxy server
   - FastAPI server that intercepts HTTP requests
   - Performs security checks before forwarding requests
   - Validates responses for prompt injection
   - Protected by x402 payment middleware

2. **`client/`** - AI agent client with Streamlit GUI
   - Enterprise Chat interface demonstrating safe HTTP requests
   - Uses BarrierX proxy for all external API calls
   - Shows how agents can safely interact with external services

3. **`phishing_server/`** - Mock phishing server for testing
   - Demonstrates prompt injection attack vectors
   - Used to test BarrierX's detection capabilities
   - Shows hidden prompt injection attempts in web responses

## How to Use

### Prerequisites

- Python 3.10+
- `uv` package manager (recommended)

### 1. Install Dependencies

Using `uv`:
```bash
uv sync
```

### 2. Install Spacy Model (for Presidio)

```bash
uv pip install --python .venv/bin/python en-core-web-lg
```

### 3. Set Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI API Key (required for prompt injection detection)
OPENAI_API_KEY=your_openai_api_key

# CDP Wallet Configuration (for client)
CDP_API_KEY_ID=your_cdp_api_key_id
CDP_API_KEY_SECRET=your_cdp_api_key_secret
CDP_WALLET_SECRET=your_cdp_wallet_secret
NETWORK_ID=base-sepolia
BUYER_WALLET_ADDRESS=your_wallet_address

# BarrierX Server Configuration
SELLER_WALLET_ADDRESS=your_seller_wallet_address
```

### 4. Run the Servers

**BarrierX Proxy Server:**
```bash
cd barrierx_server
uv run python main.py
```
Server runs on `http://0.0.0.0:4021`

**Phishing Server (optional, for testing):**
```bash
cd phishing_server
uv run python main.py
```
Server runs on `http://0.0.0.0:8080`

**Client GUI:**
```bash
cd client
uv run streamlit run chatbot_gui.py
```
GUI opens at `http://localhost:8501`

### 5. Test the System

1. Open the Enterprise Chat GUI in your browser
2. Try making a request to the phishing server: `http://localhost:8080/weather`
3. BarrierX will detect and block the prompt injection attempt
4. Try making a safe request to a legitimate API

## Security Features

- **Data Leakage Detection**: Uses Presidio Analyzer and regex patterns to detect sensitive information

- **Prompt Injection Detection**: Uses LLM to classify prompt injection attempts.

## Architecture

```
AI Agent (Client)
    ↓
BarrierX Proxy Server (/check)
    ↓ (security checks)
External API
    ↓ (response validation)
AI Agent (Client)
```

All HTTP requests from the agent go through BarrierX, which validates both the request and response before returning to the agent.

