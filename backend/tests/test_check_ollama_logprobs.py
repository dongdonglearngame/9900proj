from types import SimpleNamespace

import pytest

import app.scripts.check_ollama_logprobs as preflight_module
from app.harness.target_predict import PredictionResult


class _FakeResponse:
    def __init__(self, version: str) -> None:
        self._version = version

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"version": self._version}


class _FakeClient:
    def __init__(self, option_logprobs: dict[str, float | None]) -> None:
        self._option_logprobs = option_logprobs

    def predict(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
    ) -> PredictionResult:
        _ = scenario
        return PredictionResult(
            status="ok",
            answer="A",
            answer_text=choices["A"],
            model=model,
            prompt_template_version="test",
            cache_hit=False,
            raw_response="A",
            option_logprobs=self._option_logprobs,
            option_probs={letter: None for letter in choices},
            top_logprobs_raw=[],
            runtime_seconds=0.0,
        )


def _configure(
    monkeypatch,
    *,
    version: str = "0.12.11",
    option_logprobs: dict[str, float | None] | None = None,
) -> None:
    monkeypatch.setattr(
        preflight_module,
        "get_settings",
        lambda: SimpleNamespace(ollama_base_url="http://localhost:11434"),
    )
    monkeypatch.setattr(
        preflight_module.httpx,
        "get",
        lambda *_args, **_kwargs: _FakeResponse(version),
    )
    scores = option_logprobs or {"A": -0.1, "B": -2.0}
    monkeypatch.setattr(preflight_module, "OllamaClient", lambda: _FakeClient(scores))


def test_parse_version_accepts_patch_suffix() -> None:
    assert preflight_module._parse_version("0.12.11-rc1") == (0, 12, 11)
    assert preflight_module._parse_version("invalid") is None


def test_logprob_preflight_reports_version_and_scores(monkeypatch) -> None:
    _configure(monkeypatch)

    result = preflight_module.run_preflight("llama3.2:3b")

    assert result["status"] == "ok"
    assert result["ollama_version"] == "0.12.11"
    assert result["option_logprobs"] == {"A": -0.1, "B": -2.0}


def test_logprob_preflight_rejects_old_ollama(monkeypatch) -> None:
    _configure(monkeypatch, version="0.12.10")

    with pytest.raises(RuntimeError, match=r"0\.12\.11\+ is required"):
        preflight_module.run_preflight("llama3.2:3b")


def test_logprob_preflight_rejects_missing_option_score(monkeypatch) -> None:
    _configure(monkeypatch, option_logprobs={"A": -0.1, "B": None})

    with pytest.raises(RuntimeError, match="option logprobs for: B"):
        preflight_module.run_preflight("llama3.2:3b")
