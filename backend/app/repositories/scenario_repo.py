import json
from collections.abc import Callable, Generator

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, func, select

from app.db.models import Question
from app.db.models import ScenarioItem as ScenarioItemRecord
from app.db.session import get_session
from app.schemas.scenario import ScenarioItem, ScenariosResponse

# Built-in mock scenarios so the app is demoable before EmoBench is loaded.
# TODO(P18-DATA-1/2): read scenarios from the scenario_items + questions tables instead
# (join + task_type/dimension filters + real total), falling back to these when empty.
MOCK_SCENARIOS = [
    ScenarioItem(
        question_id="q_regina_001",
        scenario_item_id="s_regina_001",
        task_type="EU",
        dimension="emotion_cause",
        subject="Regina",
        scenario=(
            "Regina's best friend recently broke up with her longtime partner and is "
            "texting Regina in the middle of the night expressing feelings of loneliness."
        ),
        question_text="What should Regina do?",
        choices={
            "A": "Ignore the texts and continue sleeping",
            "B": "Tell her friend to seek professional help",
            "C": "Stay up and lend a listening ear",
            "D": "Suggest her friend find a new partner",
        },
        label="C",
    ),
    ScenarioItem(
        question_id="q_omar_001",
        scenario_item_id="s_omar_001",
        task_type="EA",
        dimension="emotion_regulation",
        subject="Omar",
        scenario=(
            "Omar received harsh feedback on a presentation and feels embarrassed before "
            "his next meeting."
        ),
        question_text="What is the most emotionally constructive response?",
        choices={
            "A": "Avoid the meeting completely",
            "B": "Pause, review the feedback, and prepare one improvement",
            "C": "Blame the audience for misunderstanding",
            "D": "Send an angry message to his manager",
        },
        label="B",
    ),
]


class ScenarioRepository:
    def __init__(
        self,
        session_factory: Callable[[], Generator[Session, None, None]] = get_session,
        *,
        use_mock_fallback: bool = True,
    ) -> None:
        self._session_factory = session_factory
        self._use_mock_fallback = use_mock_fallback

    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        loaded = self._list_loaded_scenarios(
            task_type=task_type,
            dimension=dimension,
            limit=limit,
            offset=offset,
        )
        if loaded.total > 0 or not self._use_mock_fallback:
            return loaded

        items = MOCK_SCENARIOS
        if task_type:
            items = [item for item in items if item.task_type == task_type]
        if dimension:
            items = [item for item in items if item.dimension == dimension]
        return ScenariosResponse(items=items[offset : offset + limit], total=len(items))

    def _list_loaded_scenarios(
        self,
        *,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        session_iterator = self._session_factory()
        session = next(session_iterator)
        try:
            filters = []
            if task_type:
                filters.append(Question.task_type == task_type)
            if dimension:
                filters.append(Question.dimension == dimension)

            base = (
                select(Question, ScenarioItemRecord)
                .join(
                    ScenarioItemRecord,
                    col(Question.scenario_item_id) == col(ScenarioItemRecord.id),
                )
                .order_by(Question.id)
            )
            count_query = select(func.count()).select_from(Question)
            for condition in filters:
                base = base.where(condition)
                count_query = count_query.where(condition)

            total = session.exec(count_query).one()
            rows = session.exec(base.offset(offset).limit(limit)).all()
        except SQLAlchemyError:
            return ScenariosResponse(items=[], total=0)
        finally:
            session.close()
            session_iterator.close()

        items = [
            ScenarioItem(
                question_id=question.id,
                scenario_item_id=scenario.id,
                task_type=question.task_type,
                dimension=question.dimension,
                subject=scenario.subject,
                scenario=scenario.scenario_text,
                question_text=question.question_text,
                choices=json.loads(question.choices_json),
                label=question.ground_truth,  # type: ignore[arg-type]
            )
            for question, scenario in rows
        ]
        return ScenariosResponse(items=items, total=total)
