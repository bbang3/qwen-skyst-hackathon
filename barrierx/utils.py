import functools
import json
from io import BytesIO

import requests
import urllib.request
import urllib3
import http.client
import httpx
import aiohttp

from .constants import (
    BARRIERX_PROXY_URL,
    CDP_API_KEY_ID,
    CDP_API_KEY_SECRET,
    CDP_WALLET_SECRET,
    NETWORK_ID,
    BUYER_WALLET_ADDRESS,
    IDEMPOTENCY_KEY,
)

from .wallet_utils import BarrierXActionProvider, barrierx_action_provider


import asyncio
import json
import os
import sys
import time
    

def patch(backups, target, attr, new_value):
    key = (target, attr)
    if key not in backups:
        backups[key] = getattr(target, attr)
    setattr(target, attr, new_value)