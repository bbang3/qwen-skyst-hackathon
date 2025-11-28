import threading
from contextvars import ContextVar

from coinbase_agentkit import (
    CdpEvmWalletProvider,
    CdpEvmWalletProviderConfig,
)

from .constants import (
    BUYER_WALLET_ADDRESS,
    CDP_API_KEY_ID,
    CDP_API_KEY_SECRET,
    CDP_WALLET_SECRET,
    IDEMPOTENCY_KEY,
    NETWORK_ID,
)
from .wallet_utils import BarrierXActionProvider

wallet_provider = CdpEvmWalletProvider(
    CdpEvmWalletProviderConfig(
        api_key_id=CDP_API_KEY_ID,
        api_key_secret=CDP_API_KEY_SECRET,
        wallet_secret=CDP_WALLET_SECRET,
        network_id=NETWORK_ID,
        address=BUYER_WALLET_ADDRESS,
        idempotency_key=IDEMPOTENCY_KEY,
    )
)
barrierx_provider = BarrierXActionProvider()

_local = threading.local()
_local.disable_intercept = False

disable_intercept_var = ContextVar("disable_intercept", default=False)

def is_intercept_disabled():
    return disable_intercept_var.get()

def disable_intercept():
    return disable_intercept_var.set(True)

def enable_intercept(token):
    disable_intercept_var.reset(token)