import json
from collections.abc import Callable, Generator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.repositories.scenario_repo import ScenarioRepository
from app.scripts.load_emobench import EmoBenchLoadError, load_emobench


@pytest.fixture
def session_factory() -> Generator[
    tuple[Session, Callable[[], Generator[Session, None, None]]],
    None,
    None,
]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    def factory() -> Generator[Session, None, None]:
        yield Session(engine)

    try:
        yield session, factory
    finally:
        session.close()


def test_load_emobench_splits_shared_eu_scenario_and_repository_filters(
    tmp_path,
    session_factory,
) -> None:
    session, factory = session_factory
    source = tmp_path / "emobench.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "eu-1",
                    "Scenario": "Regina is worried about a close friend.",
                    "Subject": "Regina",
                    "Task": "EU",
                    "Emotion": {
                        "Choices": ["happy", "worried", "angry", "calm"],
                        "Label": "B",
                    },
                    "Cause": {
                        "Choices": {
                            "A": "A party invitation",
                            "B": "A work deadline",
                            "C": "A friend's distress",
                            "D": "A weather change",
                        },
                        "Label": "A friend's distress",
                    },
                },
                {
                    "id": "ea-1",
                    "Scenario": "Omar received harsh feedback before a meeting.",
                    "Subject": "Omar",
                    "Task": "EA",
                    "Dimension": "emotion_regulation",
                    "Problem": "What should Omar do next?",
                    "Choices": ["Leave", "Reflect and prepare", "Blame others", "Shout"],
                    "Label": 1,
                },
            ]
        ),
        encoding="utf-8",
    )

    summary = load_emobench(source, session=session)

    assert summary == {"scenarios": 2, "questions": 3}
    repo = ScenarioRepository(session_factory=factory, use_mock_fallback=False)
    eu_page = repo.list_scenarios(task_type="EU", dimension=None, limit=10, offset=0)
    assert eu_page.total == 2
    assert {item.dimension for item in eu_page.items} == {"emotion", "cause"}
    assert eu_page.items[0].scenario == "Regina is worried about a close friend."

    cause_page = repo.list_scenarios(task_type="EU", dimension="cause", limit=10, offset=0)
    assert cause_page.total == 1
    assert cause_page.items[0].label == "C"

    paged = repo.list_scenarios(task_type=None, dimension=None, limit=1, offset=1)
    assert paged.total == 3
    assert len(paged.items) == 1


def test_load_emobench_fails_loudly_on_malformed_entry(tmp_path, session_factory) -> None:
    session, _factory = session_factory
    source = tmp_path / "bad.json"
    source.write_text(json.dumps([{"Scenario": "Missing choices and label"}]), encoding="utf-8")

    with pytest.raises(EmoBenchLoadError, match="no question"):
        load_emobench(source, session=session)


def test_load_emobench_defaults_to_english_records(tmp_path, session_factory) -> None:
    session, factory = session_factory
    source = tmp_path / "multi_language.jsonl"
    rows = [
        {
            "qid": "1",
            "language": "en",
            "scenario": "English scenario",
            "choices": ["A", "B", "C", "D"],
            "label": "A",
        },
        {
            "qid": "1",
            "language": "zh",
            "scenario": "Chinese scenario",
            "choices": ["A", "B", "C", "D"],
            "label": "B",
        },
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    summary = load_emobench(source, session=session)

    assert summary == {"scenarios": 1, "questions": 1}
    page = ScenarioRepository(session_factory=factory, use_mock_fallback=False).list_scenarios(
        task_type="EA",
        dimension=None,
        limit=10,
        offset=0,
    )
    assert page.total == 1
    assert page.items[0].scenario == "English scenario"
