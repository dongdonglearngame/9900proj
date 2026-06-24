from dataclasses import dataclass
from typing import Protocol

from app.harness.target_predict import PredictionResult
from app.repositories.scenario_repo import ScenarioRepository
from app.schemas.scenario import ScenarioItem, ScenariosResponse
from app.services.prediction_service import get_prediction_service

PAGE_SIZE = 100


class ScenarioSource(Protocol):
    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse: ...


class TargetPredictor(Protocol):
    def target_predict(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
    ) -> PredictionResult: ...


@dataclass
class DimensionStats:
    total: int = 0
    correct: int = 0
    cache_hits: int = 0

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "total": self.total,
            "correct": self.correct,
            "cache_hits": self.cache_hits,
            "accuracy": accuracy(self.correct, self.total),
        }


class EvaluationService:
    """Baseline target-model accuracy over loaded questions (P18-3)."""

    def __init__(
        self,
        *,
        scenario_source: ScenarioSource | None = None,
        predictor: TargetPredictor | None = None,
        page_size: int = PAGE_SIZE,
    ) -> None:
        self._scenario_source = scenario_source or ScenarioRepository()
        self._predictor = predictor or get_prediction_service()
        self._page_size = page_size

    def run_baseline(self, model: str, task_type: str) -> dict[str, object]:
        questions = self._load_questions(task_type)
        if not questions:
            return {
                "model": model,
                "task_type": task_type,
                "status": "no_questions",
                "total": 0,
                "correct": 0,
                "skipped": 0,
                "cache_hits": 0,
                "accuracy": None,
                "by_dimension": {},
            }

        correct = 0
        skipped = 0
        cache_hits = 0
        by_dimension: dict[str, DimensionStats] = {}

        for question in questions:
            if question.label is None:
                skipped += 1
                continue

            prediction = self._predictor.target_predict(
                scenario=question.scenario,
                choices=question.choices,
                model=model,
            )
            is_correct = prediction.answer == question.label
            correct += int(is_correct)
            cache_hits += int(prediction.cache_hit)
            dimension_stats = by_dimension.setdefault(question.dimension, DimensionStats())
            dimension_stats.total += 1
            dimension_stats.correct += int(is_correct)
            dimension_stats.cache_hits += int(prediction.cache_hit)

        total = sum(stats.total for stats in by_dimension.values())
        return {
            "model": model,
            "task_type": task_type,
            "status": "ok",
            "total": total,
            "correct": correct,
            "skipped": skipped,
            "cache_hits": cache_hits,
            "accuracy": accuracy(correct, total),
            "by_dimension": {
                dimension: stats.as_dict() for dimension, stats in by_dimension.items()
            },
        }

    def _load_questions(self, task_type: str) -> list[ScenarioItem]:
        questions: list[ScenarioItem] = []
        offset = 0
        while True:
            page = self._scenario_source.list_scenarios(
                task_type=task_type,
                dimension=None,
                limit=self._page_size,
                offset=offset,
            )
            if not page.items:
                break
            questions.extend(page.items)
            offset += len(page.items)
            if offset >= page.total:
                break
        return questions


def accuracy(correct: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(correct / total, 4)
