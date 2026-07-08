import json
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager

from sqlmodel import Session, select

from app.db.hashing import choices_hash, scenario_hash
from app.db.models import Prediction as PredictionRecord
from app.db.session import get_session
from app.harness.target_predict import PredictionResult


class SQLitePredictionRepository:
    """SQLite-backed prediction cache shared by single runs and batch comparisons."""

    def __init__(
        self,
        session_factory: Callable[[], Generator[Session, None, None]] = get_session,
    ) -> None:
        self._session_factory = session_factory

    def get(self, cache_key: str) -> PredictionResult | None:
        with self._session() as session:
            record = session.exec(
                select(PredictionRecord).where(PredictionRecord.cache_key == cache_key)
            ).first()
            if record is None:
                return None

            return PredictionResult(
                status=record.status,
                answer=record.answer,
                answer_text=record.answer_text,
                model=record.model,
                prompt_template_version=record.prompt_template_version,
                cache_hit=False,
                raw_response=record.raw_response,
                option_logprobs=json.loads(record.option_logprobs_json),
                option_probs=json.loads(record.option_probs_json),
                top_logprobs_raw=json.loads(record.top_logprobs_raw_json),
                runtime_seconds=record.runtime_seconds,
            )

    def set(
        self,
        cache_key: str,
        result: PredictionResult,
        *,
        question_id: str | None = None,
        scenario: str,
        choices: dict[str, str],
        endpoint_type: str,
        top_logprobs: int | None,
        target_num_predict: int | None,
    ) -> None:
        record = PredictionRecord(
            id=cache_key,
            cache_key=cache_key,
            question_id=question_id,
            scenario_hash=scenario_hash(scenario),
            choices_hash=choices_hash(choices),
            model=result.model,
            prompt_template_version=result.prompt_template_version,
            endpoint_type=endpoint_type,
            top_logprobs=top_logprobs,
            target_num_predict=target_num_predict,
            answer=result.answer,
            answer_text=result.answer_text,
            status=result.status,
            raw_response=result.raw_response,
            option_logprobs_json=json.dumps(result.option_logprobs, sort_keys=True),
            option_probs_json=json.dumps(result.option_probs, sort_keys=True),
            top_logprobs_raw_json=json.dumps(result.top_logprobs_raw),
            runtime_seconds=result.runtime_seconds,
        )
        with self._session() as session:
            session.merge(record)
            session.commit()

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session_iterator = self._session_factory()
        session = next(session_iterator)
        try:
            yield session
        finally:
            session.close()
            session_iterator.close()
