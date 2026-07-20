# S2 Counterfactual Validity Rubric

This rubric separates frozen-harness flips from counterfactual validity. A result is
not valid merely because the target model predicts the selected foil.

## Labels

### Good

The edit is grammatical, locally minimal, relevant to the selected foil, and leaves a
coherent story. It changes an event, outcome, relationship, or observable behaviour
that plausibly explains the target prediction change. It does not state the target
emotion or copy answer wording.

### Acceptable

The edit is understandable, relevant, and internally consistent, but has a minor
wording, fluency, or causal-strength issue. The issue must not change the story's core
meaning or make the explanation misleading.

### Invalid

Use `Invalid` when any material problem applies:

- `grammar`: malformed or unnatural text changes the interpretation.
- `contradiction`: an unchanged sentence conflicts with the edited fact.
- `irrelevant`: the edit does not provide a plausible cause for the target answer.
- `foil_leak`: the edit directly states or morphologically derives the target answer.
- `focal_shift`: the edit replaces the focal person or event with a bystander reaction.
- `evaluative_cue`: the flip relies only on words such as `surprisingly`, `great`, or
  `unique`, rather than an underlying event change.
- `near_synonym`: the edit is a near-synonym swap with no meaningful causal change.
- `model_sensitivity`: spelling, punctuation, container words, or equivalent phrasing
  changes the prediction without changing the scenario's relevant facts.
- `excessive_edit`: the result exceeds the configured edit bound without a justified
  causal need.

## Annotation Procedure

1. Show the annotator the original scenario, original prediction, foil, modified
   scenario, new prediction, and highlighted diff.
2. Hide prompt variant, strategy diagnostics, and other annotators' labels until the
   independent decision is recorded.
3. Two team members independently assign `Good`, `Acceptable`, or `Invalid`, plus one
   or more reason codes and a one-sentence justification.
4. Resolve disagreements in a short adjudication meeting. Preserve both original
   labels and the adjudicated label.
5. Do not change a prompt using holdout labels. Holdout is evaluated once after the
   strategy is frozen.

## Required Record

Each annotation row must contain:

- question ID and dimension;
- original scenario and prediction;
- selected foil and its option text;
- modified scenario and new prediction;
- token edit distance and changed-word fraction;
- reviewer A label/reasons;
- reviewer B label/reasons;
- adjudicated label/reasons;
- free-text note.

## Reported Metrics

- Mechanical flip rate: `mechanical successes / attempted scenarios`.
- Human-valid precision: `(Good + Acceptable) / mechanical successes`.
- Human-valid scenario rate: `(Good + Acceptable) / attempted scenarios`.
- Invalid rate by reason code.
- Average edit distance for `Good + Acceptable` results, reported separately from all
  mechanical successes.

The fixed dev-40 set is success-enriched regression data and must not be presented as
an EU population estimate. Final claims require a separate, untouched holdout set.
