"""Small server-side UI client; no database or metric calculations in the UI."""

from urllib.parse import urlsplit

import httpx


class ApiClientError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url):
        url = urlsplit(base_url)
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise ValueError("Use a loopback API URL.")
        self.base_url = base_url.rstrip("/")

    def request(self, path, params=None, body=None):
        if path not in {"/health", "/metrics/summary", "/forecast", "/assistant/query"}:
            raise ValueError("Unsupported API route")
        try:
            with httpx.Client(
                timeout=httpx.Timeout(65, connect=3),
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = (
                    client.post(self.base_url + path, json=body)
                    if body is not None
                    else client.get(self.base_url + path, params=params)
                )
                data = response.json()
                if response.status_code != 200:
                    # Backend messages are sanitized; never expose transport exceptions/URLs.
                    raise ApiClientError(
                        data.get("error", {}).get(
                            "message", "The API could not complete this request."
                        )
                    )
                return data
        except (httpx.HTTPError, ValueError) as exc:
            raise ApiClientError(
                "The local API is unavailable or timed out. Start the demo and retry."
            ) from exc
