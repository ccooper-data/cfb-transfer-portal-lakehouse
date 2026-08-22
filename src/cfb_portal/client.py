from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping


BASE_URL = "https://api.collegefootballdata.com"


@dataclass(frozen=True)
class ApiResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class CFBDClient:
    """Small raw HTTP client used so exact source bytes can be archived.

    The official `cfbd` package remains useful for exploration, but ingestion captures
    raw response bytes before any model coercion so provenance is reproducible.
    """

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL) -> None:
        self.api_key = api_key or os.environ.get("CFBD_API_KEY") or os.environ.get("BEARER_TOKEN")
        if not self.api_key:
            raise RuntimeError("Set CFBD_API_KEY (or BEARER_TOKEN) before ingestion")
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, params: Mapping[str, object] | None = None, timeout: int = 120) -> ApiResponse:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": "cfb-transfer-portal-lakehouse/0.1",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            headers = {k: v for k, v in response.headers.items()}
            status = int(response.status)
        return ApiResponse(url=url, status=status, headers=headers, body=body)
