"""Safety checks — secrets detection and overwrite protection."""

import re

SECRET_PATTERNS = [
    (r"(?:sk|pk)[-_](?:live|test)[-_][a-zA-Z0-9]{20,}", "Stripe key"),
    (r"ghp_[a-zA-Z0-9]{36,}", "GitHub personal access token"),
    (r"gho_[a-zA-Z0-9]{36,}", "GitHub OAuth token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key ID"),
    (r"xox[bpsa]-[a-zA-Z0-9-]{10,}", "Slack token"),
    (r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}", "JWT token"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private key"),
    (r"[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}", "API key/token"),
]


def check_for_secrets(text: str) -> list[str]:
    """Scan text for patterns that look like secrets or credentials.

    Returns a list of warning strings, one per detected pattern type.
    """
    if not text:
        return []

    found: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, text):
            found.append(label)

    return found
