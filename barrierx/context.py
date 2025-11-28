import threading
from coinbase_agentkit import (
    CdpEvmWalletProvider,
    CdpEvmWalletProviderConfig,
)    

from .constants import (
    BARRIERX_PROXY_URL,
    CDP_API_KEY_ID,
    CDP_API_KEY_SECRET,
    CDP_WALLET_SECRET,
    NETWORK_ID,
    BUYER_WALLET_ADDRESS,
    IDEMPOTENCY_KEY,
)
from .wallet_utils import (
    BarrierXActionProvider
)


wallet_provider = CdpEvmWalletProvider(
    CdpEvmWalletProviderConfig(
        api_key_id=CDP_API_KEY_ID,
        api_key_secret=CDP_API_KEY_SECRET,
        wallet_secret=CDP_WALLET_SECRET,
        network_id=NETWORK_ID,
        address=BUYER_WALLET_ADDRESS,
        idempotency_key=IDEMPOTENCY_KEY
    )
)
barrierx_provider = BarrierXActionProvider()

_local = threading.local()
_local.disable_intercept = False

def is_intercept_disabled():
    return getattr(_local, "disable_intercept", False)

def disable_intercept():
    _local.disable_intercept = True

def enable_intercept():
    _local.disable_intercept = False