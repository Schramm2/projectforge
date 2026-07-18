"""Tests for interactive prompt review behavior."""

from io import StringIO
from types import SimpleNamespace

from rich.console import Console

from projectforge.prompts import _ask_execution_mode, _ask_project_basics, collect_answers


def test_execution_mode_labels_standard_as_the_actual_default(monkeypatch):
    captured = {}

    class Selection:
        def ask(self):
            return "standard"

    def fake_select(message, *, choices, default=None):
        captured["message"] = message
        captured["choices"] = choices
        captured["default"] = default
        return Selection()

    monkeypatch.setattr("projectforge.prompts.prompt_select", fake_select)
    answers = {"agents": False}

    _ask_execution_mode(answers)

    assert captured["default"] == "standard"
    assert captured["choices"][0].value == "standard"
    assert "Standard (default)" in captured["choices"][0].title
    assert "recommended" not in captured["choices"][1].title.lower()
    assert answers["agents"] is False


def test_missing_docker_message_explains_recovery(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(
        "projectforge.prompts.create_console",
        lambda: Console(file=output, force_terminal=False, color_system=None, width=120),
    )
    monkeypatch.setattr(
        "projectforge.prompts.prompt_text",
        lambda message, **kwargs: SimpleNamespace(
            ask=lambda: "demo" if message == "Project name" else "A demo project"
        ),
    )
    monkeypatch.setattr(
        "projectforge.prompts.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: "fastapi"),
    )
    answers = {}

    _ask_project_basics(answers, docker_available=False)

    assert answers["docker"] is False
    assert "Docker is not installed" in output.getvalue()
    assert "Install Docker and restart Forge" in output.getvalue()


def test_collect_answers_allows_review_edit_before_scaffold(monkeypatch):
    calls = {"basics": 0, "appearance": 0, "integrations": 0, "demo": 0, "execution": 0}
    actions = iter(["basics", "scaffold"])

    def _fake_basics(answers, *, docker_available):
        calls["basics"] += 1
        if calls["basics"] == 1:
            answers["name"] = "first-name"
        else:
            answers["name"] = "corrected-name"
        answers["stack"] = "fastapi"
        answers["description"] = "A test scaffold"
        answers["docker"] = False

    def _fake_appearance(answers):
        calls["appearance"] += 1
        answers["design_template"] = None
        answers["media_collection"] = None

    def _fake_integrations(answers):
        calls["integrations"] += 1
        answers["auth_provider"] = None
        answers["services"] = []
        answers["ci"] = {"include": False, "mode": None, "actions": []}
        answers["extra"] = ""

    def _fake_demo(answers):
        calls["demo"] += 1
        answers["demo_mode"] = True

    def _fake_execution(answers):
        calls["execution"] += 1
        answers["agents"] = False

    monkeypatch.setattr("projectforge.prompts._ask_project_basics", _fake_basics)
    monkeypatch.setattr("projectforge.prompts._ask_design_and_media", _fake_appearance)
    monkeypatch.setattr("projectforge.prompts._ask_customizations", _fake_integrations)
    monkeypatch.setattr("projectforge.prompts._ask_demo_mode", _fake_demo)
    monkeypatch.setattr("projectforge.prompts._ask_execution_mode", _fake_execution)
    monkeypatch.setattr("projectforge.prompts._review_answers", lambda answers: next(actions))
    monkeypatch.setattr("projectforge.preferences.get_defaults", lambda: {})

    answers = collect_answers(docker_available=True)

    assert answers["name"] == "corrected-name"
    assert calls == {"basics": 2, "appearance": 1, "integrations": 1, "demo": 1, "execution": 1}
