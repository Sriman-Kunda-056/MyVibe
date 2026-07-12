"""Gmail adapter for VibeOS."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from email.message import EmailMessage as MimeEmailMessage
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class GmailMessage:
    """Normalized Gmail message metadata."""

    message_id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    labels: List[str]

    @classmethod
    def from_google_message(cls, message: Dict[str, Any]) -> "GmailMessage":
        headers = message.get("payload", {}).get("headers", [])
        return cls(
            message_id=message.get("id", ""),
            thread_id=message.get("threadId", ""),
            subject=_header(headers, "Subject") or "(no subject)",
            sender=_header(headers, "From") or "",
            snippet=message.get("snippet", ""),
            labels=list(message.get("labelIds", [])),
        )


class GmailAdapter:
    """Thin adapter around Gmail messages."""

    def __init__(self, user_id: str = "me", service: Any = None) -> None:
        self.user_id = user_id
        self._service = service

    @property
    def service(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            from Auth import get_gmail_credentials

            self._service = build("gmail", "v1", credentials=get_gmail_credentials())
        return self._service

    def list_recent_messages(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
    ) -> List[GmailMessage]:
        response = (
            self.service.users()
            .messages()
            .list(userId=self.user_id, maxResults=max_results, q=query)
            .execute()
        )
        messages = response.get("messages", [])
        return [self.get_message(message["id"]) for message in messages]

    def get_message(self, message_id: str) -> GmailMessage:
        message = (
            self.service.users()
            .messages()
            .get(
                userId=self.user_id,
                id=message_id,
                format="metadata",
                metadataHeaders=["Subject", "From"],
            )
            .execute()
        )
        return GmailMessage.from_google_message(message)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> str:
        message = MimeEmailMessage()
        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc
        message.set_content(body)

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        sent = (
            self.service.users()
            .messages()
            .send(userId=self.user_id, body={"raw": encoded})
            .execute()
        )
        return sent.get("id", "")


def _header(headers: Iterable[Dict[str, str]], name: str) -> Optional[str]:
    expected = name.lower()
    for header in headers:
        if header.get("name", "").lower() == expected:
            return header.get("value")
    return None
