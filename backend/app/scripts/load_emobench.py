"""Load EmoBench into the scenario_items + questions tables."""

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.db.hashing import choices_hash, scenario_hash
from app.db.init_db import init_db
from app.db.models import Question, ScenarioItem
from app.db.session import engine

CHOICE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SCENARIO_KEYS = ("Scenario", "scenario", "Text", "text", "Context", "context", "Input", "input")
SUBJECT_KEYS = ("Subject", "subject", "Person", "person", "Name", "name")
TASK_KEYS = (
    "Task",
    "task",
    "TaskType",
    "task_type",
    "taskType",
    "Type",
    "type",
)
DIMENSION_KEYS = (
    "Dimension",
    "dimension",
    "question type",
    "Category",
    "category",
    "coarse_category",
    "finegrained_category",
)
QUESTION_KEYS = ("Problem", "problem", "Question", "question", "QuestionText", "question_text")
CHOICES_KEYS = ("Choices", "choices", "Options", "options", "Answers", "answers")
LABEL_KEYS = ("Label", "label", "Answer", "answer", "Correct", "correct")


class EmoBenchLoadError(ValueError):
    """Raised when the source file shape is not loadable as EmoBench MCQA data."""


@dataclass(frozen=True)
class LoadedQuestion:
    scenario_id: str
    question: Question


