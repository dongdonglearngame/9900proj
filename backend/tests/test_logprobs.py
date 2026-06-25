from app.harness.logprobs import extract_option_logprobs, normalize_token, option_logprobs_to_probs


def test_normalize_token() -> None:
    assert normalize_token(" a ") == "A"


def test_extract_option_logprobs_keeps_missing_none() -> None:
    payload = {
        "logprobs": [
            {
                "top_logprobs": [
                    {"token": " A", "logprob": -0.2},
                    {"token": "C", "logprob": -2.0},
                    {"token": "A", "logprob": -0.1},
                ]
            }
        ]
    }

    scores = extract_option_logprobs(payload)

    assert scores["A"] == -0.1
    assert scores["B"] is None
    assert scores["C"] == -2.0
    assert scores["D"] is None
    assert option_logprobs_to_probs(scores)["B"] is None


def test_extract_option_logprobs_reads_message_logprobs() -> None:
    payload = {
        "message": {
            "logprobs": [
                {
                    "top_logprobs": [
                        {"token": "B", "logprob": -0.4},
                        {"token": "D", "logprob": -3.2},
                    ]
                }
            ]
        }
    }

    scores = extract_option_logprobs(payload)

    assert scores["A"] is None
    assert scores["B"] == -0.4
    assert scores["C"] is None
    assert scores["D"] == -3.2


def test_extract_option_logprobs_ignores_non_numeric_values() -> None:
    payload = {
        "message": {
            "logprobs": [
                {
                    "top_logprobs": [
                        {"token": "A", "logprob": True},
                        {"token": "B", "logprob": "nope"},
                    ]
                }
            ]
        }
    }

    assert extract_option_logprobs(payload) == {
        "A": None,
        "B": None,
        "C": None,
        "D": None,
    }
