"""Pydantic schemas and input validators for automated posting."""

import re
from typing import List, Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


# Regular expression to extract URL-like substrings from text
URL_CANDIDATE_REGEX = re.compile(
    r"(?:https?://|www\.)[^\s<>'\"`]+",
    re.IGNORECASE,
)

# Reject schemes that are not supported CTA protocols (e.g., ftp://, mailto:, file://)
UNSUPPORTED_SCHEME_REGEX = re.compile(
    r"\b(?:ftp|mailto|file|javascript|ssh|telnet)://[^\s]+",
    re.IGNORECASE,
)

# Domain name regex to validate hostnames:
# 1. Standard domains (e.g. example.com, sub.domain.org)
# 2. Localhost
# 3. Valid IPv4 addresses (e.g. 127.0.0.1, 192.168.1.1)
# 4. Optional port numbers (:80, :4000)
DOMAIN_REGEX = re.compile(
    r"^(?:"
    r"localhost|"
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}"
    r")(?::\d+)?$"
)


def clean_url_punctuation(raw_url: str) -> str:
    """Trim surrounding punctuation marks commonly attached in conversational sentences,

    while preserving balanced parenthesis (e.g., Wikipedia URLs).
    """
    url = raw_url.rstrip(".,;:!?'\">`")
    # If trailing bracket/parenthesis, only strip if it is unmatched
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    while url.endswith("]") and url.count("]") > url.count("["):
        url = url[:-1]
    while url.endswith("}") and url.count("}") > url.count("{"):
        url = url[:-1]
    return url.rstrip(".,;:!?'\">`")


def is_valid_url(url: str) -> bool:
    """Validate that the string is a well-formed HTTP/HTTPS URL with a valid host."""
    try:
        test_url = url
        if test_url.lower().startswith("www."):
            test_url = "https://" + test_url

        parsed = urlparse(test_url)
        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.netloc:
            return False

        # Validate host portion (strip port or basic auth for domain matching)
        host = parsed.netloc.split("@")[-1]
        if not DOMAIN_REGEX.match(host):
            return False

        return True
    except Exception:
        return False


class PostingRequest(BaseModel):
    """Incoming request payload for posting across platforms."""

    message: str = Field(
        ...,
        description="The content to publish. Must be 1-200 chars and contain exactly one valid CTA URL.",
        examples=[
            "Check out our latest business platform and grow your online visibility. https://example.com"
        ],
    )

    @field_validator("message")
    @classmethod
    def validate_message_and_cta(cls, value: str) -> str:
        """Enforce character limit and exactly one valid CTA URL constraint."""
        if not value or not value.strip():
            raise ValueError("Message cannot be empty or contain only whitespace.")

        trimmed = value.strip()
        if len(trimmed) > 200:
            raise ValueError(
                f"Message length ({len(trimmed)}) exceeds the maximum allowed limit of 200 characters."
            )

        # Check for unsupported schemes
        unsupported = UNSUPPORTED_SCHEME_REGEX.findall(trimmed)
        if unsupported:
            raise ValueError(
                f"Unsupported URL scheme detected: '{unsupported[0]}'. Only HTTP and HTTPS URLs are allowed."
            )

        # Detect potential URLs
        raw_matches = URL_CANDIDATE_REGEX.findall(trimmed)
        cleaned_urls = [clean_url_punctuation(u) for u in raw_matches]

        # Check for malformed scheme attempts like 'http://', 'https://'
        malformed_attempts = re.findall(r"\bhttps?://[^\s]*", trimmed, re.IGNORECASE)
        for attempt in malformed_attempts:
            cleaned = clean_url_punctuation(attempt)
            if not is_valid_url(cleaned):
                raise ValueError(
                    f"Malformed or invalid URL detected in message: '{cleaned}'."
                )

        if not cleaned_urls:
            raise ValueError("Message must contain exactly one CTA link, but none was found.")

        if len(cleaned_urls) > 1:
            raise ValueError(
                f"Message must contain exactly one CTA link, but found {len(cleaned_urls)}: "
                + ", ".join(cleaned_urls)
            )

        single_url = cleaned_urls[0]
        if not is_valid_url(single_url):
            raise ValueError(f"The CTA URL '{single_url}' is malformed or invalid.")

        return trimmed


class PlatformResult(BaseModel):
    """Result of publishing to an individual platform."""

    platform: str
    status: Literal["success", "failed"]
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    """Consolidated response returned by the multi-platform posting API."""

    success: bool
    results: List[PlatformResult]
