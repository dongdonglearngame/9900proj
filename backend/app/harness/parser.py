def parse_answer_letter(raw_response: str) -> str | None:
    """Parse the model's chosen letter (A-D) out of its raw response.

    TODO(P18-HARNESS-3): implement. Prefer an explicit uppercase A-D; tolerate
      "Answer: x" style prefixes. Return None when no letter can be found (the caller
      treats that as a parse failure and retries once).
    """
    raise NotImplementedError("answer parser not implemented yet (P18-HARNESS-3)")
