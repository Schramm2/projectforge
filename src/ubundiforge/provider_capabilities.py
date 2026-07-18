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
        safe_mode="acceptEdits",
        plan_mode="plan (read-only)",
        unsafe_mode="bypassPermissions",
    ),
    "gemini": ProviderCapability(
        install_url="https://geminicli.com/docs/get-started/installation/",
        deterministic_status=False,
        default_model="provider_default",
        safe_mode="auto_edit with sandbox",
        plan_mode="plan with sandbox",
        unsafe_mode="yolo",
    ),
    "codex": ProviderCapability(
        install_url="https://github.com/openai/codex",
        deterministic_status=True,
        default_model="provider_default",
        safe_mode="workspace-write",
        plan_mode="read-only",
        unsafe_mode="bypass approvals and sandbox",
    ),
}
