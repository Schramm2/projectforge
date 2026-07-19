"""Stable provider capability metadata shared by diagnostics and execution UX."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapability:
    """Credential-free provider behavior that Forge can explain before execution."""

    install_url: str
    deterministic_status: bool
    default_model: str
    safe_mode: str
    plan_mode: str
    unsafe_mode: str

    def diagnostic_payload(self) -> dict:
        """Return the stable, JSON-safe capability contract."""
        return {
            "deterministic_status": self.deterministic_status,
            "default_model": self.default_model,
            "approval_modes": {
                "safe": self.safe_mode,
                "plan": self.plan_mode,
                "unsafe": self.unsafe_mode,
            },
            "unsafe_requires_consent": True,
        }


PROVIDER_CAPABILITIES = {
    "claude": ProviderCapability(
        install_url="https://code.claude.com/docs/en/setup",
        deterministic_status=True,
        default_model="provider_default",
        safe_mode="safe-mode + acceptEdits",
        plan_mode="safe-mode + plan (read-only)",
        unsafe_mode="bypassPermissions",
    ),
    "antigravity": ProviderCapability(
        install_url="https://antigravity.google/docs/cli-install",
        deterministic_status=True,
        default_model="provider_default",
        safe_mode="add-dir + accept-edits + terminal sandbox (headless write rule required)",
        plan_mode="add-dir + plan with sandbox",
        unsafe_mode="skip permissions without sandbox",
    ),
    "codex": ProviderCapability(
        install_url="https://github.com/openai/codex",
        deterministic_status=True,
        default_model="provider_default",
        safe_mode="cd + ephemeral workspace-write (ambient config ignored)",
        plan_mode="cd + ephemeral read-only (ambient config ignored)",
        unsafe_mode="bypass approvals and sandbox",
    ),
}
