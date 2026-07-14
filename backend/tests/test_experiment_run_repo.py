import json
from collections.abc import Generator

from sqlmodel import Session, SQLModel

from app.db.models import Counterfactual, Metric
from app.db.session import create_configured_engine
from app.repositories.experiment_run_repo import ExperimentRunRepository


def test_experiment_run_repository_stores_git_commit_and_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'runs.db'}")
    SQLModel.metadata.create_all(engine)

    def session_factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    monkeypatch.setattr("app.repositories.experiment_run_repo.get_git_commit", lambda: "abc123")
    repo = ExperimentRunRepository(session_factory=session_factory)

    created = repo.create(
        name="demo-b-fixed-subset",
        scenario_subset_id="subset-10",
        model="llama3.2:3b",
        budget=20,
        prompt_template_version="target-v2",
        strategy_ids=["s1_word_greedy", "s2_llm_propose_verify"],
        task_type="EU",
        dimension="cause",
        notes="smoke run",
    )
    restored = repo.get(created.id)

    assert restored is not None
    assert restored.git_commit == "abc123"
    assert restored.scenario_subset_id == "subset-10"
    assert restored.task_type == "EU"
    assert json.loads(restored.strategy_ids_json) == [
        "s1_word_greedy",
        "s2_llm_propose_verify",
    ]

    with Session(engine) as session:
        session.add(
            Counterfactual(
                id="cf1",
                experiment_run_id=created.id,
                job_id="job1",
                question_id="q1",
                strategy_id="s1_word_greedy",
                model="llama3.2:3b",
                status="success",
                original_answer="A",
                foil="C",
                new_answer="C",
                original_scenario="Regina is worried.",
                modified_scenario="Regina is calm.",
                diff_json="[]",
                attempts_json="[]",
                runtime_seconds=1.2,
            )
        )
        session.add(
            Metric(
                id="metric1",
                experiment_run_id=created.id,
                counterfactual_id="cf1",
                strategy_id="s1_word_greedy",
                flip_success=True,
                token_edit_distance=1,
                changed_word_fraction=0.25,
                search_calls=3,
                postprocess_calls=1,
                proposer_calls=0,
                total_target_calls=4,
                runtime_seconds=1.2,
            )
        )
        session.commit()

        assert session.get(Counterfactual, "cf1").experiment_run_id == created.id
        assert session.get(Metric, "metric1").experiment_run_id == created.id
