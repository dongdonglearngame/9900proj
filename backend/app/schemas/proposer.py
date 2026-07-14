from app.schemas.common import APIModel


class ProposerCallDiagnostics(APIModel):
    requested_candidates: int
    seed: int
    num_predict: int
    temperature: float
    raw_candidates: int
    parsed_candidates: int
    delivered_candidates: int
    done_reason: str | None = None
    eval_count: int | None = None
    response_tokens: int | None = None
    latency_seconds: float


class ProposerDiagnostics(APIModel):
    calls: list[ProposerCallDiagnostics]
    requested_candidates: int
    raw_candidates: int
    parsed_candidates: int
    delivered_candidates: int
    unique_valid_candidates: int
    target_verified_candidates: int
    guard_rejections: dict[str, int]
    raw_requested_yield: float | None
    parsed_raw_yield: float | None
    unique_valid_requested_yield: float | None
    target_verified_parsed_yield: float | None
    target_verified_delivered_yield: float | None
