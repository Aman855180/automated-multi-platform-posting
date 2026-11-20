"""Unit tests for Pydantic input validation."""

import pytest
from pydantic import ValidationError
from app.schemas import PostingRequest


def test_valid_message_with_single_url():
    """Ensure a valid message containing exactly one URL passes validation."""
    msg = "Check out our latest business platform and grow your online visibility. https://example.com"
    req = PostingRequest(message=msg)
    assert req.message == msg


def test_valid_message_with_trailing_punctuation():
    """Ensure URL followed by period, exclamation, or question mark parses cleanly."""
    msg = "Check out our product at https://example.com/demo! It is great."
    req = PostingRequest(message=msg)
    assert "https://example.com/demo" in req.message


def test_empty_message_rejected():
    """Ensure empty message raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        PostingRequest(message="")
    assert "Message cannot be empty" in str(exc_info.value)


def test_whitespace_only_message_rejected():
    """Ensure whitespace-only message raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        PostingRequest(message="    \n\t  ")
    assert "Message cannot be empty" in str(exc_info.value)


def test_message_exceeding_200_chars_rejected():
    """Ensure message longer than 200 characters is rejected."""
    long_msg = "A" * 185 + " https://example.com"
    assert len(long_msg) > 200
    with pytest.raises(ValidationError) as exc_info:
        PostingRequest(message=long_msg)
    assert "exceeds the maximum allowed limit of 200 characters" in str(exc_info.value)


def test_message_exactly_200_chars_accepted():
    """Ensure message of exactly 200 characters passes validation."""
    url = " https://example.com"
    prefix_len = 200 - len(url)
    msg = ("A" * prefix_len) + url
    assert len(msg) == 200
    req = PostingRequest(message=msg)
    assert len(req.message) == 200


def test_message_without_url_rejected():
    """Ensure message lacking any URL is rejected."""
    msg = "Check out our latest business platform and grow your online visibility."
    with pytest.raises(ValidationError) as exc_info:
        PostingRequest(message=msg)
    assert "Message must contain exactly one CTA link, but none was found" in str(exc_info.value)


def test_message_with_multiple_urls_rejected():
    """Ensure message containing two or more URLs is rejected."""
    msg = "Visit our site at https://example.com or our docs at https://docs.example.com"
    with pytest.raises(ValidationError) as exc_info:
        PostingRequest(message=msg)
    assert "Message must contain exactly one CTA link, but found 2" in str(exc_info.value)


def test_malformed_url_rejected():
    """Ensure malformed or unresolvable URLs are rejected."""
    malformed_examples = [
        "Check this out: http://",
        "Check this out: https://",
        "Check this out: http://...",
        "Check this out: https://invalid_domain_without_tld",
    ]
    for msg in malformed_examples:
        with pytest.raises(ValidationError):
            PostingRequest(message=msg)
