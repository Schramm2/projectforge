"""Backend adapter implementations for the multi-agent orchestration framework."""

from ubundiforge.adapters.claude_adapter import ClaudeAdapter
from ubundiforge.adapters.codex_adapter import CodexAdapter
from ubundiforge.adapters.gemini_adapter import GeminiAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
    "codex": CodexAdapter,
}


def get_adapter(backend: str, conventions: str = ""):
    adapter_cls = ADAPTER_REGISTRY.get(backend)
    if adapter_cls is None:
        raise ValueError(f"No adapter for backend: {backend}")
    return adapter_cls(conventions=conventions)
