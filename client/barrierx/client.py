import dotenv

dotenv.load_dotenv()
import functools
import requests

from .intercept import (
    barrierx_patch_all,
    barrierx_unpatch_all,
)
import asyncio


def barrierx(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        barrierx_patch_all()
        try:
            return func(*args, **kwargs)
        finally:
            barrierx_unpatch_all()

    return wrapper


if __name__ == "__main__":

    @barrierx
    def run():
        import requests

        url = "https://api.duckduckgo.com/"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BarrierX-Demo/1.0",
        }

        body = {
            "q": "python decorator example",
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        r = requests.post(url, headers=headers, json=body)

        print("Status:", r.status_code)
        print("Response:", r.text[:500])

        # print("Sending via httpx")
        # r2 = httpx.get("https://httpbin.org/get")
        # print("Returned:", r2.status_code, r2.text[:50])

    run()
