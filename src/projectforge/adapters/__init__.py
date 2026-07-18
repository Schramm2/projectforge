"""Backend adapter implementations for the multi-agent orchestration framework."""

from projectforge.adapters.antigravity_adapter import AntigravityAdapter
from projectforge.adapters.claude_adapter import ClaudeAdapter
from projectforge.adapters.codex_adapter import CodexAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "claude": ClaudeAdapter,
    "antigravity": AntigravityAdapter,
    "codex": CodexAdapter,
}


def get_adapter(
    backend: str,
    conventions: str = "",
    *,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
):
    adapter_cls = ADAPTER_REGISTRY.get(backend)
    if adapter_cls is None:
        raise ValueError(f"No adapter for backend: {backend}")
    return adapter_cls(
        conventions=conventions,
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )
