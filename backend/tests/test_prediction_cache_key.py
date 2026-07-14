from app.db.hashing import prediction_cache_key


def test_prediction_cache_key_includes_inference_signature() -> None:
    base = {
        "model": "llama3.2:3b",
        "prompt_template_version": "target-v2",
        "scenario": "Regina is worried.",
        "choices": {"A": "Ignore", "B": "Listen"},
        "endpoint_type": "ollama_chat",
        "top_logprobs": 20,
        "target_num_predict": 4,
        "temperature": 0.0,
    }

    original = prediction_cache_key(**base)

    assert prediction_cache_key(**{**base, "target_num_predict": 8}) != original
    assert prediction_cache_key(**{**base, "top_logprobs": 5}) != original
    assert prediction_cache_key(**{**base, "endpoint_type": "mock"}) != original
    assert prediction_cache_key(**{**base, "temperature": 0.5}) != original
