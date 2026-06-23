from app.harness.target_predict import ChoiceLetter

CHOICES: tuple[ChoiceLetter, ...] = ("A", "B", "C", "D")


def normalize_token(token: str) -> str:
    return token.strip().upper()


def empty_option_scores() -> dict[ChoiceLetter, float | None]:
    return {letter: None for letter in CHOICES}


def extract_option_logprobs(payload: dict) -> dict[ChoiceLetter, float | None]:
    """Pull per-option logprobs (A-D) out of an Ollama chat response.

    TODO(P18-HARNESS-2): implement. Read top_logprobs from the first generated token,
      normalise tokens, keep the max logprob per letter, and leave missing options as
      None (never 0 or -inf). See plan section 7.4.
    """
    raise NotImplementedError("logprob extraction not implemented yet (P18-HARNESS-2)")


def option_logprobs_to_probs(
    option_logprobs: dict[ChoiceLetter, float | None],
) -> dict[ChoiceLetter, float | None]:
    """TODO(P18-HARNESS-2): map logprobs to probabilities via exp(); keep None as None."""
    raise NotImplementedError("logprob->prob conversion not implemented yet (P18-HARNESS-2)")
