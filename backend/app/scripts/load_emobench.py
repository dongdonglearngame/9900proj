"""Load EmoBench into the scenario_items + questions tables.

TODO(P18-DATA-2): implement the loader.

Expected per-record shapes (verify against the real dump — no EmoBench file ships
with the repo, so the field names below are from the public layout):
- EU (Emotional Understanding): one Scenario with up to two sub-questions ``Emotion``
  and ``Cause``, each ``{"Choices": [...4...], "Label": <text|letter|index>}``. The two
  sub-questions SHARE one scenario (dedupe by scenario hash) -> ~400 items, not 200.
- EA (Emotional Application): one Scenario with top-level ``Choices``/``Label`` and an
  optional ``Problem`` question text.

Requirements:
- Parse a ``.json`` list (or ``{"data": [...]}``) or ``.jsonl`` file.
- Write scenario_items (deduped by hash) and questions; do NOT hard-code an item count.
- Fail loudly (raise) on malformed entries rather than skipping them silently.

`app/db/models.py`, `app/db/session.py`, `app/db/init_db.py` and `app/db/hashing.py`
already provide the tables, engine, schema bootstrap and hashing helpers to build on.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Load EmoBench data into SQLite.")
    parser.add_argument("--input", required=True, help="Path to EmoBench JSON or JSONL file.")
    parser.add_argument("--source-dataset", default="emobench")
    args = parser.parse_args()
    raise NotImplementedError(f"EmoBench loader not implemented yet (P18-DATA-2): {args.input}")


if __name__ == "__main__":
    main()
