import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from app.core.config import get_settings
from app.proposer.clients import OllamaProposerClient, ProposerClient
from app.proposer.harness import parse_proposed_edits_with_diagnostics
from app.proposer.prompts import build_proposer_messages


def run_spike(
    *,
    client: ProposerClient,
    scenario: str,
    choices: dict[str, str],
    original_answer: str,
    foil: str,
    counts: list[int],
    num_predict_values: list[int],
    temperature: float,
    seed: int,
    repetitions: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for count in counts:
        for num_predict in num_predict_values:
            for repetition in range(repetitions):
                messages = build_proposer_messages(
                    scenario=scenario,
                    choices=choices,
                    foil=foil,
                    original_answer=original_answer,
                    count=count,
                    avoid=None,
                )
                options = {
                    "temperature": temperature,
                    "seed": seed + repetition,
                    "num_predict": num_predict,
                }
                started = perf_counter()
                completion = client.complete(messages, options)
                latency_seconds = round(perf_counter() - started, 4)
                parsed = parse_proposed_edits_with_diagnostics(
                    completion.content,
                    limit=count,
                )
                rows.append(
                    {
                        "count": count,
                        "num_predict": num_predict,
                        "seed": seed + repetition,
                        "done_reason": completion.done_reason,
                        "eval_count": completion.eval_count,
                        "response_tokens": completion.response_tokens,
                        "response_characters": len(completion.content),
                        "raw_candidates": parsed.raw_candidates,
                        "parsed_candidates": parsed.parsed_candidates,
                        "delivered_candidates": len(parsed.edits),
                        "raw_requested_yield": _ratio(parsed.raw_candidates, count),
                        "parsed_raw_yield": _ratio(
                            parsed.parsed_candidates,
                            parsed.raw_candidates,
                        ),
                        "latency_seconds": latency_seconds,
                    }
                )

    return {
        "mode": "s2_full_scenario_rewrite",
        "configuration": {
            "counts": counts,
            "num_predict_values": num_predict_values,
            "temperature": temperature,
            "base_seed": seed,
            "repetitions": repetitions,
        },
        "rows": rows,
    }


def _load_case(path: Path) -> tuple[str, dict[str, str], str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")

    scenario = payload.get("scenario")
    choices = payload.get("choices")
    original_answer = payload.get("original_answer")
    foil = payload.get("foil")
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError("scenario must be a non-empty string")
    if not isinstance(choices, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in choices.items()
    ):
        raise ValueError("choices must be an object of string keys and values")
    if original_answer not in choices:
        raise ValueError("original_answer must be a key in choices")
    if foil not in choices:
        raise ValueError("foil must be a key in choices")
    if original_answer == foil:
        raise ValueError("foil must differ from original_answer")
    return scenario, choices, original_answer, foil


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Measure S2 proposer output length and candidate yield.",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--counts", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument(
        "--num-predict-values",
        type=int,
        nargs="+",
        default=[512, 1024, 1536],
    )
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=settings.proposer_temperature)
    parser.add_argument("--seed", type=int, default=settings.proposer_seed)
    parser.add_argument("--model", default=settings.proposer_model)
    parser.add_argument("--ollama-base-url", default=settings.ollama_base_url)
    args = parser.parse_args()

    if any(count <= 0 for count in args.counts):
        parser.error("--counts values must be positive")
    if any(value <= 0 for value in args.num_predict_values):
        parser.error("--num-predict-values must be positive")
    if args.repetitions <= 0:
        parser.error("--repetitions must be positive")

    scenario, choices, original_answer, foil = _load_case(args.input)
    report = run_spike(
        client=OllamaProposerClient(
            base_url=args.ollama_base_url,
            model=args.model,
        ),
        scenario=scenario,
        choices=choices,
        original_answer=original_answer,
        foil=foil,
        counts=args.counts,
        num_predict_values=args.num_predict_values,
        temperature=args.temperature,
        seed=args.seed,
        repetitions=args.repetitions,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
