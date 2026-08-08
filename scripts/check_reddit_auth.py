#!/usr/bin/env python3
"""Verify Reddit OAuth credentials before starting a long collection run.

Gets a token, makes one real search request, and reports the rate limit Reddit
hands back so a full run can be paced against a measured number rather than a
guess.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from reddit_client import RedditClient, add_credential_arguments


DEFAULT_USER_AGENT = (
    "reddit-foundthepost-content-analysis/0.1 "
    "(credential preflight; contact: local research script)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    add_credential_arguments(parser)
    parser.add_argument(
        "--query",
        default="found my post",
        help="Phrase used for the single live test search.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = RedditClient(
        user_agent=args.user_agent,
        client_id=args.client_id,
        client_secret=args.client_secret,
    )

    print(f"auth mode: {client.auth_mode}")
    if not client.uses_oauth:
        print(
            "\nNo credentials found. Set both environment variables:\n"
            "  export REDDIT_CLIENT_ID=...\n"
            "  export REDDIT_CLIENT_SECRET=...\n"
            "Create a 'script' app at https://www.reddit.com/prefs/apps",
            file=sys.stderr,
        )
        return 2

    print(f"client id:  {args.client_id[:4]}...{args.client_id[-2:]}")

    try:
        token = client.oauth_token()
    except RuntimeError as error:
        print(f"\nToken request FAILED: {error}", file=sys.stderr)
        return 1
    print(f"token:      acquired, {len(token)} chars")

    params = {
        "q": f'"{args.query}"',
        "sort": "relevance",
        "t": "all",
        "limit": "5",
        "raw_json": "1",
        "type": "link",
    }
    url = client.api_url("/search", params)

    started = time.monotonic()
    request = Request(url, headers=client.headers())
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = dict(response.headers)
    except HTTPError as error:
        print(f"\nTest search FAILED: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started

    children = payload.get("data", {}).get("children", [])
    print(f"test search: {len(children)} results in {elapsed:.2f}s")
    if children:
        first = children[0].get("data", {})
        print(f"  sample:   r/{first.get('subreddit', '')} - {first.get('title', '')[:70]}")

    remaining = headers.get("x-ratelimit-remaining")
    used = headers.get("x-ratelimit-used")
    reset = headers.get("x-ratelimit-reset")
    if remaining is not None:
        print(f"rate limit: {remaining} remaining, {used} used, resets in {reset}s")
        try:
            per_minute = float(remaining) + float(used or 0)
            print(f"  budget:   about {per_minute:.0f} requests per 10-minute window")
        except (TypeError, ValueError):
            pass
    else:
        print("rate limit: no x-ratelimit headers returned")

    print("\nCredentials work. Collection scripts are ready to run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
