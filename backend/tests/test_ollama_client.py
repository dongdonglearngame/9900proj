import logging

import app.llm.ollama_client as ollama_module
from app.harness.prompt_templates import build_target_messages
from app.llm.ollama_client import OllamaClient

CHOICES = {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f"}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _chat_payload(content: str) -> dict:
    return {
        "message": {
            "content": content,
            "logprobs": [
                {
                    "top_logprobs": [
                        {"token": "A", "logprob": -0.1},
                        {"token": "C", "logprob": -2.0},
                    ]
                }
            ],
        }
    }


def test_predict_sends_frozen_payload_and_parses_answer(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, json: dict, timeout: int) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(_chat_payload("A"))

    monkeypatch.setattr(ollama_module.httpx, "post", fake_post)

    result = OllamaClient().predict("scenario", CHOICES, "mock-model")

    assert result.status == "ok"
    assert result.answer == "A"
    assert result.answer_text == "a"
    assert result.option_logprobs["A"] == -0.1
    assert result.option_logprobs["C"] == -2.0
    assert result.option_logprobs["B"] is None
    assert result.option_logprobs["D"] is None
    assert result.option_logprobs["E"] is None
    assert result.option_logprobs["F"] is None
    assert result.top_logprobs_raw
    assert captured["url"].endswith("/api/chat")
    assert captured["json"]["model"] == "mock-model"
    assert captured["json"]["messages"] == build_target_messages("scenario", CHOICES)
    assert captured["json"]["messages"][0]["content"].endswith(
        "A, B, C, D, E, or F. Do not explain."
    )
    assert "F. f" in captured["json"]["messages"][1]["content"]
    assert captured["json"]["stream"] is False
    assert captured["json"]["logprobs"] is True
    assert captured["json"]["options"]["temperature"] == 0
    assert captured["json"]["options"]["num_predict"] == 4
    assert captured["timeout"] == 120


def test_predict_retries_once_on_parse_failure(monkeypatch, caplog) -> None:
    calls = {"n": 0}

    def fake_post(*_args, **_kwargs) -> _FakeResponse:
        calls["n"] += 1
        return _FakeResponse(_chat_payload("???" if calls["n"] == 1 else "B"))

    monkeypatch.setattr(ollama_module.httpx, "post", fake_post)
    caplog.set_level(logging.WARNING)

    result = OllamaClient().predict("scenario", CHOICES, "mock-model")

    assert calls["n"] == 2
    assert result.status == "ok"
    assert result.answer == "B"
    assert "retrying once" in caplog.text


def test_predict_parse_failed_after_retry(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        ollama_module.httpx,
        "post",
        lambda *_args, **_kwargs: _FakeResponse(_chat_payload("???")),
    )
    caplog.set_level(logging.WARNING)

    result = OllamaClient().predict("scenario", CHOICES, "mock-model")

    assert result.status == "parse_failed"
    assert result.answer is None
    assert "parse failed after retry" in caplog.text
