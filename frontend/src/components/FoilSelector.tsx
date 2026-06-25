import { choiceLetters, type ChoiceLetter, type ChoiceMap } from "../types/api";

interface FoilSelectorProps {
  choices: ChoiceMap;
  disabled?: boolean;
  foil: ChoiceLetter | null;
  originalAnswer: ChoiceLetter | null;
  onFoilChange: (foil: ChoiceLetter) => void;
  onGenerate: () => void;
}

export function FoilSelector({
  choices,
  disabled = false,
  foil,
  originalAnswer,
  onFoilChange,
  onGenerate,
}: FoilSelectorProps) {
  const availableChoices = choiceLetters(choices).filter((letter) => letter !== originalAnswer);

  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Step 4 - Select Foil Answer</h2>
        <p>Choose the answer you want the model to have selected instead. This becomes the counterfactual target.</p>
      </div>

      <div className="choices-list">
        {availableChoices.map((letter) => (
          <button
            className={`choice-card foil-choice ${foil === letter ? "selected" : ""}`}
            key={letter}
            type="button"
            disabled={disabled}
            onClick={() => onFoilChange(letter)}
          >
            <span className="choice-badge">{letter}</span>
            <p>{choices[letter]}</p>
            {foil === letter ? <span className="selected-check" aria-hidden="true" /> : null}
          </button>
        ))}
      </div>

      <button className="outline-accent-button" disabled={disabled} type="button" onClick={onGenerate}>
        {disabled ? "Generating Counterfactual" : "Generate Counterfactual Explanation"}
      </button>
    </section>
  );
}
