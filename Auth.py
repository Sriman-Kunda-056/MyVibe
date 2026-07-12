"""Google OAuth helpers for VibeOS adapters."""

from __future__ import annotations

import os
from typing import Any, Optional, Sequence


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]
TASKS_SCOPES = ["https://www.googleapis.com/auth/tasks"]

CREDS_PATH = os.getenv("GOOGLE_OAUTH_CREDENTIALS_PATH", "./credentials.json")
TOKEN_PATH = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "token.json")
GMAIL_TOKEN_PATH = os.getenv("GOOGLE_GMAIL_TOKEN_PATH", "gmail_token.json")
TASKS_TOKEN_PATH = os.getenv("GOOGLE_TASKS_TOKEN_PATH", "tasks_token.json")


def get_google_credentials(
    scopes: Sequence[str],
    token_path: str,
    creds_path: Optional[str] = None,
) -> Any:
    """Load or create OAuth credentials for the requested Google scopes."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials_path = creds_path or CREDS_PATH
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                scopes,
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def get_calendar_credentials() -> Any:
    return get_google_credentials(CALENDAR_SCOPES, TOKEN_PATH)


def get_gmail_credentials() -> Any:
    return get_google_credentials(GMAIL_SCOPES, GMAIL_TOKEN_PATH)


def get_tasks_credentials() -> Any:
    return get_google_credentials(TASKS_SCOPES, TASKS_TOKEN_PATH)