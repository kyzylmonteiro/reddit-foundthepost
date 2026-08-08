#!/usr/bin/env python3
"""Shared Reddit JSON client for the collection scripts.

Reddit answers HTTP 403 Blocked for unauthenticated requests to its public
``.json`` endpoints, so OAuth client credentials are effectively required.
Supplying a client id and secret switches every request to ``oauth.reddit.com``
with a bearer token that is refreshed as it expires.

Standard library only. The collection scripts import this by filename because
they all live in ``scripts/``.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REDDIT_BASE = "https://www.reddit.com"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"

BLOCKED_MESSAGE = (
    "Reddit returned HTTP 403 Blocked for an unauthenticated request. Reddit no "
    "longer serves the public .json endpoints to scripts; set REDDIT_CLIENT_ID "
    "and REDDIT_CLIENT_SECRET (or pass --client-id/--client-secret) to collect "
    "over OAuth. Create a 'script' app at https://www.reddit.com/prefs/apps"
)

NO_CREDENTIALS_WARNING = (
    "Warning: no Reddit OAuth credentials supplied. Reddit answers HTTP 403 "
    "Blocked for unauthenticated JSON requests, so this run will very likely "
    "fail. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
)


class RedditClient:
    """Reddit JSON client that prefers OAuth and falls back to public endpoints."""

    def __init__(
        self,
        user_agent: str,
        client_id: str = "",
        client_secret: str = "",
    ) -> None:
        self.user_agent = user_agent
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = ""
        self.token_expires_at = 0.0

    @property
    def uses_oauth(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def auth_mode(self) -> str:
        if self.uses_oauth:
            return "oauth_client_credentials"
        return "unauthenticated_www_json"

    def api_url(self, path: str, params: dict[str, str]) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        if self.uses_oauth:
            return f"{REDDIT_OAUTH_BASE}{clean_path}?{urlencode(params)}"
        return f"{REDDIT_BASE}{clean_path}.json?{urlencode(params)}"

    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        if self.uses_oauth:
            headers["Authorization"] = f"bearer {self.oauth_token()}"
        return headers

    def oauth_token(self) -> str:
        if self.access_token and time.monotonic() < self.token_expires_at:
            return self.access_token

        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic_auth = base64.b64encode(credentials).decode("ascii")
        body = urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = Request(
            f"{REDDIT_BASE}/api/v1/access_token",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"failed to authenticate with Reddit OAuth "
                f"(HTTP {error.code}): {detail}"
            ) from error

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Reddit OAuth response did not include access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        self.access_token = token
        self.token_expires_at = time.monotonic() + max(60, expires_in - 60)
        return self.access_token

    def request_json(self, url: str, retries: int = 6) -> Any:
        for attempt in range(retries + 1):
            request = Request(url, headers=self.headers())
            try:
                with urlopen(request, timeout=45) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                if self.uses_oauth and error.code == 401 and attempt < retries:
                    self.access_token = ""
                    self.token_expires_at = 0.0
                    continue
                if error.code == 403 and not self.uses_oauth:
                    raise RuntimeError(BLOCKED_MESSAGE) from error
                if error.code == 429 and attempt < retries:
                    retry_after = error.headers.get("Retry-After")
                    delay = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 60
                    )
                    time.sleep(delay)
                    continue
                if 500 <= error.code < 600 and attempt < retries:
                    time.sleep(2**attempt)
                    continue
                raise
            except (TimeoutError, URLError):
                if attempt < retries:
                    time.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError(f"failed to fetch {url}")


def add_credential_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the standard --client-id / --client-secret options to a parser.

    Both default to environment variables so credentials never have to appear in
    a command line, and so they are never written into a run manifest.
    """
    parser.add_argument(
        "--client-id",
        default=os.environ.get("REDDIT_CLIENT_ID", ""),
        help=(
            "Reddit OAuth client id. Defaults to the REDDIT_CLIENT_ID "
            "environment variable. Required now that Reddit answers 403 for "
            "unauthenticated JSON requests."
        ),
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        help="Reddit OAuth client secret. Defaults to REDDIT_CLIENT_SECRET.",
    )


def client_from_args(args: argparse.Namespace) -> RedditClient:
    return RedditClient(
        user_agent=args.user_agent,
        client_id=getattr(args, "client_id", ""),
        client_secret=getattr(args, "client_secret", ""),
    )
