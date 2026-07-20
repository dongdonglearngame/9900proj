# S2 PR2 Semantic-Validity Results

Date: 2026-07-21

Branch: `feat/s2-grounded-semantic-validity`

This report records the S2 PR2 decision process. Mechanical success means only that
the frozen target selected the foil. It does not imply a valid counterfactual.

## Environment

- Target and proposer model: `llama3.2:3b`
- Model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`
- Ollama: 0.32.1
- Frozen target prompt: `target-v2-chat-dynamic-choices`
- Proposer temperature / base seed: 0.7 / 0
- Budget / foil mode: 20 / single
- Repository backend: SQLite

## Samples

The fixed dev-40 is the existing success-enriched regression set. It contains all 15
v3 mechanical successes plus deterministic non-success examples, balanced across
cause/emotion and historical original-correct/incorrect strata. It is not an EU
population sample.

The first holdout-20 was frozen after the initial implementation. A subsequent code
audit found that a generic `-ly` suffix heuristic falsely treated ordinary words such
as `family` as evaluative cues. Because that functional bug was fixed after the first
holdout had been observed, the first set is retained only as regression evidence and
is not presented as an untouched final holdout.

After the fix passed the complete backend test suite, a final holdout-v2 was selected
mechanically from the remaining questions without inspecting candidate outputs. It
excludes dev-40 and the first holdout, and contains five questions from each dimension
x historical-original-correctness stratum. Its IDs are stored in
`s2-pr2-holdout20-v2-question-ids.txt`. No strategy rule was changed after this set
was executed.

## Controlled Prompt Ablation

All dev-40 variants used the same code, model, seed, budget, target harness, quality
constraints, and semantic-risk ranking. Only the examples in the proposer prompt
changed.

| Variant | Prompt version | Mechanical success | Avg edit | Changed fraction | Target calls | Proposer calls | Runtime |
|---|---|---:|---:|---:|---:|---:|---:|
| v5 baseline | `s2-proposer-v5-coherence-checklist` | 8/40 | 4.1250 | 9.94% | 2.100 | 1.900 | 16.345s |
| zero-shot | `s2-proposer-v6-zero-shot` | 10/40 | 4.4000 | 10.52% | 1.975 | 1.825 | 15.167s |
| one-shot | `s2-proposer-v6-one-shot-curated` | 14/40 | 5.8571 | 14.46% | 1.975 | 1.900 | 15.113s |
| three-shot | `s2-proposer-v6-1-three-shot-curated` | 2/40 | 4.0000 | 14.72% | 1.200 | 1.950 | 13.761s |

Candidate funnels:

| Variant | Requested | Raw | Parsed | Unique valid | Target verified |
|---|---:|---:|---:|---:|---:|
| v5 baseline | 304 | 237 | 230 | 93 | 84 |
| zero-shot | 292 | 198 | 196 | 88 | 79 |
| one-shot | 304 | 227 | 227 | 91 | 79 |
| three-shot | 312 | 216 | 216 | 48 | 48 |

### Interpretation

- One-shot increased mechanical coverage but failed the minimality gate. Several
  successes changed 8-12 words or remained contradictory, including q161 and q187.
- The corrected three-shot prompt reached exactly the approximate four-word target
  but reduced mechanical coverage to 2/40. Its two flips were still not sufficient
  evidence of improved semantic validity.
- Zero-shot gained four successes and lost two relative to v5; the gains included
  known-invalid or doubtful cases such as q187 and typo-only q118.
- No prompt-only variant improved both human-facing validity and minimality. The v5
  prompt therefore remains the default. The controlled variants remain available for
  reproduction and future experiments.

This result directly tests the client's one/few-shot suggestion. Curated examples
changed model behaviour, but more mechanical flips did not translate into more
credible counterfactuals on this sample.

## Span-Grounded Spike

The optional `span_grounded` variant asked the proposer for exact
`original_span`/`replacement_span` pairs. The application, not the LLM, assembled the
candidate scenario. It was tested on the first 20 fixed dev questions.

| Metric | Result |
|---|---:|
| Mechanical success | 5/20 |
| Average edit distance | 2.6000 |
| Average changed fraction | 6.03% |
| Requested / raw / parsed | 148 / 127 / 82 |
| Explicit invalid spans | 41 |
| Exact grounded parsed/raw | 64.57% |
| Unique valid / target verified | 71 / 66 |

The predefined adoption gate was 80% exact grounding. The observed 64.57% failed the
gate. Some grounded successes were also malformed or semantically invalid, including
`offered -> asked` in q50 and a punctuation-damaged movie-title edit in q90. The span
path remains experimental, is not the default, and did not receive a repair loop.

## Precision-First Hardening

The final production candidate keeps the v5 prompt and adds two high-confidence hard
guards:

- reject edits made only from evaluative cues, such as `surprisingly` or `unique`;
- reject known near-synonym-only behaviour swaps, such as `frowning -> scowling`.

Other semantic signals remain diagnostics and ranking features rather than hard
rejections. The default changed-word hard cap is now six; the previous 7-12 word
fallback is no longer enabled by default.

Final dev-40 result after removing the false-positive suffix heuristic:

| Metric | v5 baseline | Hardened v5 |
|---|---:|---:|
| Mechanical success | 8/40 | 5/40 |
| Average edit distance | 4.1250 | 4.2000 |
| Average changed fraction | 9.94% | 9.90% |
| Average target calls | 2.100 | 1.350 |
| Average runtime | 16.345s | 13.022s |

Removed baseline successes:

- q90: exceeded the six-word bound;
- q161: evaluative-cue-only `rude -> unique` edit;
- q50: exceeded the six-word bound;
- q96: evaluative-cue-only insertion of `surprisingly`.

Across all 40 questions the final hardened run recorded 43 changed-word rejections,
one evaluative-cue-only rejection, one near-synonym-only rejection, and 54
target-verified candidates. Its funnel was 312 requested, 240 raw, 240 parsed, 58
unique valid, and 54 target verified. Run-to-run proposer variation means the 5/40
result must not be attributed solely to one guard change.

## Provisional Human Review

The following is a single-reviewer engineering triage, not the required final team
annotation. Two independent reviewers must still apply `s2-validity-rubric.md` and
adjudicate disagreements.

The v5 baseline had one provisionally acceptable result (q65) among eight mechanical
successes. The final hardened result retained q65 and produced four outputs that still
appear invalid: q135, q7, q121, and q189 did not make a coherent, causally relevant
change for the foil. This gives a provisional precision change from 1/8 to 1/5 while
keeping the provisional valid scenario count at 1/40.

This is a precision improvement, not a valid-coverage improvement. It must not be
reported as a final human-valid rate until dual review is complete.

## First Holdout-20 (Superseded)

The hardened configuration completed all 20 questions in the first holdout:

- mechanical success: 1/20;
- not found: 19/20;
- failed/skipped: 0/0;
- average edit distance on success: 2;
- average target calls: 1.20;
- average runtime: 15.263 seconds.

The only success, q109, deleted `sighed and` while leaving all date facts unchanged.
The original story already stated that the date was enjoyable and both people wanted
to meet again. It is provisionally `Invalid: model_sensitivity`, so provisional
human-valid coverage is 0/20. This set is regression evidence only because the `-ly`
false-positive fix was made after its output had been observed.

## Final Frozen Holdout-20 v2

The final code completed all 20 mechanically selected holdout-v2 questions with full
coverage and no failed or skipped rows:

- mechanical success: 2/20;
- not found: 18/20;
- failed/skipped: 0/0;
- average edit distance on success: 2;
- average changed fraction on success: 3.97%;
- average target calls: 1.50;
- average runtime: 15.272 seconds;
- candidate funnel: 152 requested, 128 raw, 128 parsed, 34 unique valid, and 30
  target verified.

The q107 cause result changed `the expected one` to `unusually accurate`, which
plausibly supports the foil that John unusually excelled; it is provisionally
`Acceptable`. The q132 emotion result changed only `pale` to `green` and is
provisionally `Invalid: model_sensitivity`. The single-reviewer provisional human-valid
scenario rate is therefore 1/20 and precision is 1/2. These are not final human-valid
metrics until the required second reviewer and adjudication are complete.

## Decision

1. Keep `v5_baseline` as the production prompt default.
2. Merge prompt variants and prompt-version diagnostics for reproducible ablation.
3. Merge semantic-risk diagnostics and the two high-confidence hard guards.
4. Keep the six-word production hard cap.
5. Keep span grounding experimental; do not add repair after the failed gate.
6. Report both holdout outcomes honestly. The final holdout-v2 contains one
   provisionally acceptable result, but S2 is not yet a reliable generator of
   human-valid counterfactuals.
7. Complete two-reviewer annotation before using a human-valid precision number in the
   Sprint 2 presentation or final report.

## Raw Artifacts

Artifacts are intentionally outside the Git repository in the local
`benchmark-results` directory.

| File | SHA256 |
|---|---|
| `s2_pr2_v5_baseline_dev40.json` | `3399100CC95878D2369466581A524D7488C1CE19CFC8A2D29F22BF53F3CA5E1C` |
| `s2_pr2_zero_shot_dev40.json` | `DC94DD53BAA20E1BE42CD4466D32B297D19E61086682AC515A2690634984C0B2` |
| `s2_pr2_one_shot_dev40.json` | `04D2AD9B3081E17421DFEEADB9C2910DD6B0691C2FB29707D5480FE2035CC4A0` |
| `s2_pr2_few_shot_v2_dev40.json` | `A79CA8BA01F3C710E478553AE40EE1B67AC2F9302663E16CC0BE6EBE4E696786` |
| `s2_pr2_span_grounded_spike20.json` | `E6B16722355ED2CD14433880CDBDF3FFE789BD511B774763BF2192B04A30FE71` |
| `s2_pr2_v5_hardguard_dev40.json` | `62D152EA0734BB1906A00C81DC06F9A2C5BCFB78EDD52E013D626FC82AD56715` |
| `s2_pr2_v5_hardguard_holdout20.json` | `5FB19AF3E0004E00068C7538ACDEB46673F3FC1AAA821705251CDCA963AD11EF` |
| `s2_pr2_v5_hardguard_v2_dev40.json` | `9097D7FAA1ECA1A8A083DC28A759A896E2C8B79057938C6AEECF25E16906B9D5` |
| `s2_pr2_v5_hardguard_holdout20_v2.json` | `D79B2F62B264CD262622522853892A18EB0616931690C15BAE143CAEA6F7337D` |
