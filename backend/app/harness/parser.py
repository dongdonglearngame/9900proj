import re

_CLEAN_LETTER_RE = re.compile(r"^\s*([ABCD])\s*[\.\)]?\s*$", re.IGNORECASE)
_ANSWER_PREFIX_RE = re.compile(
    r"^\s*(?:answer|final answer|choice|the answer|the correct answer)"
    r"\s*(?:is|:|-)?\s*([ABCD])\s*[\.\)]?\s*$",
    re.IGNORECASE,
)


def parse_answer_letter(raw_response: str) -> str | None:
    """Parse the model's chosen letter (A-D) out of its raw response.

    Keep this deliberately constrained: long explanations are treated as parse failures
    so the frozen harness remains a stable multiple-choice function.
    """
    text = raw_response.strip()
    match = _CLEAN_LETTER_RE.fullmatch(text) or _ANSWER_PREFIX_RE.fullmatch(text)
    if match is None:
        return None
    return match.group(1).upper()