def load_emobench(
    input_path: Path,
    *,
    source_dataset: str = "emobench",
    language: str | None = "en",
    session: Session | None = None,
) -> dict[str, int]:
    records = filter_records_by_language(read_records(input_path), language)
    owns_session = session is None
    if session is None:
        init_db()
        session = Session(engine)

    try:
        scenario_ids: set[str] = set()
        question_count = 0
        for index, record in enumerate(records, start=1):
            scenario, questions = parse_record(
                record,
                index=index,
                source_dataset=source_dataset,
            )
            existing_scenario = session.get(ScenarioItem, scenario.id)
            if existing_scenario:
                update_scenario(existing_scenario, scenario)
            else:
                session.add(scenario)
            scenario_ids.add(scenario.id)

            for loaded in questions:
                existing_question = session.get(Question, loaded.question.id)
                if existing_question:
                    update_question(existing_question, loaded.question)
                else:
                    session.add(loaded.question)
                question_count += 1

        session.commit()
        return {"scenarios": len(scenario_ids), "questions": question_count}
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def read_records(input_path: Path) -> list[dict[str, Any]]:
    if not input_path.exists():
        raise EmoBenchLoadError(f"input file does not exist: {input_path}")

    if input_path.suffix.lower() == ".jsonl":
        records = [
            json.loads(line)
            for line in input_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        records = payload.get("data", payload) if isinstance(payload, dict) else payload

    if not isinstance(records, list):
        raise EmoBenchLoadError("expected a JSON list, JSONL records, or {'data': [...]} payload")
    if not all(isinstance(record, dict) for record in records):
        raise EmoBenchLoadError("every EmoBench record must be a JSON object")
    return records


def filter_records_by_language(
    records: list[dict[str, Any]],
    language: str | None,
) -> list[dict[str, Any]]:
    if language is None:
        return records
    return [
        record
        for record in records
        if "language" not in record or str(record["language"]).casefold() == language.casefold()
    ]


def parse_record(
    record: dict[str, Any],
    *,
    index: int,
    source_dataset: str,
) -> tuple[ScenarioItem, list[LoadedQuestion]]:
    scenario_text = require_text(record, SCENARIO_KEYS, index, "scenario")
    scenario_id = f"{source_dataset}_s_{scenario_hash(scenario_text)[:16]}"
    source_item_id = text_or_default(
        first_present(record, ("id", "ID", "qid", "source_item_id", "item_id")),
        f"record_{index}",
    )
    language = optional_text(record, ("language", "Language"))
    if language:
        source_item_id = f"{language}_{source_item_id}"
    scenario = ScenarioItem(
        id=scenario_id,
        source_dataset=source_dataset,
        source_item_id=source_item_id,
        scenario_hash=scenario_hash(scenario_text),
        scenario_text=scenario_text,
        subject=optional_text(record, SUBJECT_KEYS),
        raw_json=json.dumps(record, ensure_ascii=False, sort_keys=True),
    )

    parsed_questions = list(parse_questions(record, index=index, source_dataset=source_dataset))
    if not parsed_questions:
        raise EmoBenchLoadError(f"record {index}: no question with choices and label found")

    loaded = [
        LoadedQuestion(
            scenario_id=scenario_id,
            question=Question(
                id=stable_question_id(
                    source_dataset=source_dataset,
                    source_item_id=source_item_id,
                    index=index,
                    dimension=parsed.dimension,
                ),
                scenario_item_id=scenario_id,
                source_question_id=parsed.source_question_id,
                task_type=parsed.task_type,
                dimension=parsed.dimension,
                question_text=parsed.question_text,
                choices_json=json.dumps(parsed.choices, ensure_ascii=False, sort_keys=True),
                choices_hash=choices_hash(parsed.choices),
                ground_truth=parsed.label,
            ),
        )
        for parsed in parsed_questions
    ]
    return scenario, loaded


@dataclass(frozen=True)
class ParsedQuestion:
    task_type: str
    dimension: str
    question_text: str | None
    choices: dict[str, str]
    label: str
    source_question_id: str | None


def parse_questions(
    record: dict[str, Any],
    *,
    index: int,
    source_dataset: str,
) -> Iterable[ParsedQuestion]:
    task_type = optional_text(record, TASK_KEYS)
    question_text = optional_text(record, QUESTION_KEYS)

    for prefix in ("emotion", "cause"):
        choices_value = record.get(f"{prefix}_choices")
        label_value = record.get(f"{prefix}_label")
        if choices_value is None and label_value is None:
            continue
        choices = parse_choices(choices_value, index=index, scope=prefix)
        label = parse_label(label_value, choices, index=index, scope=prefix)
        yield ParsedQuestion(
            task_type=task_type or "EU",
            dimension=prefix,
            question_text=question_text,
            choices=choices,
            label=label,
            source_question_id=f"{source_dataset}_{index}_{prefix}",
        )

    nested_questions = [
        (key, value)
        for key, value in record.items()
        if isinstance(value, dict) and first_present(value, CHOICES_KEYS) is not None
    ]
    for key, value in nested_questions:
        choices = parse_choices(first_present(value, CHOICES_KEYS), index=index, scope=key)
        label = parse_label(first_present(value, LABEL_KEYS), choices, index=index, scope=key)
        dimension = optional_text(value, DIMENSION_KEYS) or key
        yield ParsedQuestion(
            task_type=task_type or infer_task_type(record, nested=True),
            dimension=normalize_code(dimension),
            question_text=optional_text(value, QUESTION_KEYS) or question_text,
            choices=choices,
            label=label,
            source_question_id=f"{source_dataset}_{index}_{normalize_code(key)}",
        )

    if first_present(record, CHOICES_KEYS) is not None:
        choices = parse_choices(first_present(record, CHOICES_KEYS), index=index, scope="top-level")
        label = parse_label(
            first_present(record, LABEL_KEYS),
            choices,
            index=index,
            scope="top-level",
        )
        dimension = optional_text(record, DIMENSION_KEYS) or task_type or "general"
        yield ParsedQuestion(
            task_type=task_type or infer_task_type(record, nested=False),
            dimension=normalize_code(dimension),
            question_text=question_text,
            choices=choices,
            label=label,
            source_question_id=f"{source_dataset}_{index}_{normalize_code(dimension)}",
        )


def parse_choices(value: Any, *, index: int, scope: str) -> dict[str, str]:
    if isinstance(value, dict):
        choices = {str(key).upper(): text_or_default(choice, "") for key, choice in value.items()}
    elif isinstance(value, list) and 2 <= len(value) <= len(CHOICE_LETTERS):
        choices = {
            letter: text_or_default(value[position], "")
            for position, letter in enumerate(CHOICE_LETTERS[: len(value)])
        }
    else:
        raise EmoBenchLoadError(
            f"record {index} {scope}: choices must be a letter-keyed dict or 2-26 item list"
        )

    missing = [letter for letter, text in choices.items() if not text]
    if missing:
        raise EmoBenchLoadError(
            f"record {index} {scope}: missing choice text for {', '.join(missing)}"
        )
    return choices


def parse_label(
    value: Any,
    choices: dict[str, str],
    *,
    index: int,
    scope: str,
) -> str:
    if value is None:
        raise EmoBenchLoadError(f"record {index} {scope}: missing label")

    if isinstance(value, int):
        if value in range(len(choices)):
            return CHOICE_LETTERS[value]
        if value in range(1, len(choices) + 1):
            return CHOICE_LETTERS[value - 1]

    text = str(value).strip()
    upper = text.upper()
    if upper in choices:
        return upper

    for letter, choice_text in choices.items():
        if choice_text.strip().casefold() == text.casefold():
            return letter

    raise EmoBenchLoadError(
        f"record {index} {scope}: label does not match a choice letter or choice text"
    )


def require_text(
    record: dict[str, Any],
    keys: tuple[str, ...],
    index: int,
    field_name: str,
) -> str:
    value = first_present(record, keys)
    text = text_or_default(value, "")
    if not text:
        raise EmoBenchLoadError(f"record {index}: missing {field_name}")
    return text


def optional_text(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = first_present(record, keys)
    text = text_or_default(value, "")
    return text or None


def first_present(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def text_or_default(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(value).strip()


def normalize_code(value: str) -> str:
    return "_".join(value.strip().lower().split())


def infer_task_type(record: dict[str, Any], *, nested: bool) -> str:
    if nested and any(key in record for key in ("Emotion", "Cause")):
        return "EU"
    return "EA"


def stable_question_id(
    *,
    source_dataset: str,
    source_item_id: str,
    index: int,
    dimension: str,
) -> str:
    safe_source_id = normalize_code(source_item_id) or f"record_{index}"
    return f"{source_dataset}_q_{safe_source_id}_{normalize_code(dimension)}"


def update_scenario(existing: ScenarioItem, incoming: ScenarioItem) -> None:
    existing.source_dataset = incoming.source_dataset
    existing.source_item_id = incoming.source_item_id
    existing.scenario_hash = incoming.scenario_hash
    existing.scenario_text = incoming.scenario_text
    existing.subject = incoming.subject
    existing.raw_json = incoming.raw_json


def update_question(existing: Question, incoming: Question) -> None:
    existing.scenario_item_id = incoming.scenario_item_id
    existing.source_question_id = incoming.source_question_id
    existing.task_type = incoming.task_type
    existing.dimension = incoming.dimension
    existing.question_text = incoming.question_text
    existing.choices_json = incoming.choices_json
    existing.choices_hash = incoming.choices_hash
    existing.ground_truth = incoming.ground_truth


def main() -> None:
    parser = argparse.ArgumentParser(description="Load EmoBench data into SQLite.")
    parser.add_argument("--input", required=True, help="Path to EmoBench JSON or JSONL file.")
    parser.add_argument("--source-dataset", default="emobench")
    parser.add_argument(
        "--language",
        default="en",
        help="Language code to import. Use 'all' to import every language.",
    )
    args = parser.parse_args()
    language = None if args.language.casefold() == "all" else args.language
    summary = load_emobench(
        Path(args.input),
        source_dataset=args.source_dataset,
        language=language,
    )
    print(
        "Loaded "
        f"{summary['questions']} questions across {summary['scenarios']} scenarios "
        f"from {args.input}"
    )


if __name__ == "__main__":
    main()
