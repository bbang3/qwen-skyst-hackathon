from io import BytesIO
import json
import functools
import requests
import urllib.request
import urllib3
import http.client
import httpx
import aiohttp
from .utils import patch
from .context import (
    wallet_provider, barrierx_provider, 
    disable_intercept, enable_intercept, is_intercept_disabled
)


backups = {}


def send_to_barrierx(source, method, url, headers=None, body=None, extra=None):
    try:
        disable_intercept()
        payload = {
            "source": source,
            "method": method,
            "url": url,
            "headers": headers or {},
            "data": body,
            "raw": None,
            "extra": extra or {},
        }
        r= barrierx_provider.make_safe_web_request_with_x402(wallet_provider, payload)
    finally:
        enable_intercept()
        
    return r


def barrierx_patch_all():
    patch(backups, requests.sessions.Session, "request", intercept_requests)
    patch(backups, urllib.request, "urlopen", intercept_urllib)
    patch(backups, urllib3.PoolManager, "request", intercept_urllib3_http)
    patch(backups, http.client.HTTPConnection, "request", intercept_httpclient_request)
    patch(backups, http.client.HTTPSConnection, "request", intercept_httpclient_request)
    patch(backups, http.client.HTTPConnection, "getresponse", intercept_httpclient_getresponse)
    patch(backups, http.client.HTTPSConnection, "getresponse", intercept_httpclient_getresponse)
    patch(backups, httpx.Client, "request", intercept_httpx)
    patch(backups, httpx.AsyncClient, "request", intercept_httpx_async)
    patch(backups, aiohttp.ClientSession, "_request", intercept_aiohttp_request)
    

def barrierx_unpatch_all():
    for (target, attr), original in backups.items():
        setattr(target, attr, original)
        

def intercept_requests(self, method, url, **kwargs):
    if is_intercept_disabled():
        return backups[(requests.sessions.Session, "request")](self, method, url, **kwargs)

    body = kwargs.get("data") or kwargs.get("json")
    headers = kwargs.get("headers")

    resp = json.loads(send_to_barrierx("requests", method, url, headers=headers, body=body, extra=kwargs))

    r = requests.Response()
    r.status_code = resp["status"]
    r._content = resp["data"].encode() if isinstance(resp["data"], str) else resp["data"]
    r.headers = resp.get("headers", {})
    r.url = url
    return r


def intercept_urllib(req, *args, **kwargs):
    if is_intercept_disabled():
        return backups[(urllib.request, "urlopen")](req, *args, **kwargs)
    
    url = getattr(req, "full_url", req)
    headers = dict(req.header_items()) if hasattr(req, "header_items") else {}
    body = getattr(req, "data", None)

    resp = json.loads(send_to_barrierx(
        "urllib.request",
        req.get_method() if hasattr(req, "get_method") else "?",
        url,
        headers=headers,
        body=body,
    ))

    return BytesIO(
        resp["data"].encode() if isinstance(resp["data"], str) else resp["data"]
    )
    
    
def intercept_urllib3_http(self, method, url, **kwargs):
    if is_intercept_disabled():
        return backups[(urllib3.PoolManager, "request")](self, method, url, **kwargs)

    body = kwargs.get("data")
    headers = kwargs.get("headers")

    resp = json.loads(send_to_barrierx("urllib3", method, url, headers=headers, body=body, extra=kwargs))

    fake_resp = urllib3.response.HTTPResponse(
        body=BytesIO(
            resp["data"].encode() if isinstance(resp["data"], str) else resp["data"]
        ),
        status=resp["status"],
        headers=resp.get("headers"),
        preload_content=False,
    )
    return fake_resp


def intercept_httpclient_request(self, method, url, body=None, headers=None):
    if is_intercept_disabled():
        return backups[(http.client.HTTPConnection, "request")](self, method, url, body=body, headers=headers)
    
    resp = send_to_barrierx(
        "http.client", method, url, headers=headers, body=body
    )
    self._last_barrierx_response = json.loads(resp)
    return None


def intercept_httpclient_getresponse(self):
    if is_intercept_disabled():
        return backups[(http.client.HTTPConnection, "getresponse")](self)
    
    resp = self._last_barrierx_response
    message = http.client.HTTPMessage()
    for k, v in resp["headers"].items():
        message.add_header(k, v)

    fake = http.client.HTTPResponse(self.sock)
    fake.code = resp["status"]
    fake.status = resp["status"]
    fake.msg = message
    fake.reason = ""
    fake.chunked = False
    body_bytes = (
        resp["data"].encode() if isinstance(resp["data"], str) else resp["data"]
    )
    fake.fp = BytesIO(body_bytes)
    fake.length = len(body_bytes)
    return fake


def intercept_httpx(self, method, url, **kwargs):
    if is_intercept_disabled():
        return backups[(httpx.Client, "request")](self, method, url, **kwargs)
    
    headers = kwargs.get("headers")
    body = kwargs.get("content") or kwargs.get("data") or kwargs.get("json")
    resp = json.loads(send_to_barrierx("httpx", method, url, headers=headers, body=body, extra=kwargs))

    return httpx.Response(
        status_code=resp["status"],
        content=json.dumps(resp["data"]),
        headers=resp.get("headers"),
        request=httpx.Request(method, url),
    )
    
    
async def intercept_httpx_async(self, method, url, **kwargs):
    if is_intercept_disabled():
        return await backups[(httpx.AsyncClient, "request")](self, method, url, **kwargs)
    
    headers = kwargs.get("headers")
    body = kwargs.get("content") or kwargs.get("data") or kwargs.get("json")

    resp = json.loads(send_to_barrierx("httpx.AsyncClient", method, url, headers=headers, body=body, extra=kwargs))

    return httpx.Response(
        status_code=resp["status"],
        content=json.dumps(resp["data"]),
        headers=resp.get("headers"),
        request=httpx.Request(method, url),
    )
    
    
class FakeAiohttpResponse:
    def __init__(self, barrier_resp, url):
        self.status = barrier_resp["status"]
        self.headers = barrier_resp.get("headers", {})
        self._body = (
            barrier_resp["data"].encode()
            if isinstance(barrier_resp["data"], str)
            else barrier_resp["data"]
        )
        self.reason = ""
        self.url = url

        # aiohttp에서 content-stream처럼 사용되는 인터페이스
        self.content = BytesIO(self._body)

    async def read(self):
        return self._body

    async def text(self, encoding="utf-8"):
        return self._body.decode(encoding)

    async def json(self):
        return json.loads(self._body)

    async def release(self):
        """
        aiohttp의 release()는 커넥션을 반환하는 용도인데,
        여기서는 아무 작업도 필요 없음.
        """
        return None
    

async def intercept_aiohttp_request(self, method, url, **kwargs):
    if is_intercept_disabled():
        return await backups[(aiohttp.ClientSession, "_request")](self, method, url, **kwargs)
    
    headers = kwargs.get("headers")
    body = kwargs.get("data") or kwargs.get("json")

    resp = json.loads(send_to_barrierx(
        "aiohttp", method, url, headers=headers, body=body, extra=kwargs
    ))

    return FakeAiohttpResponse(resp, url)