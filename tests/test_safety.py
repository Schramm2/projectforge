"""Tests for secrets detection."""

from ubundiforge.safety import check_for_secrets


def test_no_secrets_in_normal_text():
    assert check_for_secrets("use Supabase for auth") == []


def test_empty_text():
    assert check_for_secrets("") == []


def test_detects_stripe_key():
    warnings = check_for_secrets("use sk-live-abc123def456ghi789jkl012mno")
    assert any("Stripe" in w for w in warnings)


def test_detects_github_token():
    warnings = check_for_secrets("token is ghp_abcdefghijklmnopqrstuvwxyz1234567890")
    assert any("GitHub" in w for w in warnings)


def test_detects_aws_key():
    warnings = check_for_secrets("key AKIAIOSFODNN7EXAMPLE")
    assert any("AWS" in w for w in warnings)


def test_detects_private_key():
    warnings = check_for_secrets("-----BEGIN RSA PRIVATE KEY-----")
    assert any("Private key" in w for w in warnings)


def test_detects_slack_token():
    warnings = check_for_secrets("use xoxb-1234567890-abcdefghij")
    assert any("Slack" in w for w in warnings)
