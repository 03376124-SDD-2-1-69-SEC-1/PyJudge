"""Tests for the R2 endpoint/prefix safety guards."""

import pytest

from greader.r2_safety import assert_valid_r2_endpoint


def test_accepts_a_well_formed_endpoint() -> None:
    assert_valid_r2_endpoint("https://abcd1234.r2.cloudflarestorage.com")


def test_rejects_missing_scheme() -> None:
    with pytest.raises(ValueError, match="must start with https://"):
        assert_valid_r2_endpoint("abcd1234.r2.cloudflarestorage.com")


def test_rejects_leading_or_trailing_whitespace() -> None:
    with pytest.raises(ValueError, match="whitespace"):
        assert_valid_r2_endpoint("https://abcd1234.r2.cloudflarestorage.com ")


def test_rejects_a_trailing_path() -> None:
    with pytest.raises(ValueError, match="must not include a path"):
        assert_valid_r2_endpoint("https://abcd1234.r2.cloudflarestorage.com/bucket")


def test_rejects_an_empty_host() -> None:
    with pytest.raises(ValueError, match="missing a host"):
        assert_valid_r2_endpoint("https://")


def test_rejects_a_host_with_the_wrong_suffix() -> None:
    with pytest.raises(ValueError, match="must end with"):
        assert_valid_r2_endpoint("https://abcd1234.s3.amazonaws.com")


def test_rejects_an_empty_account_id() -> None:
    with pytest.raises(ValueError, match="missing the account ID"):
        assert_valid_r2_endpoint("https://.r2.cloudflarestorage.com")
