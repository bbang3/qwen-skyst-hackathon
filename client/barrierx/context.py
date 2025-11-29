import os
import threading
from contextvars import ContextVar

from coinbase_agentkit import (
    CdpEvmWalletProvider,
    CdpEvmWalletProviderConfig,
)
from dotenv import load_dotenv

from .wallet_utils import BarrierXActionProvider

load_dotenv()

wallet_provider = CdpEvmWalletProvider(
    CdpEvmWalletProviderConfig(
        api_key_id=os.getenv("CDP_API_KEY_ID"),
        api_key_secret=os.getenv("CDP_API_KEY_SECRET"),
        wallet_secret=os.getenv("CDP_WALLET_SECRET"),
        network_id=os.getenv("NETWORK_ID"),
        address=os.getenv("BUYER_WALLET_ADDRESS"),
        idempotency_key=os.getenv("IDEMPOTENCY_KEY"),
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
